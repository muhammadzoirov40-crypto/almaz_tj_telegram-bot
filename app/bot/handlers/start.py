from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from app.bot.keyboards import (
    get_language_keyboard,
    get_main_menu_keyboard,
    get_subscribe_keyboard,
)
from app.bot.keyboards.main import LANGUAGE_CALLBACK, SUBSCRIBE_CALLBACK
from app.bot.utils import safe_answer, safe_edit_text
from app.database.repositories import UserRepository
from app.i18n import LANGS, labels_for, set_lang, t
from app.services.subscribe_service import is_subscribed
from app.services.user_service import UserService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = Router(name="start")


def _user_block(user) -> str:
    name = user.first_name or user.username or "—"
    return (
        f"👤 {t('user.name')}: <b>{name}</b>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"💰 {t('user.balance')}: <b>{user.balance} TJS</b>\n\n"
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
            t("sub.text"), reply_markup=get_subscribe_keyboard()
        )
        return

    await message.answer(
        t("start.hello") + _user_block(user) + t("start.footer"),
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin),
    )


@router.callback_query(F.data == SUBSCRIBE_CALLBACK)
async def on_subscribe_check(
    call: CallbackQuery,
    db_user=None,  # injected by UserMiddleware
    session=None,  # injected by DatabaseMiddleware
) -> None:
    bot = call.bot
    if bot is not None and not await is_subscribed(bot, call.from_user.id):
        await safe_answer(call, t("sub.not_joined"), show_alert=True)
        return

    user = db_user
    if user is None and session is not None:
        user, _ = await UserService(session).register_user(
            telegram_id=call.from_user.id,
            username=call.from_user.username,
            first_name=call.from_user.first_name,
            is_admin=False,
        )

    await safe_answer(call, t("sub.ok"))
    text = t("start.hello") + (_user_block(user) if user else "") + t(
        "start.footer"
    )
    markup = get_main_menu_keyboard(
        is_admin=user.is_admin if user else False
    )
    edited = await safe_edit_text(call.message, text, reply_markup=markup)
    if not edited and call.message is not None:
        await call.message.answer(text, reply_markup=markup)


@router.callback_query(F.data == LANGUAGE_CALLBACK)
async def on_language_menu(
    call: CallbackQuery,
    state,
    db_user=None,
) -> None:
    await state.clear()
    await safe_edit_text(
        call.message, t("lang.choose"), reply_markup=get_language_keyboard()
    )
    await safe_answer(call)


@router.callback_query(F.data.startswith("lang:set:"))
async def on_language_set(
    call: CallbackQuery,
    state,
    db_user=None,
    session=None,
) -> None:
    code = (call.data or "").removeprefix("lang:set:")
    if code not in LANGS:
        await safe_answer(call, "Нодуруст. / Nodurust.", show_alert=True)
        return

    set_lang(code)
    if db_user is not None and session is not None:
        await UserRepository(session).set_lang(db_user.id, code)

    is_admin = db_user.is_admin if db_user else False
    await safe_answer(call, t("lang.changed"))
    await safe_edit_text(
        call.message,
        t("start.hello") + (_user_block(db_user) if db_user else "") + t(
            "start.footer"
        ),
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )


@router.message(Command("menu"))
@router.message(F.text.in_(labels_for("btn.menu")))
async def cmd_menu(message: Message, db_user=None) -> None:
    is_admin = db_user.is_admin if db_user else False
    text = f"{t('menu.title')}\n\n"
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
