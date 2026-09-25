from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.keyboards import get_main_menu_keyboard
from app.services.user_service import UserService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = Router(name="start")

START_TEXT = (
    "🎮 <b>DANAT.TJ ⚡</b>\n\n"
    "Арзонтарин алмаз дар Тоҷикистон\n"
    "Free Fire • PUBG • Stars\n"
    "ва дигар бозиҳо\n"
    "1-5 дақиқа • 100% беҳтар\n\n"
)

START_FOOTER = "Лутфан аз менюи зерин интихоб кунед:"


def _user_block(user) -> str:
    name = user.first_name or user.username or "—"
    return (
        f"👤 Ном: <b>{name}</b>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"💰 Баланс: <b>{user.balance} TJS</b>\n\n"
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    db_user=None,  # injected by UserMiddleware
    session=None,  # injected by DatabaseMiddleware
) -> None:
    user_service = UserService(session)
    user, created = await user_service.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        is_admin=db_user.is_admin if db_user else False,
    )
    if created:
        logger.info("User created via /start telegram_id=%s", message.from_user.id)

    await message.answer(
        START_TEXT + _user_block(user) + START_FOOTER,
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin),
    )


@router.message(Command("menu"))
@router.message(F.text == "🏠 Асосӣ")
async def cmd_menu(message: Message, db_user=None) -> None:
    is_admin = db_user.is_admin if db_user else False
    text = "🏠 <b>Менюи DANAT.TJ</b>\n\n"
    if db_user:
        text = text + _user_block(db_user)
    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
