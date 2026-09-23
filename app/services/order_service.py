from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import OrderStatus, TransactionType
from app.database.models import Order, Product, User
from app.database.repositories import (
    OrderRepository,
    ProductRepository,
    TransactionRepository,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OrderError(Exception):
    pass


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.products = ProductRepository(session)
        self.transactions = TransactionRepository(session)

    async def get_active_products(self) -> list[Product]:
        return await self.products.get_active_products()

    async def get_product(self, product_id: int) -> Optional[Product]:
        return await self.products.get_by_id(product_id)

    async def create_order(
        self,
        user: User,
        product: Product,
        free_fire_uid: str,
        deduct_balance: bool = True,
    ) -> Order:
        if not product.is_active:
            raise OrderError("Ин маҳсулот ғайрифаъол аст.")
        if deduct_balance and user.balance < product.price:
            raise OrderError("Баланс кофӣ нест. Лутфан аввал балансро пур кунед.")

        if deduct_balance:
            # Deduct balance atomically within the same transaction
            new_balance = user.balance - product.price
            user.balance = new_balance

        order = await self.orders.create(
            user_id=user.id,
            product_id=product.id,
            free_fire_uid=free_fire_uid,
            amount=product.price,
            currency=product.currency,
            status=OrderStatus.PENDING,
        )
        if deduct_balance:
            await self.transactions.create(
                user_id=user.id,
                type_=TransactionType.ORDER_PAYMENT,
                amount=-product.price,
                description=f"Order #{order.id} · {product.name}",
                reference_id=f"order:{order.id}",
            )
        await self.session.flush()
        logger.info(
            "Order created order_id=%s user_id=%s product_id=%s uid=%s deduct_balance=%s",
            order.id,
            user.id,
            product.id,
            free_fire_uid,
            deduct_balance,
        )
        return order

    async def was_balance_deducted(self, order_id: int) -> bool:
        tx = await self.transactions.get_by_reference_id(f"order:{order_id}")
        return tx is not None

    async def get_order(self, order_id: int) -> Optional[Order]:
        return await self.orders.get_by_id(order_id)

    async def list_user_orders(
        self, user_id: int, limit: int = 10, offset: int = 0
    ) -> list[Order]:
        return await self.orders.list_by_user(user_id, limit=limit, offset=offset)

    async def can_transition(self, order: Order, new_status: str) -> bool:
        """Guard against invalid/double transitions (webhook idempotency)."""
        allowed: dict[str, set[str]] = {
            OrderStatus.PENDING: {
                OrderStatus.PAID,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            },
            OrderStatus.PAID: {
                OrderStatus.PROCESSING,
                OrderStatus.FAILED,
                OrderStatus.CANCELLED,
            },
            OrderStatus.PROCESSING: {
                OrderStatus.COMPLETED,
                OrderStatus.FAILED,
            },
            OrderStatus.COMPLETED: set(),
            OrderStatus.FAILED: set(),
            OrderStatus.CANCELLED: set(),
        }
        return new_status in allowed.get(order.status, set())

    async def transition(
        self,
        order_id: int,
        new_status: str,
        failure_reason: Optional[str] = None,
    ) -> Optional[Order]:
        order = await self.orders.get_by_id(order_id)
        if order is None:
            return None
        if not await self.can_transition(order, new_status):
            logger.warning(
                "Invalid order transition order_id=%s from=%s to=%s ignored",
                order_id,
                order.status,
                new_status,
            )
            return order  # idempotent: no change
        order = await self.orders.update_status(
            order_id, new_status, failure_reason=failure_reason
        )
        logger.info(
            "Order transition order_id=%s status=%s", order_id, new_status
        )
        return order

    async def mark_paid(self, order_id: int) -> Optional[Order]:
        return await self.transition(order_id, OrderStatus.PAID)

    async def mark_processing(self, order_id: int) -> Optional[Order]:
        return await self.transition(order_id, OrderStatus.PROCESSING)

    async def mark_completed(self, order_id: int) -> Optional[Order]:
        return await self.transition(order_id, OrderStatus.COMPLETED)

    async def mark_failed(
        self, order_id: int, reason: str = ""
    ) -> Optional[Order]:
        return await self.transition(
            order_id, OrderStatus.FAILED, failure_reason=reason
        )
