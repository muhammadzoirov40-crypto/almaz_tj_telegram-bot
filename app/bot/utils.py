from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def safe_answer(
    call: CallbackQuery,
    text: str | None = None,
    show_alert: bool = False,
) -> bool:
    """Answer callback query; ignore expired/invalid query errors."""
    try:
        await call.answer(text, show_alert=show_alert)
        return True
    except TelegramBadRequest as exc:
        message = str(exc)
        if "query is too old" in message or "query ID is invalid" in message:
            logger.debug("Expired callback query ignored: %s", message)
            return False
        raise
    except Exception:
        logger.exception("callback answer failed")
        return False


async def safe_edit_text(
    message: Message | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    **kwargs,
) -> bool:
    if message is None:
        return False
    try:
        await message.edit_text(text, reply_markup=reply_markup, **kwargs)
        return True
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return False
        raise
