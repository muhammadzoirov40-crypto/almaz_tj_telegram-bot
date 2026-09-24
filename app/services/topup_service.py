from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import OrderStatus
from app.database.models import Order
from app.database.repositories import OrderRepository
from app.providers import TopUpProvider, get_topup_provider
from app.services.order_service import OrderService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TopUpError(Exception):
    pass


class TopUpService:
    """Orchestrates the actual top-up after payment is confirmed.

    Works only against the TopUpProvider abstraction so the real
    authorized provider can be swapped in without touching this code.
    """

    def __init__(
        self,
        session: AsyncSession,
        provider: Optional[TopUpProvider] = None,
    ) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.order_service = OrderService(session)
        self.provider = provider or get_topup_provider()

    async def process_order(self, order_id: int) -> Order:
        order = await self.orders.get_by_id(order_id)
        if order is None:
            raise TopUpError(f"Order {order_id} not found")

        if order.status == OrderStatus.COMPLETED:
            logger.info("Order %s already completed, skipping", order_id)
            return order

        if order.status != OrderStatus.PAID:
            raise TopUpError(
                f"Order {order_id} is {order.status}, expected PAID"
            )

        # Move to PROCESSING (idempotent guard inside transition)
        order = await self.order_service.mark_processing(order_id)
        if order is None:
            raise TopUpError(f"Order {order_id} not found")

        product_name = order.product.name if order.product else str(order.product_id)
        sku = order.product.sku if order.product else None

        try:
            result = await self.provider.topup(
                uid=order.free_fire_uid,
                product=product_name,
                order_id=order.id,
                sku=sku,
            )
        except Exception as exc:
            logger.exception("Top-up request failed order_id=%s", order_id)
            order = await self.order_service.mark_failed(
                order_id, reason=str(exc)
            )
            assert order is not None
            return order

        if result.success and result.pending:
            # Delivered asynchronously (FireLoot): stay in PROCESSING and let
            # the poller watch GET /order/:id until completed/failed/refunded.
            if order.provider_order_id is None:
                await self.orders.set_provider_order_id(
                    order.id, result.provider_reference
                )
            logger.info(
                "Top-up submitted order_id=%s sku=%s ref=%s",
                order_id,
                sku,
                result.provider_reference,
            )
            return order

        if result.success:
            order = await self.order_service.mark_completed(order_id)
            if order is not None and order.provider_order_id is None:
                await self.orders.set_provider_order_id(
                    order.id, result.provider_reference
                )
            logger.info(
                "Top-up completed order_id=%s ref=%s",
                order_id,
                result.provider_reference,
            )
        else:
            order = await self.order_service.mark_failed(
                order_id, reason=result.message or "provider_failed"
            )
            logger.warning(
                "Top-up failed order_id=%s message=%s",
                order_id,
                result.message,
            )

        assert order is not None
        return order
