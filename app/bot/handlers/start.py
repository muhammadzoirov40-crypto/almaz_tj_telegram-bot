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
    "🎮 <b>ALMAZ TJ ⚡</b>\n\n"
    "Арзонтарин алмаз дар Тоҷикистон\n"
    "Free Fire • PUBG • Stars\n"
    "ва дигар бозиҳо\n"
    "1-5 дақиқа • 100% беҳтар\n\n"
    "📢 Канал: <a href=\"https://t.me/_ff_almaz_tj_\">@_ff_almaz_tj_</a>\n"
    "👤 Muhammad: <a href=\"tel:+992002119831\">+992 002119831</a>\n\n"
    "Лутфан аз менюи зерин интихоб кунед:"
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
        START_TEXT,
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin),
    )


@router.message(Command("menu"))
@router.message(F.text == "🏠 Асосӣ")
async def cmd_menu(message: Message, db_user=None) -> None:
    is_admin = db_user.is_admin if db_user else False
    await message.answer(
        "🏠 <b>Менюи ALMAZ TJ</b>",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
