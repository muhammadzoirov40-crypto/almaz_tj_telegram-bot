from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import TransactionType
from app.database.models import Product, User
from app.database.repositories import TransactionRepository, UserRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.transactions = TransactionRepository(session)

    async def register_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> tuple[User, bool]:
        user, created = await self.users.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            is_admin=is_admin,
        )
        if created:
            logger.info("New user registered telegram_id=%s", telegram_id)
        return user, created

    async def get_profile(self, telegram_id: int) -> Optional[User]:
        return await self.users.get_by_telegram_id(telegram_id)

    async def add_balance(
        self,
        user_id: int,
        amount: Decimal,
        description: str = "",
        reference_id: Optional[str] = None,
    ) -> User:
        if amount <= 0:
            raise ValueError("Маблағ бояд мусбӣ бошад.")
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise ValueError("Корбар ёфт нашуд.")
        new_balance = user.balance + amount
        user = await self.users.update_balance(user_id, new_balance)
        await self.transactions.create(
            user_id=user_id,
            type_=TransactionType.TOPUP,
            amount=amount,
            description=description or "Balance top-up",
            reference_id=reference_id,
        )
        logger.info("Balance credited user_id=%s amount=%s", user_id, amount)
        return user

    async def remove_balance(
        self,
        user_id: int,
        amount: Decimal,
        description: str = "",
        reference_id: Optional[str] = None,
    ) -> User:
        if amount <= 0:
            raise ValueError("Маблағ бояд мусбӣ бошад.")
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise ValueError("Корбар ёфт нашуд.")
        if user.balance < amount:
            raise ValueError(
                "Баланс кофӣ нест: "
                f"{user.balance} TJS < {amount} TJS"
            )
        user = await self.users.update_balance(
            user_id, user.balance - amount
        )
        await self.transactions.create(
            user_id=user_id,
            type_=TransactionType.REFUND,
            amount=amount,
            description=description or "Balance refund",
            reference_id=reference_id,
        )
        logger.info("Balance debited user_id=%s amount=%s", user_id, amount)
        return user
