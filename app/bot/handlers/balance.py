from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    get_balance_cancel_keyboard,
    get_balance_confirm_keyboard,
    get_balance_keyboard,
    get_balance_receipt_keyboard,
    get_main_menu_keyboard,
    get_payment_method_keyboard,
    get_share_phone_keyboard,
    get_topup_amount_keyboard,
    remove_reply_keyboard,
)
from app.bot.keyboards.main import BALANCE_TEXT
from app.bot.keyboards.payment import CANCEL_TOPUP_TEXT
from app.bot.states import BalanceTopUpStates
from app.bot.utils import safe_answer, safe_edit_text
from app.config import DEFAULT_PAYMENT_NUMBER, settings
from app.constants import BalanceTopUpMethod, BalanceTopUpStatus
from app.database.models import User
from app.database.repositories import BalanceTopUpRepository
from app.services.notification_service import notification_service
from app.services.user_service import UserService
from app.utils.logger import get_logger
from app.utils.validators import validate_phone, validate_topup_amount

logger = get_logger(__name__)

router = Router(name="balance")

PAYMENT_METHODS = {
    BalanceTopUpMethod.DS: "🏙 Dushanbe City",
    BalanceTopUpMethod.ALIF: "💳 Alif",
}

CARDS_DIR = Path(__file__).resolve().parents[3] / "assets" / "cards"


def _card_photo_path(method: str) -> Path | None:
    stem = "ds" if method == BalanceTopUpMethod.DS else "alif"
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = CARDS_DIR / f"{stem}{ext}"
        if path.is_file():
            return path
    return None


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
    await safe_edit_text(
        call.message,
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
    await safe_edit_text(
        call.message,
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
        await safe_edit_text(
            call.message,
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
    await safe_edit_text(
        call.message,
        f"💰 Маблағ: <b>{amount} TJS</b>\n\nУсули пардохтро интихоб кунед:",
        reply_markup=get_payment_method_keyboard(),
    )
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


def _format_payment_number(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if value.startswith("+"):
        return value
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 9:
        return f"+992 {digits}"
    return value


def _payment_number_for(method: str) -> str:
    if method == BalanceTopUpMethod.ALIF:
        raw = settings.payment_alif_number or settings.payment_card_number
    else:
        raw = (
            settings.payment_ds_card_number
            or settings.payment_ds_phone
            or settings.payment_card_number
        )
    return _format_payment_number(raw) or DEFAULT_PAYMENT_NUMBER


def _payment_url_for(method: str) -> str | None:
    if method == BalanceTopUpMethod.DS:
        return settings.payment_ds_url or None
    return None


def _payment_holder_for(method: str) -> str:
    if method == BalanceTopUpMethod.ALIF:
        return settings.payment_alif_holder or settings.payment_card_holder or ""
    return settings.payment_card_holder or ""


def _instructions_text(
    amount: Decimal,
    method: str,
    phone: str | None = None,
) -> str:
    method_label = PAYMENT_METHODS.get(method, method)
    number = _payment_number_for(method)
    holder = _payment_holder_for(method)

    lines = [
        f"💰 <b>Маблағ:</b> {amount} TJS",
        f"💳 <b>Усул:</b> {method_label}",
    ]
    if phone:
        lines.append(f"📱 <b>Рақами шумо:</b> <code>{phone}</code>")
    lines.extend(
        [
            "",
            "📄 <b>Рақами пардохт:</b>",
            f"<code>{number}</code>",
        ]
    )
    if holder:
        lines.append(f"👤 {holder}")
    lines.extend(
        [
            "",
            "1️⃣ Ба ин рақам маблағ фиристед",
            "2️⃣ Пас тугмаи «✅ Тасдиқи пардохт»-ро зер кунед",
            "3️⃣ Бот чек (расм/матн) мепурсад",
            "4️⃣ Чекро фиристед → админ санҷида, баланс илова мекунад",
        ]
    )
    return "\n".join(lines)


async def _show_payment_instructions(
    call: CallbackQuery,
    state: FSMContext,
    amount: Decimal,
    method: str,
) -> None:
    method_label = PAYMENT_METHODS.get(method, method)
    text = _instructions_text(amount, method)

    await state.update_data(method=method, amount=str(amount))
    await state.set_state(BalanceTopUpStates.confirming)

    photo = _card_photo_path(method)
    if photo:
        await safe_edit_text(
            call.message,
            f"💳 <b>Усул: {method_label}</b>\n\n👇 Расми картаро нигаред:",
            reply_markup=None,
        )
        await call.message.answer_photo(
            FSInputFile(photo),
            caption=text,
            reply_markup=get_balance_confirm_keyboard(
                url=_payment_url_for(method)
            ),
        )
    else:
        await safe_edit_text(
            call.message,
            text,
            reply_markup=get_balance_confirm_keyboard(
                url=_payment_url_for(method)
            ),
        )


@router.callback_query(F.data.startswith("paymethod:"))
async def on_payment_method(call: CallbackQuery, state: FSMContext) -> None:
    method_raw = (call.data or "").removeprefix("paymethod:")
    method = BalanceTopUpMethod(method_raw) if method_raw in {
        m.value for m in BalanceTopUpMethod
    } else None
    if method is None:
        await safe_answer(call, "Нодуруст.", show_alert=True)
        return

    data = await state.get_data()
    amount_raw = data.get("amount")
    if not amount_raw:
        await state.clear()
        await state.set_state(BalanceTopUpStates.waiting_amount)
        await safe_edit_text(
            call.message,
            "💳 <b>Шарҷи баланс</b>\n\n"
            "Маблағро интихоб кунед ё рақам нависед (TJS):",
            reply_markup=get_topup_amount_keyboard(),
        )
        await safe_answer(call, "Маблағ ворид кунед.", show_alert=True)
        return

    amount = Decimal(amount_raw)

    if method == BalanceTopUpMethod.DS:
        await state.update_data(method=method.value)
        await state.set_state(BalanceTopUpStates.waiting_phone)
        phone_request = (
            "🏙 <b>Dushanbe City</b>\n\n"
            "📱 Тугмаи зеринро зер кунед ва <b>рақами худатон</b>-ро "
            "фиристед (Telegram рақами шуморо мефиристад).\n\n"
            "Ё рақамро бо даст нависед: <code>+992002119831</code>"
        )
        photo = _card_photo_path(method.value)
        if photo:
            # Card photo carries the phone-request caption + reply keyboard
            await safe_edit_text(
                call.message,
                "🏙 <b>Усул: Dushanbe City</b>\n\n👇 Расми картаро нигаред:",
                reply_markup=None,
            )
            await call.message.answer_photo(
                FSInputFile(photo),
                caption=phone_request,
                reply_markup=get_share_phone_keyboard(),
            )
        else:
            # Inline buttons are removed; reply keyboard asks for the user's own number
            await safe_edit_text(call.message, phone_request, reply_markup=None)
            await call.message.answer(
                "Рақами худатонро интихоб кунед:",
                reply_markup=get_share_phone_keyboard(),
            )
        await safe_answer(call)
        return

    # Alif — no phone required, show payment number immediately
    await state.update_data(method=method.value, phone=None)
    await _show_payment_instructions(call, state, amount, method.value)


async def _finish_phone(
    message: Message,
    state: FSMContext,
    phone: str,
) -> None:
    data = await state.get_data()
    amount_raw = data.get("amount")
    if not amount_raw:
        await state.clear()
        await message.answer(
            "❌ Маблағ ёфт нашуд. Дубора оғоз кунед.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    amount = Decimal(amount_raw)
    await state.update_data(phone=phone, method=BalanceTopUpMethod.DS.value)
    await state.set_state(BalanceTopUpStates.confirming)

    text = _instructions_text(amount, BalanceTopUpMethod.DS.value, phone=phone)

    await message.answer(
        text,
        reply_markup=get_balance_confirm_keyboard(
            url=_payment_url_for(BalanceTopUpMethod.DS.value)
        ),
    )


@router.message(BalanceTopUpStates.waiting_phone, F.contact)
async def process_contact_phone(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if contact is None or not contact.phone_number:
        await message.answer(
            "❌ Рақам ёфт нашуд. Тугмаи «Рақами худамро фиристодан»-ро зер кунед.",
            reply_markup=get_share_phone_keyboard(),
        )
        return

    # Must be the user's own contact (not someone else's)
    if contact.user_id and message.from_user and contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Лутфан <b>рақами худатон</b>-ро фиристед.",
            reply_markup=get_share_phone_keyboard(),
        )
        return

    ok, error, phone = validate_phone(contact.phone_number)
    if not ok or phone is None:
        await message.answer(
            f"❌ {error}\n"
            "Дар Telegram Settings → Profile бояд рақами телефон дошта бошед.",
            reply_markup=get_share_phone_keyboard(),
        )
        return

    await message.answer(
        "✅ Рақам қабул шуд.",
        reply_markup=remove_reply_keyboard(),
    )
    await _finish_phone(message, state, phone)


@router.message(BalanceTopUpStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == CANCEL_TOPUP_TEXT:
        await state.clear()
        await message.answer(
            "🚫 Шарҷ бекор карда шуд.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    ok, error, phone = validate_phone(text)
    if not ok or phone is None:
        await message.answer(
            f"❌ {error}\n\n"
            "Тугмаи «📱 Рақами худамро фиристодан»-ро зер кунед "
            "ё рақами тоҷикӣ нависед.",
            reply_markup=get_share_phone_keyboard(),
        )
        return

    await message.answer(
        "✅ Рақам қабул шуд.",
        reply_markup=remove_reply_keyboard(),
    )
    await _finish_phone(message, state, phone)


@router.callback_query(F.data == "balance:confirm")
async def on_balance_confirm(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
    db_user: User | None = None,
) -> None:
    data = await state.get_data()
    amount_raw = data.get("amount")
    method = data.get("method") or BalanceTopUpMethod.ALIF.value
    phone = data.get("phone")

    if not amount_raw:
        await state.clear()
        await safe_answer(call, "Маблағ ёфт нашуд.", show_alert=True)
        return

    if db_user is None:
        await state.clear()
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return

    if session is None:
        await state.clear()
        await safe_answer(call, "Хатогӣ. Дубора кӯшиш кунед.", show_alert=True)
        return

    amount = Decimal(amount_raw)
    reference = data.get("reference_id")
    if not reference:
        reference = f"bal:{db_user.id}:{uuid4().hex[:16]}"

    repo = BalanceTopUpRepository(session)
    existing = await repo.get_by_reference_id(reference)
    if existing is not None and existing.status != BalanceTopUpStatus.PENDING:
        await state.clear()
        await safe_answer(call, "Ин дархост алакай коркард шудааст.", show_alert=True)
        return

    if existing is None:
        request = await repo.create(
            user_id=db_user.id,
            amount=amount,
            method=method,
            phone=phone,
            reference_id=reference,
        )
    else:
        request = existing

    await state.update_data(
        reference_id=reference,
        topup_request_id=request.id,
        amount=str(amount),
        method=method,
        phone=phone,
    )
    await state.set_state(BalanceTopUpStates.waiting_receipt)

    method_label = PAYMENT_METHODS.get(method, method)
    text = (
        "📸 <b>Чеки пардохт фиристед</b>\n\n"
        f"📦 Дархост: №{request.id}\n"
        f"💰 Маблағ: <b>{amount} TJS</b>\n"
        f"💳 Усул: {method_label}\n"
        + (f"📱 Телефон: <code>{phone}</code>\n" if phone else "")
        + "\n"
        "Рақами пардохт: "
        f"<code>{_payment_number_for(method)}</code>\n\n"
        "Лутфан <b>расми чек</b> ё <b>матни чек</b> фиристед.\n"
        "Идора чекро санҷида, ба баланс илова мекунад."
    )
    await safe_edit_text(call.message, text, reply_markup=get_balance_receipt_keyboard())
    await safe_answer(call, "Чекро фиристед")


async def _send_topup_to_admin(
    session: AsyncSession,
    request_id: int,
    db_user: User | None,
    photo_file_id: str | None = None,
    receipt_text: str | None = None,
) -> None:
    repo = BalanceTopUpRepository(session)
    request = await repo.get_by_id(request_id)
    if request is None:
        return

    method_label = PAYMENT_METHODS.get(request.method, request.method)
    user_label = "@?"
    if request.user is not None:
        user_label = (
            f"@{request.user.username}"
            if request.user.username
            else str(request.user.telegram_id)
        )
    elif db_user is not None:
        user_label = f"@{db_user.username}" if db_user.username else str(db_user.telegram_id)

    lines = [
        "📩 <b>Чеки шарҷи баланс</b>",
        "",
        f"📦 Дархост: №{request.id}",
        f"💰 Маблағ: <b>{request.amount} {request.currency}</b>",
        f"💳 Усул: {method_label}",
    ]
    if request.phone:
        lines.append(f"📱 Телефон: <code>{request.phone}</code>")
    lines.append(f"👤 Клиент: {user_label}")
    if request.reference_id:
        lines.append(f"🆔 Ref: <code>{request.reference_id}</code>")
    if receipt_text:
        lines.extend(["", f"✉️ Чек:\n{receipt_text[:400]}"])
    lines.extend(["", "Қабул ё рад кунед:"])

    from app.bot.keyboards import get_balance_topup_review_keyboard

    # Persist the receipt before notifying admins: if anything fails later the
    # transaction is rolled back and the admin would hold a message for a
    # request that no longer exists.
    await session.commit()

    try:
        await notification_service.notify_admins_new_order(
            "\n".join(lines),
            reply_markup=get_balance_topup_review_keyboard(request.id),
            photo=photo_file_id,
        )
    except RuntimeError:
        logger.warning("NotificationService bot not configured")


@router.message(BalanceTopUpStates.waiting_receipt, F.photo)
async def on_balance_receipt_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    data = await state.get_data()
    request_id = data.get("topup_request_id")
    if not request_id:
        await state.clear()
        await message.answer(
            "❌ Дархост ёфт нашуд. Дубора оғоз кунед.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    photo_file_id = message.photo[-1].file_id
    repo = BalanceTopUpRepository(session)
    await repo.set_receipt(request_id, photo_file_id=photo_file_id)
    await _send_topup_to_admin(
        session, request_id, db_user, photo_file_id=photo_file_id
    )
    await state.clear()

    await message.answer(
        "✅ <b>Чек қабул шуд</b>\n\n"
        f"📦 Дархост: №{request_id}\n\n"
        "Идора чекро санҷида, ба баланс илова мекунад.\n"
        "Дар бораи қабул/рад ба шумо хабар дода мешавад.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(BalanceTopUpStates.waiting_receipt)
async def on_balance_receipt_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    text = (message.text or "").strip()
    if text == CANCEL_TOPUP_TEXT:
        await _cancel_balance_topup_message(message, state)
        return

    data = await state.get_data()
    request_id = data.get("topup_request_id")
    if not request_id:
        await state.clear()
        await message.answer(
            "❌ Дархост ёфт нашуд. Дубора оғоз кунед.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    receipt_text = text[:500]
    repo = BalanceTopUpRepository(session)
    await repo.set_receipt(request_id, receipt_text=receipt_text)
    await _send_topup_to_admin(
        session, request_id, db_user, receipt_text=receipt_text
    )
    await state.clear()

    await message.answer(
        "✅ <b>Чек қабул шуд</b>\n\n"
        f"📦 Дархост: №{request_id}\n\n"
        "Идора чекро санҷида, ба баланс илова мекунад.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "balance:cancel")
async def on_balance_cancel(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession | None = None,
) -> None:
    data = await state.get_data()
    request_id = data.get("topup_request_id")
    if request_id and session is not None:
        repo = BalanceTopUpRepository(session)
        request = await repo.get_by_id(request_id)
        if request is not None and request.status == BalanceTopUpStatus.PENDING:
            await repo.mark_cancelled(request_id)

    await state.clear()
    await safe_edit_text(
        call.message,
        "🚫 Шарҷ бекор карда шуд.",
        reply_markup=get_main_menu_keyboard(),
    )
    await safe_answer(call)


@router.message(BalanceTopUpStates.confirming, F.text == CANCEL_TOPUP_TEXT)
@router.message(BalanceTopUpStates.waiting_receipt, F.text == CANCEL_TOPUP_TEXT)
async def on_balance_cancel_message(
    message: Message, state: FSMContext, session=None
) -> None:
    await _cancel_balance_topup_message(message, state, session)


async def _cancel_balance_topup_message(
    message: Message, state: FSMContext, session=None
) -> None:
    data = await state.get_data()
    request_id = data.get("topup_request_id")
    if request_id and session is not None:
        repo = BalanceTopUpRepository(session)
        request = await repo.get_by_id(request_id)
        if request is not None and request.status == BalanceTopUpStatus.PENDING:
            await repo.mark_cancelled(request_id)
    await state.clear()
    await message.answer(
        "🚫 Шарҷ бекор карда шуд.",
        reply_markup=get_main_menu_keyboard(),
    )
    if request_id:
        logger.info("Balance topup cancelled by user request_id=%s", request_id)
