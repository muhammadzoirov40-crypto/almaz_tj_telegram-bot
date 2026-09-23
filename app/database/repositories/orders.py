from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import OrderStatus
from app.database.models import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        product_id: int,
        free_fire_uid: str,
        amount: Decimal,
        currency: str,
        status: str = OrderStatus.PENDING,
    ) -> Order:
        order = Order(
            user_id=user_id,
            product_id=product_id,
            free_fire_uid=free_fire_uid,
            amount=amount,
            currency=currency,
            status=status,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.product),
                selectinload(Order.user),
                selectinload(Order.payments),
            )
            .where(Order.id == order_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_provider_order_id(
        self, provider_order_id: str
    ) -> Optional[Order]:
        stmt = select(Order).where(Order.provider_order_id == provider_order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> list[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.product))
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(
        self, status: str, limit: int = 50
    ) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.status == status)
            .order_by(Order.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self, query: str, limit: int = 20
    ) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.free_fire_uid.contains(query))
            .order_by(Order.id.desc())
            .limit(limit)
        )
        if query.isdigit():
            stmt = select(Order).where(
                (Order.free_fire_uid.contains(query))
                | (Order.id == int(query))
            ).order_by(Order.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        order_id: int,
        status: str,
        failure_reason: Optional[str] = None,
    ) -> Optional[Order]:
        order = await self.get_by_id(order_id)
        if order is None:
            return None
        order.status = status
        if failure_reason is not None:
            order.failure_reason = failure_reason
        if status == OrderStatus.COMPLETED:
            order.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return order

    async def set_provider_order_id(
        self, order_id: int, provider_order_id: str
    ) -> Optional[Order]:
        order = await self.get_by_id(order_id)
        if order is None:
            return None
        order.provider_order_id = provider_order_id
        await self.session.flush()
        return order

    async def count_all(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(Order.id))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
