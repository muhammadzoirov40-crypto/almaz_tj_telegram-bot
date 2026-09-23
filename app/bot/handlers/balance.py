from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    get_balance_cancel_keyboard,
    get_balance_confirm_keyboard,
    get_balance_keyboard,
    get_main_menu_keyboard,
    get_payment_method_keyboard,
    get_topup_amount_keyboard,
)
from app.bot.keyboards.main import BALANCE_TEXT
from app.bot.keyboards.payment import CANCEL_TOPUP_TEXT
from app.bot.states import BalanceTopUpStates
from app.database.models import User
from app.services.user_service import UserService
from app.utils.logger import get_logger
from app.bot.utils import safe_answer, safe_edit_text
from app.utils.validators import validate_phone, validate_topup_amount

logger = get_logger(__name__)

router = Router(name="balance")

PAYMENT_METHODS = {
    "card": "💳 Карти бонкӣ",
    "ds": "🏙 Dushanbe City",
}


def _balance_text(user: User) -> str:
    return (
        f"💰 <b>Баланс:</b> {user.balance} TJS\n\n"
        "Барои афзоиш «💳 Шарҷ кунед»-ро зер кунед.\n"
        "ALMAZ TJ ⚡ — 1-5 дақиқа • 100% беҳтар"
    )


async def _get_or_none_user(session, telegram_id: int) -> User | None:
    if session is None:
        return None
    return await UserService(session).get_profile(telegram_id)


async def _show_balance_message(message: Message, session, db_user=None) -> None:
    user = db_user or await _get_or_none_user(session, message.from_user.id)
    if user is None:
        await message.answer("❌ Шумо ҳанӯз сабт наштаед. /start кунед.")
        return
    await message.answer(
        _balance_text(user),
        reply_markup=get_balance_keyboard(is_admin=bool(db_user and db_user.is_admin)),
    )


@router.message(Command("balance"))
@router.message(F.text == BALANCE_TEXT)
async def on_balance(message: Message, session=None, db_user=None) -> None:
    await _show_balance_message(message, session, db_user)


@router.callback_query(F.data == "menu:balance")
async def on_balance_callback(
    call: CallbackQuery,
    state: FSMContext,
    session=None,
    db_user=None,
) -> None:
    await state.clear()
    user = db_user or await _get_or_none_user(session, call.from_user.id)
    if user is None:
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return
    await safe_edit_text(call.message, 
        _balance_text(user),
        reply_markup=get_balance_keyboard(
            is_admin=bool(db_user and db_user.is_admin)
        ),
    )
    await safe_answer(call)


@router.callback_query(F.data == "balance:topup")
async def on_balance_topup(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BalanceTopUpStates.waiting_amount)
    await safe_edit_text(call.message, 
        "💳 <b>Шарҷи баланс</b>\n\n"
        "Маблағро интихоб кунед ё рақам нависед (TJS):",
        reply_markup=get_topup_amount_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data.startswith("bal:amt:"))
async def on_amount_choice(call: CallbackQuery, state: FSMContext) -> None:
    raw = (call.data or "").removeprefix("bal:amt:")
    if raw == "custom":
        await state.set_state(BalanceTopUpStates.waiting_amount)
        await safe_edit_text(call.message, 
            "✏️ <b>Маблағ</b>\n\nМаблағро бо рақам нависед (масалан: 25):",
            reply_markup=get_balance_cancel_keyboard(),
        )
        await safe_answer(call)
        return

    ok, error, amount = validate_topup_amount(raw)
    if not ok or amount is None:
        await safe_answer(call, error or "Нодуруст.", show_alert=True)
        return

    await state.update_data(amount=str(amount))
    await state.set_state(BalanceTopUpStates.confirming)
    await _ask_payment_method(call, amount, method=None, phone=None)
    await safe_answer(call)


@router.message(BalanceTopUpStates.waiting_amount)
async def process_custom_amount(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == CANCEL_TOPUP_TEXT:
        await _cancel_balance_topup_message(message, state)
        return

    ok, error, amount = validate_topup_amount(text)
    if not ok or amount is None:
        await message.answer(f"❌ {error}", reply_markup=get_balance_cancel_keyboard())
        return

    await state.update_data(amount=str(amount))
    await state.set_state(BalanceTopUpStates.confirming)
    await message.answer(
        f"💰 Маблағ: <b>{amount} TJS</b>\n\nУсули пардохтро интихоб кунед:",
        reply_markup=get_payment_method_keyboard(),
    )


@router.callback_query(F.data.startswith("paymethod:"))
async def on_payment_method(call: CallbackQuery, state: FSMContext) -> None:
    method = (call.data or "").removeprefix("paymethod:")
    if method not in PAYMENT_METHODS:
        await safe_answer(call, "Нодуруст.", show_alert=True)
        return

    data = await state.get_data()
    amount_raw = data.get("amount")
    if not amount_raw:
        await state.clear()
        await state.set_state(BalanceTopUpStates.waiting_amount)
        await safe_edit_text(call.message, 
            "💳 <b>Шарҷи баланс</b>\n\n"
            "Маблағро интихоб кунед ё рақам нависед (TJS):",
            reply_markup=get_topup_amount_keyboard(),
        )
        await safe_answer(call, "Маблағ ворид кунед.", show_alert=True)
        return

    if method == "ds":
        await state.update_data(method=method)
        await state.set_state(BalanceTopUpStates.waiting_phone)
        await safe_edit_text(call.message, 
            "🏙 <b>Dushanbe City</b>\n\n"
            "Рақами телефони худро барои пардохт нависед.\n"
            "Масалан: <code>+992901234567</code>",
            reply_markup=get_balance_cancel_keyboard(),
        )
        await safe_answer(call)
        return

    amount = Decimal(amount_raw)
    await state.update_data(method=method, phone=None)
    await state.set_state(BalanceTopUpStates.confirming)
    await _ask_payment_method(call, amount, method=method, phone=None)
    await safe_answer(call)


@router.message(BalanceTopUpStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == CANCEL_TOPUP_TEXT:
        await _cancel_balance_topup_message(message, state)
        return

    ok, error, phone = validate_phone(text)
    if not ok or phone is None:
        await message.answer(f"❌ {error}", reply_markup=get_balance_cancel_keyboard())
        return

    data = await state.get_data()
    amount_raw = data.get("amount")
    if not amount_raw:
        await state.clear()
        await message.answer(
            "❌ Маблағ ёфт нашуд. Дубора оғоз кунед.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    await state.update_data(phone=phone, method="ds")
    await state.set_state(BalanceTopUpStates.confirming)
    amount = Decimal(amount_raw)
    await message.answer(
        _confirm_text(amount, method="ds", phone=phone),
        reply_markup=get_balance_confirm_keyboard(),
    )


def _confirm_text(amount: Decimal, method: str, phone: str | None) -> str:
    method_label = PAYMENT_METHODS.get(method, method)
    lines = [
        "🧾 <b>Тасдиқи шарҷ</b>",
        "",
        f"💰 Маблағ: <b>{amount} TJS</b>",
        f"💳 Усул: {method_label}",
    ]
    if phone:
        lines.append(f"📱 Рақам: <code>{phone}</code>")
    lines.extend(
        [
            "",
            "Пас аз тасдиқ, маблағ ба баланс илова мешавад.",
        ]
    )
    return "\n".join(lines)


async def _ask_payment_method(
    call: CallbackQuery,
    amount: Decimal,
    method: str | None,
    phone: str | None,
) -> None:
    if method and phone:
        text = _confirm_text(amount, method=method, phone=phone)
        markup = get_balance_confirm_keyboard()
    else:
        text = (
            f"💰 Маблағ: <b>{amount} TJS</b>\n\n"
            "Усули пардохтро интихоб кунед:"
        )
        markup = get_payment_method_keyboard()
    await safe_edit_text(call.message, text, reply_markup=markup)


@router.callback_query(F.data == "balance:confirm")
async def on_balance_confirm(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
    db_user: User | None = None,
) -> None:
    data = await state.get_data()
    amount_raw = data.get("amount")
    method = data.get("method") or "card"
    phone = data.get("phone")

    if not amount_raw:
        await state.clear()
        await safe_answer(call, "Маблағ ёфт нашуд.", show_alert=True)
        return

    amount = Decimal(amount_raw)
    if db_user is None:
        await state.clear()
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return

    if session is None:
        await state.clear()
        await safe_answer(call, "Хатогӣ. Дубора кӯшиш кунед.", show_alert=True)
        return

    # Idempotency: one top-up attempt = one reference; success clears state.
    reference = data.get("reference_id")
    if not reference:
        reference = f"topup:{db_user.id}:{uuid4().hex[:16]}"
        await state.update_data(reference_id=reference)

    user_service = UserService(session)
    existing = await user_service.transactions.get_by_reference_id(reference)
    if existing is not None:
        await state.clear()
        user = await user_service.get_profile(call.from_user.id)
        text = (
            "✅ <b>Шарҷ алакай иҷро шудааст.</b>\n\n"
            f"💰 Баланс: <b>{user.balance if user else amount} TJS</b>"
        )
        await safe_edit_text(call.message, 
            text, reply_markup=get_balance_keyboard(is_admin=db_user.is_admin)
        )
        await safe_answer(call)
        return

    try:
        user = await user_service.add_balance(
            user_id=db_user.id,
            amount=amount,
            description=f"Balance top-up via {method}"
            + (f" ({phone})" if phone else ""),
            reference_id=reference,
        )
    except ValueError as exc:
        logger.exception("Balance top-up failed user_id=%s", db_user.id)
        await safe_answer(call, str(exc), show_alert=True)
        return

    logger.info(
        "Balance top-up ok user_id=%s amount=%s method=%s",
        db_user.id,
        amount,
        method,
    )
    await state.clear()
    await safe_edit_text(call.message, 
        "✅ <b>Шарҷ бомуваффақият анҷом ёфт!</b>\n\n"
        f"💰 Баланс: <b>{user.balance} TJS</b>\n"
        f"💳 {PAYMENT_METHODS.get(method, method)}"
        + (f"\n📱 {phone}" if phone else ""),
        reply_markup=get_balance_keyboard(is_admin=db_user.is_admin),
    )
    await safe_answer(call, "Шарҷ шуд!")


@router.callback_query(F.data == "balance:cancel")
async def on_balance_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit_text(call.message, 
        "🚫 Шарҷ бекор карда шуд.",
        reply_markup=get_main_menu_keyboard(),
    )
    await safe_answer(call)


@router.message(BalanceTopUpStates.confirming, F.text == CANCEL_TOPUP_TEXT)
async def on_balance_cancel_message(message: Message, state: FSMContext) -> None:
    await _cancel_balance_topup_message(message, state)


async def _cancel_balance_topup_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🚫 Шарҷ бекор карда шуд.",
        reply_markup=get_main_menu_keyboard(),
    )
