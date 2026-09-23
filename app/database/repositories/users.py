from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            is_admin=is_admin,
            balance=Decimal("0.00"),
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            changed = False
            if username is not None and user.username != username:
                user.username = username
                changed = True
            if first_name is not None and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if changed:
                await self.session.flush()
            return user, False

        try:
            user = await self.create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                is_admin=is_admin,
            )
            return user, True
        except IntegrityError:
            await self.session.rollback()
            user = await self.get_by_telegram_id(telegram_id)
            if user is None:
                raise
            changed = False
            if username is not None and user.username != username:
                user.username = username
                changed = True
            if first_name is not None and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if changed:
                await self.session.flush()
            return user, False

    async def update_balance(self, user_id: int, new_balance: Decimal) -> User:
        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} found")
        user.balance = new_balance
        await self.session.flush()
        return user

    async def set_active(self, user_id: int, is_active: bool) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        user.is_active = is_active
        await self.session.flush()
        return user

    async def list_users(self, limit: int = 50, offset: int = 0) -> list[User]:
        stmt = (
            select(User).order_by(User.id.desc()).limit(limit).offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_users(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
