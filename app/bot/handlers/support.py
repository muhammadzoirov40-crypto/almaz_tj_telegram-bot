from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import get_main_menu_keyboard
from app.bot.keyboards.main import SUPPORT_TEXT
from app.bot.states import SupportStates
from app.config import settings
from app.database.models import User
from app.services.notification_service import notification_service
from app.utils.logger import get_logger
from app.bot.utils import safe_answer, safe_edit_text

logger = get_logger(__name__)

router = Router(name="support")


@router.message(Command("support"))
@router.message(F.text == SUPPORT_TEXT)
async def support_start(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportStates.waiting_subject)
    await message.answer(
        "📞 <b>Дастгирӣ — DANAT.TJ</b>\n\n"
        "Мавзӯи муроҷиататонро нависед (масалан: Пардохт, Донат, Дигар).\n"
        "Ё ба админ нависед: <a href=\"https://t.me/Muhammad_beckend\">@Muhammad_beckend</a>"
    )


@router.callback_query(F.data == "menu:support")
async def support_start_callback(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SupportStates.waiting_subject)
    await safe_edit_text(call.message, 
        "📞 <b>Дастгирӣ — DANAT.TJ</b>\n\n"
        "Мавзӯи муроҷиататонро нависед (масалан: Пардохт, Донат, Дигар).\n"
        "Ё ба админ нависед: <a href=\"https://t.me/Muhammad_beckend\">@Muhammad_beckend</a>"
    )
    await safe_answer(call)


@router.message(SupportStates.waiting_subject)
async def support_subject(message: Message, state: FSMContext) -> None:
    subject = (message.text or "").strip()[:256]
    if not subject:
        await message.answer("Лутфан мавзӯро нависед.")
        return
    await state.update_data(subject=subject)
    await state.set_state(SupportStates.waiting_message)
    await message.answer(
        "✉️ Хулосаи муамморо нависед:"
    )


@router.message(SupportStates.waiting_message)
async def support_message(
    message: Message,
    state: FSMContext,
    session=None,
    db_user: User | None = None,
) -> None:
    body = (message.text or "").strip()
    if not body:
        await message.answer("Матн холӣ аст. Дубора нависед.")
        return

    data = await state.get_data()
    subject = data.get("subject", "Бе мавзӯъ")

    if db_user is None or session is None:
        await state.clear()
        await message.answer("❌ Хатогӣ. /start кунед.")
        return

    from app.database.repositories import SupportTicketRepository

    repo = SupportTicketRepository(session)
    ticket = await repo.create(
        user_id=db_user.id,
        subject=subject,
        message=body,
    )
    await state.clear()

    await message.answer(
        f"✅ Муроҷиат №{ticket.id} қабул шуд.\n"
        "Дастгирӣ дар вақти наздик ҷавоб медиҳад.",
        reply_markup=get_main_menu_keyboard(is_admin=db_user.is_admin),
    )

    for admin_id in settings.admin_ids:
        await notification_service.safe_send(
            admin_id,
            "📞 Муроҷиати нав ба дастгирӣ\n"
            f"🆔 №{ticket.id}\n"
            f"👤 {db_user.username or db_user.telegram_id}\n"
            f"📌 {subject}\n"
            f"✉️ {body[:500]}",
        )

    logger.info(
        "Support ticket created id=%s user_id=%s", ticket.id, db_user.id
    )
