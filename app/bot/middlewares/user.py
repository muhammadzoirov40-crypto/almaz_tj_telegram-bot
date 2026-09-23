from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser

from app.config import settings
from app.database.repositories import UserRepository


class UserMiddleware(BaseMiddleware):
    """Ensures current user exists in DB and injects `db_user`.
    Blocked users (is_active=False) are ignored for non-admin events.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        session = data.get("session")

        if tg_user is not None and session is not None:
            repo = UserRepository(session)
            user, _ = await repo.get_or_create(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                is_admin=settings.is_admin_id(tg_user.id),
            )
            if settings.is_admin_id(tg_user.id) and not user.is_admin:
                user.is_admin = True
                await session.flush()
            data["db_user"] = user

            if not user.is_active and not user.is_admin:
                return None

        return await handler(event, data)
