from __future__ import annotations

from typing import Any, Callable, Awaitable

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import settings


class AdminFilter(BaseFilter):
    """Allow only configured admin Telegram IDs."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and settings.is_admin_id(user.id)
