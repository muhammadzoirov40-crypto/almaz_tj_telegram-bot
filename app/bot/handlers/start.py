from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import ChatMemberUpdated, Message

from app.bot.keyboards import get_main_menu_keyboard, get_subscribe_keyboard
from app.bot.utils import safe_answer, safe_edit_text
from app.services.subscribe_service import is_subscribed
from app.services.user_service import UserService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = Router(name="start")

START_TEXT = (
    "Салом, хуш омадед ба боти DANAT.TJ 🏆\n\n"
    "Арзонтарин алмаз дар Тоҷикистон\n"
    "Free Fire • PUBG • Mobile Legends\n"
    "ва дигар бозиҳо\n"
    "1-5 дақиқа • 100% беҳтар\n\n"
)

START_FOOTER = "Лутфан аз менюи зерин интихоб кунед:"

SUBSCRIBE_TEXT = (
    "👋 Пеш аз оғоз ба канал мо обуна шавед!\n\n"
    "1️⃣ Каналро кушоед ва тугмаи «Подписаться»-ро пахш кунед\n"
    "2️⃣ Баъд тугмаи «✅ Проверить»-ро пахш кунед\n\n"
    "Обуна шудед → менюи бот кушода мешавад."
)


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

    bot = message.bot
    if bot is not None and not await is_subscribed(bot, user.telegram_id):
        await message.answer(
            SUBSCRIBE_TEXT, reply_markup=get_subscribe_keyboard()
        )
        return

    await message.answer(
        START_TEXT + _user_block(user) + START_FOOTER,
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin),
    )


@router.callback_query(F.data == "sub:check")
async def on_subscribe_check(
    call: CallbackQuery,
    db_user=None,  # injected by UserMiddleware
    session=None,  # injected by DatabaseMiddleware
) -> None:
    bot = call.bot
    if bot is not None and not await is_subscribed(bot, call.from_user.id):
        await safe_answer(
            call,
            "Шумо ҳанӯз обуна нестед. Каналро обуна шавед.",
            show_alert=True,
        )
        return

    user = db_user
    if user is None and session is not None:
        user, _ = await UserService(session).register_user(
            telegram_id=call.from_user.id,
            username=call.from_user.username,
            first_name=call.from_user.first_name,
            is_admin=False,
        )

    await safe_answer(call, "Обуна тасдиқ шуд!")
    text = START_TEXT + (_user_block(user) if user else "") + START_FOOTER
    markup = get_main_menu_keyboard(
        is_admin=user.is_admin if user else False
    )
    edited = await safe_edit_text(call.message, text, reply_markup=markup)
    if not edited and call.message is not None:
        await call.message.answer(text, reply_markup=markup)


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


@router.my_chat_member()
async def on_chat_member_update(event: ChatMemberUpdated) -> None:
    """Log chat id when bot is added to a channel (used to set OTZIF_CHANNEL_ID)."""
    logger.info(
        "Chat member update: chat_id=%s type=%s status=%s by=%s",
        event.chat.id,
        event.chat.type,
        event.new_chat_member.status,
        event.from_user.id if event.from_user else None,
    )
