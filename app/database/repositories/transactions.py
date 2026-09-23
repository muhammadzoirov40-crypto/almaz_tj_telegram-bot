from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        type_: str,
        amount: Decimal,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Transaction:
        transaction = Transaction(
            user_id=user_id,
            type=type_,
            amount=amount,
            description=description,
            reference_id=reference_id,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def get_by_reference_id(
        self, reference_id: str
    ) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.reference_id == reference_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: int, limit: int = 50
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
