from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import PaymentStatus
from app.database.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        order_id: int,
        amount: Decimal,
        currency: str,
        provider: str,
        transaction_id: Optional[str] = None,
        status: str = PaymentStatus.PENDING,
    ) -> Payment:
        payment = Payment(
            order_id=order_id,
            amount=amount,
            currency=currency,
            provider=provider,
            transaction_id=transaction_id,
            status=status,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_transaction_id(
        self, transaction_id: str
    ) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.transaction_id == transaction_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_order_id(self, order_id: int) -> Optional[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_order_ids(self, order_ids: list[int]) -> list[Payment]:
        if not order_ids:
            return []
        stmt = (
            select(Payment)
            .options(selectinload(Payment.order))
            .where(Payment.order_id.in_(order_ids))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_paid(
        self,
        payment_id: int,
        transaction_id: Optional[str] = None,
    ) -> Optional[Payment]:
        payment = await self.get_by_id(payment_id)
        if payment is None:
            return None
        payment.status = PaymentStatus.PAID
        payment.paid_at = datetime.now(timezone.utc)
        if transaction_id:
            payment.transaction_id = transaction_id
        await self.session.flush()
        return payment

    async def mark_failed(self, payment_id: int) -> Optional[Payment]:
        payment = await self.get_by_id(payment_id)
        if payment is None:
            return None
        payment.status = PaymentStatus.FAILED
        await self.session.flush()
        return payment
