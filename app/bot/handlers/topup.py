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
from app.bot.states import TopUpStates
from app.bot.utils import safe_answer, safe_edit_text
from app.constants import OrderStatus
from app.constants.games import (
    GAME_LABELS,
    game_label as _catalog_game_label,
    game_needs_zone,
    is_known_game,
    match_products,
)
from app.database.models import Order, User
from app.i18n import labels_for, t
from app.providers import get_topup_provider
from app.services.notification_service import notification_service
from app.services.order_service import OrderError, OrderService
from app.services.user_service import UserService
from app.utils.logger import get_logger
from app.utils.validators import (
    normalize_uid,
    normalize_zone,
    validate_uid,
    validate_zone,
)

logger = get_logger(__name__)

router = Router(name="topup")

FF_CATEGORIES = {
    "diamonds": "diamonds",
    "vouchers": "vouchers",
}


def _ff_category_label(category: str) -> str:
    key = "btn.diamonds" if category == "diamonds" else "btn.vouchers"
    return t(key)


def _ff_category(name: str) -> str:
    lowered = name.lower()
    if "diamond" in lowered:
        return "diamonds"
    return "vouchers"

def _game_prompt(db_user: User | None) -> str:
    """Game selection screen, with the user's balance when known."""
    base = t("top.game_prompt")
    if db_user is None:
        return base
    return (
        f"{base}\n\n"
        + t("top.balance_line", balance=_fmt_money(db_user.balance))
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
    cat_label = _ff_category_label(category) if category else ""
    title = f"{game_label} — {cat_label}" if cat_label else game_label
    text = (
        f"🔥 <b>{title}</b>\n\n"
        + t("top.pick_product")
        + "\n"
        + t("top.balance_line", balance=balance)
    )
    return text, products, cat_label


@router.message(Command("topup"))
@router.message(F.text.in_(labels_for("btn.donate")))
async def cmd_topup(
    message: Message,
    state: FSMContext,
    db_user: User | None = None,
) -> None:
    await state.set_state(TopUpStates.choosing_game)
    await message.answer(
        _game_prompt(db_user), reply_markup=get_game_keyboard()
    )


@router.callback_query(F.data == "menu:topup")
async def on_topup_callback(
    call: CallbackQuery,
    state: FSMContext,
    db_user: User | None = None,
) -> None:
    await state.clear()
    await state.set_state(TopUpStates.choosing_game)
    await safe_edit_text(
        call.message, _game_prompt(db_user), reply_markup=get_game_keyboard()
    )
    await safe_answer(call)


@router.message(TopUpStates.choosing_game, F.text.in_(labels_for("btn.cancel")))
@router.message(TopUpStates.choosing_product, F.text.in_(labels_for("btn.cancel")))
@router.message(TopUpStates.waiting_uid, F.text.in_(labels_for("btn.cancel")))
@router.message(TopUpStates.waiting_zone, F.text.in_(labels_for("btn.cancel")))
@router.message(TopUpStates.confirming_account, F.text.in_(labels_for("btn.cancel")))
@router.message(TopUpStates.confirming_order, F.text.in_(labels_for("btn.cancel")))
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
        t("top.cancelled"),
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
        t("top.cancelled"),
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
        await safe_answer(call, t("bal.invalid"), show_alert=True)
        return

    await state.update_data(game=game, category=None)
    await state.set_state(TopUpStates.choosing_game)

    if session is None:
        await safe_answer(call, t("bal.error"), show_alert=True)
        return

    game_label = _catalog_game_label(game)

    if game == "ff":
        await state.set_state(TopUpStates.choosing_product)
        await safe_edit_text(
            call.message,
            f"🔥 <b>{game_label}</b>\n\n"
            + t("top.choose_category"),
            reply_markup=get_ff_category_keyboard(),
        )
        await safe_answer(call)
        return

    try:
        result = await _products_prompt(session, game, db_user)
    except Exception:
        logger.exception("Products load failed game=%s", game)
        await safe_answer(call, t("bal.error"), show_alert=True)
        return

    if result is None:
        await state.set_state(TopUpStates.choosing_product)
        await safe_edit_text(
            call.message,
            f"😔 <b>{game_label}</b>\n\n"
            + t("top.no_products"),
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
async def on_back_games(
    call: CallbackQuery,
    state: FSMContext,
    db_user: User | None = None,
) -> None:
    await state.set_state(TopUpStates.choosing_game)
    await state.update_data(category=None, product_id=None)
    await safe_edit_text(
        call.message, _game_prompt(db_user), reply_markup=get_game_keyboard()
    )
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
        await safe_answer(call, t("bal.invalid"), show_alert=True)
        return

    data = await state.get_data()
    game = data.get("game", "ff")
    if game != "ff":
        await safe_answer(call, t("bal.invalid"), show_alert=True)
        return

    if session is None:
        await safe_answer(call, t("bal.error"), show_alert=True)
        return

    await state.update_data(category=category, product_id=None)
    await state.set_state(TopUpStates.choosing_product)

    try:
        result = await _products_prompt(session, game, db_user, category=category)
    except Exception:
        logger.exception(
            "Products load failed game=%s category=%s", game, category
        )
        await safe_answer(call, t("bal.error"), show_alert=True)
        return

    if result is None:
        await safe_edit_text(
            call.message,
            t("top.no_products_group"),
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
async def on_back_categories(
    call: CallbackQuery,
    state: FSMContext,
    db_user: User | None = None,
) -> None:
    data = await state.get_data()
    game = data.get("game", "ff")
    await state.update_data(category=None, product_id=None)
    await state.set_state(TopUpStates.choosing_product)
    if game == "ff":
        await safe_edit_text(
            call.message,
            "🔥 <b>Free Fire</b>\n\n" + t("top.choose_category"),
            reply_markup=get_ff_category_keyboard(),
        )
    else:
        await safe_edit_text(
            call.message, _game_prompt(db_user), reply_markup=get_game_keyboard()
        )
    await safe_answer(call)


@router.callback_query(F.data == "back:products")
async def on_back_products(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
    db_user: User | None = None,
) -> None:
    data = await state.get_data()
    game = data.get("game", "ff")
    category = data.get("category")
    await state.update_data(product_id=None)
    await state.set_state(TopUpStates.choosing_product)

    if game == "ff" and not category:
        await safe_edit_text(
            call.message,
            "🔥 <b>Free Fire</b>\n\n" + t("top.choose_category"),
            reply_markup=get_ff_category_keyboard(),
        )
        await safe_answer(call)
        return

    if session is None:
        await safe_answer(call, t("bal.error"), show_alert=True)
        return

    result = await _products_prompt(session, game, db_user, category=category)
    if result is None:
        await safe_edit_text(
            call.message, _game_prompt(db_user), reply_markup=get_game_keyboard()
        )
        await safe_answer(call)
        return

    text, products, _ = result
    back_callback = (
        "back:categories" if game == "ff" and category else "back:games"
    )
    await safe_edit_text(
        call.message,
        text,
        reply_markup=get_products_keyboard(
            products, back_callback=back_callback
        ),
    )
    await safe_answer(call)


@router.callback_query(F.data == "back:uid")
async def on_back_uid(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    game = data.get("game", "ff")
    game_label = _catalog_game_label(game)
    await state.set_state(TopUpStates.waiting_uid)
    await safe_edit_text(
        call.message,
        t("top.uid_prompt", game_label=game_label),
        reply_markup=get_uid_request_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data.startswith("product:"))
async def on_product_selected(
    call: CallbackQuery,
    state: FSMContext,
) -> None:
    product_id = _parse_callback_id(call.data or "", "product:")
    if product_id is None:
        await safe_answer(call, t("bal.invalid"), show_alert=True)
        return

    data = await state.get_data()
    game = data.get("game", "ff")
    game_label = _catalog_game_label(game)

    await state.update_data(product_id=product_id)
    await state.set_state(TopUpStates.waiting_uid)
    await safe_edit_text(
        call.message,
        t("top.uid_prompt", game_label=game_label),
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
            t("top.product_not_found"),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    provider = get_topup_provider()
    try:
        info = await provider.lookup_account(uid, game=game)
    except NotImplementedError:
        await message.answer(
            t("top.uid_lookup_unavailable"),
            reply_markup=get_main_menu_keyboard(),
        )
        await _clear_topup_state(state)
        return
    except Exception:
        logger.exception("Account lookup failed uid=%s game=%s", uid, game)
        await message.answer(
            t("top.uid_lookup_error"),
            reply_markup=get_uid_request_keyboard(),
        )
        return

    if not info.found:
        await message.answer(
            f"{t('top.uid_not_found')} {info.message}".rstrip(),
            reply_markup=get_uid_request_keyboard(),
        )
        return

    nickname = info.nickname.strip()
    game_label = _catalog_game_label(game)
    if nickname:
        name_line = t("top.name_line", nickname=nickname)
    else:
        short_note = t("top.name_not_checked")
        if info.message and ("API" in info.message or "http" in info.message.lower()):
            short_note = info.message
        name_line = t("top.name_unknown", note=short_note)

    await state.update_data(
        uid=uid,
        nickname=nickname or "—",
        zone=None,
        verify_game=info.game or game_label,
        name_line=name_line,
    )

    # MLBB (FireLoot) needs the zone/server id on the order payload.
    if game_needs_zone(game):
        await state.set_state(TopUpStates.waiting_zone)
        await message.answer(
            t("top.zone_prompt", game_label=game_label),
            reply_markup=get_uid_request_keyboard(),
        )
        return

    await _send_account_verify(message, state)


async def _send_account_verify(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(TopUpStates.confirming_account)
    await message.answer(
        t(
            "top.verify",
            game=data.get("verify_game") or "",
            uid=data.get("uid") or "",
            name=data.get("name_line") or "",
        ),
        reply_markup=get_account_confirm_keyboard(),
    )


@router.message(TopUpStates.waiting_zone)
async def process_zone(message: Message, state: FSMContext) -> None:
    ok, error = validate_zone(message.text or "")
    if not ok:
        await message.answer(error or t("val.zone_invalid"))
        return

    await state.update_data(zone=normalize_zone(message.text or ""))
    await _send_account_verify(message, state)


@router.callback_query(F.data == "account:no")
async def on_account_no(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    game = data.get("game", "ff")
    game_label = _catalog_game_label(game)
    await state.set_state(TopUpStates.waiting_uid)
    await safe_edit_text(
        call.message,
        t("top.uid_prompt", game_label=game_label),
        reply_markup=get_uid_request_keyboard(),
    )
    await safe_answer(call, t("top.enter_other_id"))


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
            call.message, _game_prompt(db_user), reply_markup=get_game_keyboard()
        )
        await safe_answer(call)
        return

    order_service = OrderService(session)
    product = await order_service.get_product(product_id)
    if product is None or not product.is_active:
        await _clear_topup_state(state)
        await safe_edit_text(
            call.message,
            t("top.product_unavailable"),
            reply_markup=get_main_menu_keyboard(),
        )
        await safe_answer(call, t("top.product_unavailable_alert"), show_alert=True)
        return

    balance = Decimal(db_user.balance)
    price = Decimal(product.price)
    after = balance - price

    text = t(
        "top.order_confirm",
        product=format_product_button(product),
        game=game_label,
        uid=uid,
        nickname=nickname,
        balance=_fmt_money(balance),
        currency=product.currency,
        after=_fmt_money(after),
    )
    zone = data.get("zone")
    if zone:
        text += "\n" + t("top.zone_line", zone=zone)
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
        await safe_answer(call, t("alert.not_registered"), show_alert=True)
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
        await safe_answer(call, t("alert.not_registered"), show_alert=True)
        return

    data = await state.get_data()
    product_id = data.get("product_id")
    uid = data.get("uid")
    if not product_id or not uid:
        await _clear_topup_state(state)
        await safe_edit_text(
            call.message, _game_prompt(db_user), reply_markup=get_game_keyboard()
        )
        await safe_answer(call, t("top.data_not_found"), show_alert=True)
        return

    order_service = OrderService(session)
    product = await order_service.get_product(product_id)
    if product is None or not product.is_active:
        await safe_answer(call, t("top.product_unavailable_alert"), show_alert=True)
        return

    user_service = UserService(session)
    user = await user_service.get_profile(call.from_user.id)
    if user is None:
        await safe_answer(call, t("alert.not_registered"), show_alert=True)
        return

    try:
        order = await order_service.create_order(
            user=user,
            product=product,
            free_fire_uid=uid,
            zone=data.get("zone"),
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

    text = t(
        "top.paid",
        id=order_id,
        product=product_name,
        uid=uid,
        balance=new_balance,
        currency=currency,
    )
    await safe_edit_text(
        call.message, text, reply_markup=get_payment_receipt_keyboard(order_id)
    )
    await safe_answer(call, t("top.paid_alert"))


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

    admin_text = t(
        "top.admin_order",
        id=order.id,
        product=product_name,
        uid=order.free_fire_uid,
        amount=order.amount,
        currency=order.currency,
        user=user_label,
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
        t("top.order_cancelled"),
        reply_markup=None,
    )
    await call.message.answer(
        t("menu.title"),
        reply_markup=get_main_menu_keyboard(),
    )
    await safe_answer(call)
