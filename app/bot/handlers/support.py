from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import get_main_menu_keyboard
from app.bot.states import SupportStates
from app.config import settings
from app.database.models import User
from app.i18n import labels_for, t
from app.services.notification_service import notification_service
from app.utils.logger import get_logger
from app.bot.utils import safe_answer, safe_edit_text

logger = get_logger(__name__)

router = Router(name="support")


@router.message(Command("support"))
@router.message(F.text.in_(labels_for("btn.support")))
async def support_start(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportStates.waiting_subject)
    await message.answer(
        t("support.body"),
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:support")
async def support_start_callback(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SupportStates.waiting_subject)
    await safe_edit_text(call.message,
        t("support.body"),
        reply_markup=get_main_menu_keyboard(),
    )
    await safe_answer(call)


@router.message(SupportStates.waiting_subject)
async def support_subject(message: Message, state: FSMContext) -> None:
    subject = (message.text or "").strip()[:256]
    if not subject:
        await message.answer(t("support.write_subject"))
        return
    await state.update_data(subject=subject)
    await state.set_state(SupportStates.waiting_message)
    await message.answer(t("support.write_message"))


@router.message(SupportStates.waiting_message)
async def support_message(
    message: Message,
    state: FSMContext,
    session=None,
    db_user: User | None = None,
) -> None:
    body = (message.text or "").strip()
    if not body:
        await message.answer(t("support.empty_body"))
        return

    data = await state.get_data()
    subject = data.get("subject") or t("support.no_subject")

    if db_user is None or session is None:
        await state.clear()
        await message.answer(t("support.error"))
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
        t("support.created", id=ticket.id),
        reply_markup=get_main_menu_keyboard(is_admin=db_user.is_admin),
    )

    for admin_id in settings.admin_ids:
        await notification_service.safe_send(
            admin_id,
            t(
                "support.notify_admin",
                id=ticket.id,
                user=db_user.username or db_user.telegram_id,
                subject=subject,
                body=body[:500],
            ),
        )

    logger.info(
        "Support ticket created id=%s user_id=%s", ticket.id, db_user.id
    )
