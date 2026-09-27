from __future__ import annotations

import asyncio
from decimal import Decimal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.bot.handlers import router as handlers_router
from app.bot.keyboards.main import get_bot_commands
from app.bot.middlewares import DatabaseMiddleware, UserMiddleware
from app.config import settings
from app.constants import OrderStatus
from app.database.database import (
    close_db_connection,
    get_session_factory,
    init_db_connection,
    session_scope,
)
from app.database.models import Order, Product
from app.i18n import set_lang, t
from app.services.notification_service import notification_service
from app.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)

# FireLoot delivers orders asynchronously — poll GET /order/:id for status.
FIRELOOT_POLL_INTERVAL = 15

_background_tasks: list[asyncio.Task] = []

DEFAULT_PRODUCTS = [
    # Free Fire — FireLoot CIS (diamonds)
    ("FF 110 Diamonds", 110, Decimal("9")),
    ("FF 341 Diamonds", 341, Decimal("28")),
    ("FF 572 Diamonds", 572, Decimal("45")),
    ("FF 1166 Diamonds", 1166, Decimal("89")),
    ("FF 2398 Diamonds", 2398, Decimal("177")),
    ("FF 6160 Diamonds", 6160, Decimal("429")),
    # Free Fire — FireLoot CIS (vouchers)
    ("FF Ваучер ҳафтаи Сабук", 0, Decimal("6")),
    ("FF Ваучер ҳафта", 0, Decimal("16.80")),
    ("FF Ваучер моҳ", 0, Decimal("64.80")),
    # PUBG
    ("PUBG 60 UC", 60, Decimal("10.00")),
    ("PUBG 325 UC", 325, Decimal("48.95")),
    ("PUBG 660 UC", 660, Decimal("93.70")),
    ("PUBG 1800 UC", 1800, Decimal("241")),
    # Blood Strike
    ("Blood Strike 80 Gold", 80, Decimal("8.00")),
    ("Blood Strike 420 Gold", 420, Decimal("36.00")),
    ("Blood Strike 880 Gold", 880, Decimal("70.00")),
    # Arena Breakout
    ("Arena Breakout 60 CR", 60, Decimal("9.00")),
    ("Arena Breakout 300 CR", 300, Decimal("42.00")),
    ("Arena Breakout 680 CR", 680, Decimal("88.00")),
    # Arena Breakout: Infinite
    ("Arena Breakout: Infinite 60 CR", 60, Decimal("9.00")),
    ("Arena Breakout: Infinite 300 CR", 300, Decimal("42.00")),
    ("Arena Breakout: Infinite 680 CR", 680, Decimal("88.00")),
    # Honor of Kings
    ("Honor of Kings 80 Tokens", 80, Decimal("9.00")),
    ("Honor of Kings 400 Tokens", 400, Decimal("40.00")),
    ("Honor of Kings 800 Tokens", 800, Decimal("76.00")),
    # Marvel Rivals
    ("Marvel Rivals 100 Lattice", 100, Decimal("12.00")),
    ("Marvel Rivals 500 Lattice", 500, Decimal("55.00")),
    ("Marvel Rivals 1000 Lattice", 1000, Decimal("105.00")),
    # Mobile Legends — Russia
    ("MLBB RU 86 Diamonds", 86, Decimal("12.00")),
    ("MLBB RU 172 Diamonds", 172, Decimal("23.00")),
    ("MLBB RU 706 Diamonds", 706, Decimal("88.00")),
    # Mobile Legends — Kyrgyzstan / Belarus
    ("MLBB CIS 86 Diamonds", 86, Decimal("12.00")),
    ("MLBB CIS 172 Diamonds", 172, Decimal("23.00")),
    ("MLBB CIS 706 Diamonds", 706, Decimal("88.00")),
]


async def ensure_schema() -> None:
    """Create tables if missing and seed demo products (dev convenience)."""
    from sqlalchemy import select

    from app.database.database import Base, get_engine
    import app.database.models  # noqa: F401 — register models on Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # create_all() does not alter existing tables — add the SKU column if the
    # database was created by an older version of the code.
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE products ADD COLUMN IF NOT EXISTS sku VARCHAR(64)")
            )
    except Exception:
        logger.warning("Could not ensure products.sku column", exc_info=True)

    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN IF NOT EXISTS lang VARCHAR(8) "
                    "NOT NULL DEFAULT 'ru'"
                )
            )
    except Exception:
        logger.warning("Could not ensure users.lang column", exc_info=True)

    # MLBB products need a FireLoot zone (server id) on the order payload.
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS zone VARCHAR(32)")
            )
    except Exception:
        logger.warning("Could not ensure orders.zone column", exc_info=True)

    factory = get_session_factory()
    async with factory() as session:
        imported = False
        if settings.fireloot_api_key:
            try:
                from app.services.catalog_import import import_catalog

                stats = await import_catalog(session)
                imported = not stats.get("skipped", False)
            except Exception:
                logger.exception("FireLoot catalogue import failed")

        if not imported:
            await _seed_default_products(session)

        await session.commit()
        logger.info("Product catalogue ready")


async def _seed_default_products(session) -> None:
    """Offline fallback: the hand-maintained product list."""
    result = await session.execute(select(Product))
    existing = {p.name: p for p in result.scalars().all()}

    default_names = {name for name, _, _ in DEFAULT_PRODUCTS}
    for name, product in existing.items():
        if name not in default_names:
            product.is_active = False

    for name, diamonds, price in DEFAULT_PRODUCTS:
        product = existing.get(name)
        if product is None:
            session.add(
                Product(
                    name=name,
                    diamonds=diamonds,
                    price=price,  # type: ignore[arg-type]
                    currency="TJS",
                    is_active=True,
                )
            )
        else:
            product.diamonds = diamonds
            product.price = price  # type: ignore[assignment]
            product.is_active = True
    logger.info("Synced products with DEFAULT_PRODUCTS")


async def _sync_fireloot_catalog_loop() -> None:
    """Keep the product catalogue (SKUs + prices) fresh every 15 minutes."""
    from app.services.catalog_import import import_catalog
    from app.services.fireloot_catalog import SYNC_INTERVAL

    while True:
        try:
            async with session_scope() as session:
                stats = await import_catalog(session)
                if not stats.get("skipped"):
                    await session.commit()
                    logger.info("FireLoot catalogue sync: %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("FireLoot catalogue sync failed")
        await asyncio.sleep(SYNC_INTERVAL)


async def _refund_order(session, order: Order, reason: str) -> bool:
    from app.services.order_service import OrderService
    from app.services.user_service import UserService

    order_service = OrderService(session)
    if order.user_id is None:
        return False
    if not await order_service.was_balance_deducted(order.id):
        return False
    reference = f"fireloot:order:{order.id}"
    if await order_service.transactions.get_by_reference_id(reference) is not None:
        return False
    await UserService(session).add_balance(
        user_id=order.user_id,
        amount=Decimal(order.amount),
        description=f"Refund order #{order.id}: {reason}",
        reference_id=reference,
    )
    logger.info(
        "Refunded order_id=%s amount=%s reason=%s",
        order.id,
        order.amount,
        reason,
    )
    return True


def _processing_orders_stmt():
    """PROCESSING orders the FireLoot poller must check (GET /order/:ref).

    FireLoot refs are short codes ("DMELC", "NEY90") with no known prefix, so
    every referenced remote order is polled; local mock/realtop references are
    excluded because they do not exist on FireLoot's side.
    """
    return (
        select(Order)
        .options(selectinload(Order.product), selectinload(Order.user))
        .where(Order.status == OrderStatus.PROCESSING)
        .where(Order.provider_order_id.is_not(None))
        .where(~Order.provider_order_id.like("mocktop_%"))
        .where(~Order.provider_order_id.like("realtop_%"))
        .order_by(Order.id.asc())
        .limit(25)
    )


async def _poll_fireloot_orders(bot: Bot) -> None:
    """Watch FireLoot orders stuck in PROCESSING (GET /order/:id)."""
    from app.providers.fireloot import FireLootClient, FireLootError
    from app.services.order_service import OrderService

    while True:
        await asyncio.sleep(FIRELOOT_POLL_INTERVAL)
        try:
            client = FireLootClient()
            if not client.configured:
                continue

            async with session_scope() as session:
                result = await session.execute(_processing_orders_stmt())
                orders = list(result.scalars().all())
                if not orders:
                    continue

                order_service = OrderService(session)
                for order in orders:
                    try:
                        data = await client.order_status(
                            order.provider_order_id or ""
                        )
                    except FireLootError as exc:
                        logger.warning(
                            "FireLoot status failed ref=%s err=%s",
                            order.provider_order_id,
                            exc.code,
                        )
                        continue

                    status = str(data.get("status") or "").lower()
                    product_name = order.product.name if order.product else ""
                    user = order.user

                    if status == "completed":
                        updated = await order_service.mark_completed(order.id)
                        if updated is None:
                            continue
                        logger.info(
                            "FireLoot order completed order_id=%s",
                            order.id,
                        )
                        if user is not None:
                            set_lang(user.lang)
                            await notification_service.safe_send(
                                user.telegram_id,
                                t(
                                    "notif.done",
                                    id=order.id,
                                    product=product_name,
                                    uid=order.free_fire_uid,
                                ),
                            )
                    elif status in {"failed", "refunded"}:
                        refunded = await _refund_order(session, order, status)
                        updated = await order_service.mark_failed(
                            order.id, reason=f"fireloot:{status}"
                        )
                        if updated is None:
                            continue
                        logger.warning(
                            "FireLoot order %s order_id=%s refunded=%s",
                            status,
                            order.id,
                            refunded,
                        )
                        if user is not None:
                            set_lang(user.lang)
                            note = (
                                t(
                                    "notif.refunded",
                                    amount=order.amount,
                                    currency=order.currency,
                                )
                                if refunded
                                else ""
                            )
                            await notification_service.safe_send(
                                user.telegram_id,
                                t(
                                    "notif.failed",
                                    id=order.id,
                                    product=product_name,
                                    uid=order.free_fire_uid,
                                    note=note,
                                ),
                            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("FireLoot order polling failed")


async def on_startup(bot: Bot) -> None:
    await init_db_connection()
    await ensure_schema()
    notification_service.set_bot(bot)

    commands = await get_bot_commands()
    await bot.set_my_commands(commands)

    if settings.fireloot_api_key:
        _background_tasks.append(asyncio.create_task(_sync_fireloot_catalog_loop()))
        logger.info("FireLoot catalogue sync started")
    _background_tasks.append(asyncio.create_task(_poll_fireloot_orders(bot)))
    logger.info("Bot started, commands registered")


async def on_shutdown(bot: Bot) -> None:
    for task in _background_tasks:
        task.cancel()
    _background_tasks.clear()
    await close_db_connection()
    logger.info("Bot stopped")


async def main() -> None:
    configure_logging()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # DatabaseMiddleware first (outer): injects `session`, then UserMiddleware injects `db_user`
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(UserMiddleware())

    dp.include_router(handlers_router)

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        exception = event.exception
        message = str(exception)
        if isinstance(exception, TelegramBadRequest) and (
            "query is too old" in message
            or "query ID is invalid" in message
            or "message is not modified" in message
        ):
            logger.debug("Ignored expired/no-op Telegram error: %s", message)
            return True
        logger.error(
            "Unhandled error while processing update: %s",
            message,
            exc_info=exception,
        )
        return True

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
