from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    format_product_button,
    get_account_confirm_keyboard,
    get_ff_category_keyboard,
    get_game_keyboard,
    get_main_menu_keyboard,
    get_order_confirm_keyboard,
    get_payment_receipt_keyboard,
    get_products_keyboard,
    get_uid_request_keyboard,
)
from app.bot.keyboards.main import TOPUP_TEXT
from app.bot.keyboards.topup import CANCEL_TEXT
from app.bot.states import TopUpStates
from app.bot.utils import safe_answer, safe_edit_text
from app.constants import OrderStatus
from app.constants.games import (
    GAME_LABELS,
    game_label as _catalog_game_label,
    is_known_game,
    match_products,
)
from app.database.models import Order, User
from app.providers import get_topup_provider
from app.services.notification_service import notification_service
from app.services.order_service import OrderError, OrderService
from app.services.user_service import UserService
from app.utils.logger import get_logger
from app.utils.validators import normalize_uid, validate_uid

logger = get_logger(__name__)

router = Router(name="topup")

FF_CATEGORIES = {
    "diamonds": "💎 Алмазҳо",
    "vouchers": "🎟️ Ваучер / Гузарнома",
}


def _ff_category(name: str) -> str:
    lowered = name.lower()
    if "diamond" in lowered:
        return "diamonds"
    return "vouchers"

GAME_PROMPT = (
    "💎 <b>ALMAZ TJ — Донат</b>\n\n"
    "Бозиро интихоб кунед:"
)

UID_PROMPT = (
    "🎮 <b>{game_label} — ID бозигар</b>\n\n"
    "Лутфан ID (UID) бозигарро ворид кунед.\n"
    "UID одатан 8–12 рақам аст.\n\n"
    "⚠️ Паролро ҳаргиз напурсед ва нависед!"
)


def _parse_callback_id(data: str, prefix: str) -> int | None:
    try:
        return int(data.removeprefix(prefix))
    except (ValueError, AttributeError):
        return None


GAMES = set(GAME_LABELS)


async def _clear_topup_state(state: FSMContext) -> None:
    await state.clear()


def _fmt_money(value: Decimal | str | float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


async def _products_prompt(
    session: AsyncSession,
    game: str,
    db_user: User | None,
    category: str | None = None,
) -> tuple[str, list, str] | None:
    order_service = OrderService(session)
    products = await order_service.get_active_products()
    products = match_products(game, products)
    if game == "ff" and category:
        products = [p for p in products if _ff_category(p.name) == category]
    if not products:
        return None

    game_label = _catalog_game_label(game)
    balance = _fmt_money(db_user.balance) if db_user else "0.00"
    cat_label = FF_CATEGORIES.get(category or "", "")
    title = f"{game_label} — {cat_label}" if cat_label else game_label
    text = (
        f"🔥 <b>{title}</b>\n\n"
        "Маҳсулотро интихоб кунед.\n"
        f"💳 Хисоби шумо: {balance} с."
    )
    return text, products, cat_label


@router.message(Command("topup"))
@router.message(F.text == TOPUP_TEXT)
async def cmd_topup(message: Message, state: FSMContext) -> None:
    await state.set_state(TopUpStates.choosing_game)
    await message.answer(GAME_PROMPT, reply_markup=get_game_keyboard())


@router.callback_query(F.data == "menu:topup")
async def on_topup_callback(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TopUpStates.choosing_game)
    await safe_edit_text(call.message, GAME_PROMPT, reply_markup=get_game_keyboard())
    await safe_answer(call)


@router.message(TopUpStates.choosing_game, F.text == CANCEL_TEXT)
@router.message(TopUpStates.choosing_product, F.text == CANCEL_TEXT)
@router.message(TopUpStates.waiting_uid, F.text == CANCEL_TEXT)
@router.message(TopUpStates.confirming_account, F.text == CANCEL_TEXT)
@router.message(TopUpStates.confirming_order, F.text == CANCEL_TEXT)
async def cancel_topup(
    message: Message,
    state: FSMContext,
    session: AsyncSession | None = None,
) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    await _clear_topup_state(state)

    if order_id and session is not None:
        try:
            order_service = OrderService(session)
            order = await order_service.get_order(order_id)
            if order is not None and order.status == OrderStatus.PENDING:
                await order_service.transition(order_id, OrderStatus.CANCELLED)
        except Exception:
            logger.exception("Cancel order failed order_id=%s", order_id)

    await message.answer(
        "🚫 Амалиёт бекор карда шуд.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "topup:cancel")
async def cancel_topup_callback(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    await _clear_topup_state(state)

    if order_id and session is not None:
        try:
            order_service = OrderService(session)
            order = await order_service.get_order(order_id)
            if order is not None and order.status == OrderStatus.PENDING:
                await order_service.transition(order_id, OrderStatus.CANCELLED)
        except Exception:
            logger.exception("Cancel order failed order_id=%s", order_id)

    await safe_edit_text(
        call.message,
        "🚫 Амалиёт бекор карда шуд.",
        reply_markup=get_main_menu_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data.startswith("game:"))
async def on_game_selected(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
    db_user: User | None = None,
) -> None:
    game = (call.data or "").removeprefix("game:")
    if not is_known_game(game):
        await safe_answer(call, "Нодуруст.", show_alert=True)
        return

    await state.update_data(game=game, category=None)
    await state.set_state(TopUpStates.choosing_game)

    if session is None:
        await safe_answer(call, "Хатогӣ. Дубора кӯшиш кунед.", show_alert=True)
        return

    game_label = _catalog_game_label(game)

    if game == "ff":
        await state.set_state(TopUpStates.choosing_product)
        await safe_edit_text(
            call.message,
            f"🔥 <b>{game_label}</b>\n\n"
            "Гурӯҳро интихоб кунед:",
            reply_markup=get_ff_category_keyboard(),
        )
        await safe_answer(call)
        return

    try:
        result = await _products_prompt(session, game, db_user)
    except Exception:
        logger.exception("Products load failed game=%s", game)
        await safe_answer(call, "Хатогӣ. Дубора кӯшиш кунед.", show_alert=True)
        return

    if result is None:
        await state.set_state(TopUpStates.choosing_product)
        await safe_edit_text(
            call.message,
            f"😔 <b>{game_label}</b>\n\nҲоло маҳсулотҳо мавҷуд нест.\n"
            "Бозии дигарро интихоб кунед:",
            reply_markup=get_game_keyboard(),
        )
        await safe_answer(call)
        return

    text, products, _ = result
    await state.set_state(TopUpStates.choosing_product)
    await safe_edit_text(
        call.message,
        text,
        reply_markup=get_products_keyboard(
            products, back_callback="back:games"
        ),
    )
    await safe_answer(call)


@router.callback_query(F.data == "back:games")
async def on_back_games(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TopUpStates.choosing_game)
    await state.update_data(category=None, product_id=None)
    await safe_edit_text(call.message, GAME_PROMPT, reply_markup=get_game_keyboard())
    await safe_answer(call)


@router.callback_query(F.data.startswith("cat:"))
async def on_category_selected(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
    db_user: User | None = None,
) -> None:
    category = (call.data or "").removeprefix("cat:")
    if category not in FF_CATEGORIES:
        await safe_answer(call, "Нодуруст.", show_alert=True)
        return

    data = await state.get_data()
    game = data.get("game", "ff")
    if game != "ff":
        await safe_answer(call, "Нодуруст.", show_alert=True)
        return

    if session is None:
        await safe_answer(call, "Хатогӣ. Дубора кӯшиш кунед.", show_alert=True)
        return

    await state.update_data(category=category, product_id=None)
    await state.set_state(TopUpStates.choosing_product)

    try:
        result = await _products_prompt(session, game, db_user, category=category)
    except Exception:
        logger.exception(
            "Products load failed game=%s category=%s", game, category
        )
        await safe_answer(call, "Хатогӣ. Дубора кӯшиш кунед.", show_alert=True)
        return

    if result is None:
        await safe_edit_text(
            call.message,
            "😔 Дар ин гурӯҳ ҳанӯз маҳсулот нест.\n"
            "Гурӯҳро дигар интихоб кунед:",
            reply_markup=get_ff_category_keyboard(),
        )
        await safe_answer(call)
        return

    text, products, _ = result
    await safe_edit_text(
        call.message,
        text,
        reply_markup=get_products_keyboard(
            products, back_callback="back:categories"
        ),
    )
    await safe_answer(call)


@router.callback_query(F.data == "back:categories")
async def on_back_categories(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    game = data.get("game", "ff")
    await state.update_data(category=None, product_id=None)
    await state.set_state(TopUpStates.choosing_product)
    if game == "ff":
        await safe_edit_text(
            call.message,
            "🔥 <b>Free Fire</b>\n\nГурӯҳро интихоб кунед:",
            reply_markup=get_ff_category_keyboard(),
        )
    else:
        await safe_edit_text(call.message, GAME_PROMPT, reply_markup=get_game_keyboard())
    await safe_answer(call)


@router.callback_query(F.data.startswith("product:"))
async def on_product_selected(
    call: CallbackQuery,
    state: FSMContext,
) -> None:
    product_id = _parse_callback_id(call.data or "", "product:")
    if product_id is None:
        await safe_answer(call, "Нодуруст.", show_alert=True)
        return

    data = await state.get_data()
    game = data.get("game", "ff")
    game_label = _catalog_game_label(game)

    await state.update_data(product_id=product_id)
    await state.set_state(TopUpStates.waiting_uid)
    await safe_edit_text(
        call.message,
        UID_PROMPT.format(game_label=game_label),
        reply_markup=get_uid_request_keyboard(),
    )
    await safe_answer(call)


@router.message(TopUpStates.waiting_uid)
async def process_uid(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    ok, error = validate_uid(message.text or "")
    if not ok:
        await message.answer(f"❌ {error}")
        return

    uid = normalize_uid(message.text or "")
    data = await state.get_data()
    game = data.get("game", "ff")
    product_id = data.get("product_id")

    if not product_id:
        await _clear_topup_state(state)
        await message.answer(
            "❌ Маҳсулот ёфт нашуд. Дубора оғоз кунед.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    provider = get_topup_provider()
    try:
        info = await provider.lookup_account(uid, game=game)
    except NotImplementedError:
        await message.answer(
            "❌ Санҷидани ID ҳоло дастрас нест.\n"
            "Лутфан ба дастгирӣ муроҷиат кунед.",
            reply_markup=get_main_menu_keyboard(),
        )
        await _clear_topup_state(state)
        return
    except Exception:
        logger.exception("Account lookup failed uid=%s game=%s", uid, game)
        await message.answer(
            "❌ Хатогӣ ҳангоми санҷидани ID. Дубора кӯшиш кунед.",
            reply_markup=get_uid_request_keyboard(),
        )
        return

    if not info.found:
        await message.answer(
            f"❌ ID ёфт нашуд. {info.message}",
            reply_markup=get_uid_request_keyboard(),
        )
        return

    nickname = info.nickname.strip()
    await state.update_data(uid=uid, nickname=nickname or "—")
    await state.set_state(TopUpStates.confirming_account)

    if nickname:
        name_line = f"👤 Ном: <b>{nickname}</b>\n\nОё ҳамин ҳисоби шумост?"
    else:
        short_note = "Ном санҷида нашуд. Бе санҷиш ID-ро идома диҳед."
        if info.message and ("API" in info.message or "http" in info.message.lower()):
            short_note = info.message
        name_line = (
            "👤 Ном: <i>аниқланмади</i>\n"
            f"ℹ️ {short_note}\n\n"
            "Оё ҳамин ID шумост?"
        )

    await message.answer(
        "🔍 <b>Санҷидани ҳисоб</b>\n\n"
        f"🎮 Бозӣ: {info.game}\n"
        f"🆔 UID: <code>{uid}</code>\n"
        f"{name_line}",
        reply_markup=get_account_confirm_keyboard(),
    )


@router.callback_query(F.data == "account:no")
async def on_account_no(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    game = data.get("game", "ff")
    game_label = _catalog_game_label(game)
    await state.set_state(TopUpStates.waiting_uid)
    await safe_edit_text(
        call.message,
        UID_PROMPT.format(game_label=game_label),
        reply_markup=get_uid_request_keyboard(),
    )
    await safe_answer(call, "ID-и дигар ворид кунед.")


async def _show_order_confirm(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
) -> None:
    data = await state.get_data()
    product_id = data.get("product_id")
    uid = data.get("uid")
    nickname = data.get("nickname") or "—"
    game = data.get("game", "ff")
    game_label = _catalog_game_label(game)

    if not product_id or not uid:
        await _clear_topup_state(state)
        await safe_edit_text(
            call.message, GAME_PROMPT, reply_markup=get_game_keyboard()
        )
        await safe_answer(call)
        return

    order_service = OrderService(session)
    product = await order_service.get_product(product_id)
    if product is None or not product.is_active:
        await _clear_topup_state(state)
        await safe_edit_text(
            call.message,
            "😔 Ин маҳсулот дастрас нест.",
            reply_markup=get_main_menu_keyboard(),
        )
        await safe_answer(call, "Маҳсулот дастрас нест.", show_alert=True)
        return

    balance = Decimal(db_user.balance)
    price = Decimal(product.price)
    after = balance - price

    text = (
        "🧾 <b>Тасдики фармоиш</b>\n\n"
        f"📦 Маҳсулот: {format_product_button(product)}\n"
        f"🎮 Бозӣ: {game_label}\n"
        f"🆔 Гиранда: <code>{uid}</code>\n"
        f"👤 Лақаб: <b>{nickname}</b>\n\n"
        f"💳 Ҳисоби шумо: <b>{_fmt_money(balance)} {product.currency}</b>\n"
        f"📉 Пас аз харид: <b>{_fmt_money(after)} {product.currency}</b>\n\n"
        "Барои пардохт тугмаи поёнро пахш кунед."
    )
    await state.set_state(TopUpStates.confirming_order)
    await safe_edit_text(call.message, text, reply_markup=get_order_confirm_keyboard())
    await safe_answer(call)


@router.callback_query(F.data == "account:yes")
async def on_account_yes(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if db_user is None:
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return
    await _show_order_confirm(call, state, session, db_user)


@router.callback_query(F.data == "order:pay")
async def on_order_pay(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if db_user is None or session is None:
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return

    data = await state.get_data()
    product_id = data.get("product_id")
    uid = data.get("uid")
    if not product_id or not uid:
        await _clear_topup_state(state)
        await safe_edit_text(
            call.message, GAME_PROMPT, reply_markup=get_game_keyboard()
        )
        await safe_answer(call, "Маълумот ёфт нашуд.", show_alert=True)
        return

    order_service = OrderService(session)
    product = await order_service.get_product(product_id)
    if product is None or not product.is_active:
        await safe_answer(call, "Ин маҳсулот дастрас нест.", show_alert=True)
        return

    user_service = UserService(session)
    user = await user_service.get_profile(call.from_user.id)
    if user is None:
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return

    try:
        order = await order_service.create_order(
            user=user,
            product=product,
            free_fire_uid=uid,
            deduct_balance=True,
        )
    except OrderError as exc:
        await safe_answer(call, str(exc), show_alert=True)
        return

    order_id = order.id
    product_name = format_product_button(product)
    new_balance = _fmt_money(Decimal(user.balance) - Decimal(product.price))
    currency = product.currency

    await state.update_data(order_id=order_id, uid=uid, product_id=product_id)
    await _clear_topup_state(state)

    # Persist the order (and the balance deduction) BEFORE notifying admins.
    # Otherwise an error later in this handler rolls the order back while the
    # admin already has the "accept / reject" message → "Фармоиш ёфт нашуд".
    await session.commit()

    await _notify_admins_balance_order(session, order, product_name)

    text = (
        "✅ <b>Пардохт анjom ёфт!</b>\n\n"
        f"📦 Фармоиш: №{order_id}\n"
        f"🎮 {product_name}\n"
        f"🆔 UID: <code>{uid}</code>\n"
        f"💳 Ҳисоб: {new_balance} {currency}\n\n"
        "⏳ Интизори қабули идора шавед.\n"
        "Дар бораи қабул/рад ба шумо хабар дода мешавад."
    )
    await safe_edit_text(
        call.message, text, reply_markup=get_payment_receipt_keyboard(order_id)
    )
    await safe_answer(call, "Пардохт шуд!")


async def _notify_admins_balance_order(
    session: AsyncSession,
    order: Order,
    product_name: str,
) -> None:
    from app.database.models import User as UserModel

    user = await session.get(UserModel, order.user_id)
    user_label = "@?"
    if user is not None:
        user_label = f"@{user.username}" if user.username else str(user.telegram_id)

    admin_text = (
        "💰 <b>Пардохт аз баланс</b>\n\n"
        f"📦 №{order.id}\n"
        f"🎮 {product_name}\n"
        f"🆔 UID: <code>{order.free_fire_uid}</code>\n"
        f"💰 {order.amount} {order.currency}\n"
        f"👤 Клиент: {user_label}\n\n"
        "Тасдиқ ё рад кунед:"
    )
    try:
        await notification_service.notify_admins_new_order(
            admin_text,
            reply_markup=_order_review_kb(order.id),
        )
    except RuntimeError:
        logger.warning("NotificationService bot not configured")


def _order_review_kb(order_id: int):
    from app.bot.keyboards import get_order_review_keyboard

    return get_order_review_keyboard(order_id)


@router.callback_query(F.data == "order:cancel")
async def on_order_cancel(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
    db_user: User | None = None,
) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    await _clear_topup_state(state)

    if order_id and session is not None:
        order_service = OrderService(session)
        order = await order_service.get_order(order_id)
        if order is not None and order.status == OrderStatus.PENDING:
            was_deducted = await order_service.was_balance_deducted(order.id)
            await order_service.transition(order_id, OrderStatus.CANCELLED)
            if was_deducted and db_user is not None:
                user_service = UserService(session)
                await user_service.add_balance(
                    user_id=db_user.id,
                    amount=Decimal(order.amount),
                    description=f"Refund order #{order.id}",
                    reference_id=f"refund:order:{order.id}",
                )
            logger.info(
                "Order cancelled order_id=%s refunded=%s",
                order_id,
                was_deducted,
            )

    await safe_edit_text(
        call.message,
        "🚫 Фармоиш бекор карда шуд.",
        reply_markup=None,
    )
    await call.message.answer(
        "🏠 <b>Менюи ALMAZ TJ</b>",
        reply_markup=get_main_menu_keyboard(),
    )
    await safe_answer(call)
