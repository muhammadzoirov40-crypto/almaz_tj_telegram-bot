from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.balance_topup import BalanceTopUpStatus
from app.database.models import BalanceTopUpRequest


class BalanceTopUpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        amount: Decimal,
        method: str,
        phone: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> BalanceTopUpRequest:
        if reference_id is None:
            reference_id = f"bal:{user_id}:{uuid4().hex[:16]}"
        request = BalanceTopUpRequest(
            user_id=user_id,
            amount=amount,
            method=method,
            phone=phone,
            reference_id=reference_id,
            status=BalanceTopUpStatus.PENDING,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_by_id(self, request_id: int) -> Optional[BalanceTopUpRequest]:
        stmt = (
            select(BalanceTopUpRequest)
            .options(
                selectinload(BalanceTopUpRequest.user),
            )
            .where(BalanceTopUpRequest.id == request_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reference_id(
        self, reference_id: str
    ) -> Optional[BalanceTopUpRequest]:
        stmt = select(BalanceTopUpRequest).where(
            BalanceTopUpRequest.reference_id == reference_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_receipt(
        self,
        request_id: int,
        photo_file_id: Optional[str] = None,
        receipt_text: Optional[str] = None,
    ) -> Optional[BalanceTopUpRequest]:
        request = await self.get_by_id(request_id)
        if request is None:
            return None
        request.receipt_photo_file_id = photo_file_id
        request.receipt_text = receipt_text
        await self.session.flush()
        return request

    async def mark_approved(
        self, request_id: int
    ) -> Optional[BalanceTopUpRequest]:
        request = await self.get_by_id(request_id)
        if request is None:
            return None
        request.status = BalanceTopUpStatus.APPROVED
        request.processed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return request

    async def mark_rejected(
        self, request_id: int, reason: str = ""
    ) -> Optional[BalanceTopUpRequest]:
        request = await self.get_by_id(request_id)
        if request is None:
            return None
        request.status = BalanceTopUpStatus.REJECTED
        request.failure_reason = reason or None
        request.processed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return request

    async def mark_cancelled(
        self, request_id: int
    ) -> Optional[BalanceTopUpRequest]:
        request = await self.get_by_id(request_id)
        if request is None:
            return None
        request.status = BalanceTopUpStatus.CANCELLED
        request.processed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return request

    async def mark_refunded(
        self, request_id: int, reason: str = ""
    ) -> Optional[BalanceTopUpRequest]:
        request = await self.get_by_id(request_id)
        if request is None:
            return None
        request.status = BalanceTopUpStatus.REFUNDED
        if reason:
            request.failure_reason = reason
        request.processed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return request

    async def list_pending(self, limit: int = 10) -> list[BalanceTopUpRequest]:
        stmt = (
            select(BalanceTopUpRequest)
            .options(selectinload(BalanceTopUpRequest.user))
            .where(BalanceTopUpRequest.status == BalanceTopUpStatus.PENDING)
            .order_by(BalanceTopUpRequest.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_pending(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(BalanceTopUpRequest.id)).where(
            BalanceTopUpRequest.status == BalanceTopUpStatus.PENDING
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
