from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery, ChatMember, Message, TelegramObject

from app.bot.utils import safe_answer, safe_edit_text
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

CHECK_CALLBACK_DATA = "sub:check"

NOT_SUBSCRIBED_ALERT = "⚠️ Аввал ба канал обуна шавед!"

SUBSCRIPTION_TEXT = (
    "📢 <b>Обуна ҳатмӣ аст</b>\n\n"
    "Барои истифодаи бот аввал ба канал обуна шавед, "
    "пас тугмачаи «Ҳисоб кардан»-ро пахш кунед.\n\n"
    f"Канал: <a href=\"{settings.force_subscribe_url}\">"
    f"{settings.force_subscribe_channel}</a>"
)

# Positive membership cache: (user_id, channel) -> expires_at
_positive_cache: Dict[tuple[int, str], float] = {}
_CACHE_TTL_SECONDS = 300.0


def is_subscribed_status(member: ChatMember) -> bool:
    """True when chat member status means the user sees the channel."""
    status = getattr(member, "status", None)
    if status in ("creator", "administrator", "member"):
        return True
    return bool(getattr(member, "is_member", False))


def _cache_key(user_id: int, channel: str) -> tuple[int, str]:
    return (user_id, channel)


def _get_cached_positive(user_id: int, channel: str) -> bool:
    key = _cache_key(user_id, channel)
    expires_at = _positive_cache.get(key)
    if expires_at is None:
        return False
    if expires_at <= time.monotonic():
        _positive_cache.pop(key, None)
        return False
    return True


def _set_cached_positive(user_id: int, channel: str) -> None:
    _positive_cache[_cache_key(user_id, channel)] = (
        time.monotonic() + _CACHE_TTL_SECONDS
    )


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Check `user_id` membership in the configured force-subscribe channel."""
    channel = settings.force_subscribe_channel.strip()
    if not channel:
        return True
    if _get_cached_positive(user_id, channel):
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning(
            "Subscription check failed user_id=%s channel=%s: %s",
            user_id,
            channel,
            exc,
        )
        # Unknown bot rights / bad channel → do not lock everyone out
        return True
    if is_subscribed_status(member):
        _set_cached_positive(user_id, channel)
        return True
    return False


def get_subscription_keyboard():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows: list[list[InlineKeyboardButton]] = []
    url = settings.force_subscribe_url
    if url:
        rows.append(
            [InlineKeyboardButton(text="📢 Обуна шудан", url=url)]
        )
    rows.append(
        [InlineKeyboardButton(text="✅ Ҳисоб кардан", callback_data=CHECK_CALLBACK_DATA)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _deny(event: TelegramObject) -> None:
    if isinstance(event, CallbackQuery):
        await safe_answer(event, NOT_SUBSCRIBED_ALERT, show_alert=True)
        message = event.message
        if message is not None:
            await safe_edit_text(message, SUBSCRIPTION_TEXT, reply_markup=get_subscription_keyboard())
        return
    if isinstance(event, Message):
        await event.answer(SUBSCRIPTION_TEXT, reply_markup=get_subscription_keyboard())


class SubscriptionMiddleware(BaseMiddleware):
    """Blocks every update until the user subscribed to the required channel.

    Admins (ADMIN_IDS) bypass the check. Callback `sub:check` is forwarded
    to handlers when the user is already subscribed.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not settings.force_subscribe_enabled:
            return await handler(event, data)

        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)
        if settings.is_admin_id(tg_user.id):
            return await handler(event, data)

        bot: Bot | None = data.get("bot")
        if bot is None:
            return await handler(event, data)

        is_subscribed = await check_subscription(bot, tg_user.id)

        callback = event if isinstance(event, CallbackQuery) else None
        if callback is not None and callback.data == CHECK_CALLBACK_DATA:
            if is_subscribed:
                return await handler(event, data)
            await safe_answer(callback, NOT_SUBSCRIBED_ALERT, show_alert=True)
            return None

        if is_subscribed:
            return await handler(event, data)

        await _deny(event)
        return None
