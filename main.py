from __future__ import annotations

import asyncio
from decimal import Decimal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from app.bot.handlers import router as handlers_router
from app.bot.keyboards.main import get_bot_commands
from app.bot.middlewares import DatabaseMiddleware, UserMiddleware
from app.config import settings
from app.database.database import (
    close_db_connection,
    get_session_factory,
    init_db_connection,
)
from app.database.models import Product
from app.services.notification_service import notification_service
from app.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)

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
    # Stars
    ("Stars 100", 100, Decimal("10.00")),
    ("Stars 500", 500, Decimal("45.00")),
    ("Stars 1000", 1000, Decimal("85.00")),
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

    factory = get_session_factory()
    async with factory() as session:
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

        await session.commit()
        logger.info("Synced products with DEFAULT_PRODUCTS")


async def on_startup(bot: Bot) -> None:
    await init_db_connection()
    await ensure_schema()
    notification_service.set_bot(bot)

    commands = await get_bot_commands()
    await bot.set_my_commands(commands)
    logger.info("Bot started, commands registered")


async def on_shutdown(bot: Bot) -> None:
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
