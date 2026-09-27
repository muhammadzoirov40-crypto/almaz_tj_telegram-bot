from __future__ import annotations

from typing import Optional, Union

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, InputFile, Message

from app.config import settings
from app.i18n import t
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Sends Telegram notifications about order status changes."""

    def __init__(self, bot: Optional[Bot] = None) -> None:
        self._bot = bot

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            raise RuntimeError("NotificationService bot is not configured")
        return self._bot

    def set_bot(self, bot: Bot) -> None:
        self._bot = bot

    async def send_order_update(
        self,
        telegram_id: int,
        order_id: int,
        status: str,
        detail: str = "",
    ) -> None:
        text = self._format_order_message(order_id, status, detail)
        await self.safe_send(telegram_id, text)

    async def notify_admins_new_order(
        self,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        photo: Optional[Union[str, InputFile]] = None,
    ) -> None:
        for admin_id in settings.admin_ids:
            if photo is not None:
                await self.safe_send_photo(
                    admin_id, photo, caption=text, reply_markup=reply_markup
                )
            else:
                await self.safe_send(admin_id, text, reply_markup=reply_markup)

    async def safe_send(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        try:
            await self.bot.send_message(
                chat_id, text, reply_markup=reply_markup
            )
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning("Cannot notify chat_id=%s: %s", chat_id, exc)
            return False
        except Exception:
            logger.exception("Notification failed chat_id=%s", chat_id)
            return False

    async def safe_send_photo(
        self,
        chat_id: int,
        photo: Union[str, InputFile],
        caption: str = "",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        try:
            await self.bot.send_photo(
                chat_id,
                photo,
                caption=caption,
                reply_markup=reply_markup,
            )
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning("Cannot send photo to chat_id=%s: %s", chat_id, exc)
            return False
        except Exception:
            logger.exception("Photo send failed chat_id=%s", chat_id)
            return False

    @staticmethod
    def _format_order_message(order_id: int, status: str, detail: str) -> str:
        icons = {
            "PENDING": "⏳",
            "PAID": "💳",
            "PROCESSING": "⚙️",
            "COMPLETED": "✅",
            "FAILED": "❌",
            "CANCELLED": "🚫",
        }
        status_keys = {
            "PENDING": "status.pending",
            "PAID": "status.paid",
            "PROCESSING": "status.processing",
            "COMPLETED": "status.completed",
            "FAILED": "status.failed",
            "CANCELLED": "status.cancelled",
        }
        icon = icons.get(status, "ℹ️")
        key = status_keys.get(status)
        label = t(key) if key else status
        lines = [
            t("notif.order_line", icon=icon, id=order_id),
            t("notif.status_line", status=label),
        ]
        if detail:
            lines.append(detail)
        return "\n".join(lines)


notification_service = NotificationService()
