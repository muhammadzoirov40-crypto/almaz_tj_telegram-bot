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


def _is_media_message(message: Message) -> bool:
    return bool(
        message.photo
        or message.video
        or message.document
        or message.animation
        or message.audio
        or message.voice
        or message.sticker
    )


async def safe_edit_text(
    message: Message | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    **kwargs,
) -> bool:
    """Edit a text message, or caption if the message is media (photo receipt)."""
    if message is None:
        return False

    if _is_media_message(message):
        try:
            await message.edit_caption(
                caption=text, reply_markup=reply_markup, **kwargs
            )
            return True
        except TelegramBadRequest as exc:
            err = str(exc)
            if "message is not modified" in err:
                return False
            if "message to edit not found" in err:
                return False
            # Caption missing / cannot edit → fall through to text edit
            logger.debug("edit_caption failed, trying edit_text: %s", err)

    try:
        await message.edit_text(text, reply_markup=reply_markup, **kwargs)
        return True
    except TelegramBadRequest as exc:
        err = str(exc)
        if "message is not modified" in err:
            return False
        # Media message cannot become text → send new message instead
        if _is_media_message(message) and "message to edit not found" not in err:
            try:
                await message.answer(text, reply_markup=reply_markup)
                # Remove old buttons so only the new result shows
                try:
                    await message.edit_reply_markup(reply_markup=None)
                except TelegramBadRequest:
                    pass
                return True
            except TelegramBadRequest:
                logger.warning("Fallback answer after edit failed: %s", err)
                return False
        if "message to edit not found" in err:
            return False
        raise
