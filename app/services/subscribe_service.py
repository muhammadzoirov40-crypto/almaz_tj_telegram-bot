from __future__ import annotations

from typing import Any

from aiogram import Bot

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

SUBSCRIBED_STATUSES = {"creator", "administrator", "member"}

# Sentinel: chat_ref not given → read it from settings.
USE_DEFAULT = object()


def default_chat_ref() -> str | int | None:
    if settings.required_channel_id:
        return settings.required_channel_id
    username = (settings.required_channel_username or "").strip()
    if not username:
        return None
    return username if username.startswith("@") else f"@{username}"


async def is_subscribed(
    bot: Bot,
    user_id: int,
    chat_ref: str | int | None | object = USE_DEFAULT,
) -> bool:
    """True when the user is a member of the required channel.

    `chat_ref=None` disables the check; omit it to use settings.
    Fails open: unknown channel / API errors do not block the user.
    """
    ref = default_chat_ref() if chat_ref is USE_DEFAULT else chat_ref
    if ref is None:
        return True

    try:
        member: Any = await bot.get_chat_member(ref, user_id)
    except Exception:
        logger.warning(
            "Subscription check failed chat_ref=%s user_id=%s", ref, user_id
        )
        return True

    status = getattr(member, "status", "")
    if status == "restricted":
        return bool(getattr(member, "is_member", False))
    return status in SUBSCRIBED_STATUSES
