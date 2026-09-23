from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import SupportTicket, User


class SupportTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        subject: str,
        message: str,
        status: str = "OPEN",
    ) -> SupportTicket:
        ticket = SupportTicket(
            user_id=user_id,
            subject=subject,
            message=message,
            status=status,
        )
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        stmt = (
            select(SupportTicket)
            .options(selectinload(SupportTicket.user))
            .where(SupportTicket.id == ticket_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_open(self, limit: int = 50) -> list[SupportTicket]:
        stmt = (
            select(SupportTicket)
            .options(selectinload(SupportTicket.user))
            .where(SupportTicket.status == "OPEN")
            .order_by(SupportTicket.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, limit: int = 50) -> list[SupportTicket]:
        stmt = (
            select(SupportTicket)
            .options(selectinload(SupportTicket.user))
            .order_by(SupportTicket.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_open(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(SupportTicket.id)).where(
            SupportTicket.status == "OPEN"
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
