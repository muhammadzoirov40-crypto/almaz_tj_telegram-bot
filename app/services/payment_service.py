from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import OrderStatus, PaymentStatus
from app.database.models import Order, Payment
from app.database.repositories import OrderRepository, PaymentRepository
from app.providers import PaymentProvider, PaymentRequest, get_payment_provider
from app.services.order_service import OrderService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PaymentError(Exception):
    pass


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        provider: Optional[PaymentProvider] = None,
    ) -> None:
        self.session = session
        self.payments = PaymentRepository(session)
        self.orders = OrderRepository(session)
        self.order_service = OrderService(session)
        self.provider = provider or get_payment_provider()

    async def create_payment_for_order(self, order: Order) -> Payment:
        """Create a PENDING payment record + provider payment link."""
        if order.status not in {OrderStatus.PENDING, OrderStatus.PAID}:
            raise PaymentError(f"Order {order.id} cannot be paid in {order.status}")

        # Idempotent: reuse existing pending payment for this order
        existing = await self.payments.get_latest_by_order_id(order.id)
        if existing is not None and existing.status == PaymentStatus.PAID:
            raise PaymentError("Order is already paid")
        if existing is not None and existing.status == PaymentStatus.PENDING:
            return existing

        payment = await self.payments.create(
            order_id=order.id,
            amount=order.amount,
            currency=order.currency,
            provider=self.provider.name,
            status=PaymentStatus.PENDING,
        )

        request = PaymentRequest(
            order_id=order.id,
            amount=order.amount,
            currency=order.currency,
            description=f"ALMAZ TJ order #{order.id}",
        )
        try:
            response = await self.provider.create_payment(request)
        except Exception as exc:
            await self.payments.mark_failed(payment.id)
            logger.exception("Payment creation failed order_id=%s", order.id)
            raise PaymentError(str(exc)) from exc

        payment.transaction_id = response.provider_payment_id
        await self.session.flush()
        logger.info(
            "Payment created payment_id=%s order_id=%s provider=%s",
            payment.id,
            order.id,
            self.provider.name,
        )
        # Attach URL for the handler (not persisted on Payment model by design)
        payment_meta = {"payment_url": response.payment_url}
        setattr(payment, "_payment_url", payment_meta["payment_url"])
        return payment

    async def handle_webhook(
        self, payload: dict[str, Any]
    ) -> tuple[bool, str]:
        """Process payment webhook idempotently.

        Returns (processed: bool, message: str).
        """
        verification = await self.provider.verify_payment(payload)
        if not verification.success or not verification.transaction_id:
            logger.warning("Webhook verification failed payload_keys=%s", list(payload))
            return False, "verification_failed"

        # Duplicate protection by transaction_id
        existing_payment = await self.payments.get_by_transaction_id(
            verification.transaction_id
        )
        if existing_payment is not None and existing_payment.status == PaymentStatus.PAID:
            logger.info(
                "Duplicate webhook ignored transaction_id=%s",
                verification.transaction_id,
            )
            return True, "duplicate_ignored"

        order_id = payload.get("order_id")
        payment: Optional[Payment] = None

        if existing_payment is not None:
            payment = existing_payment
            order_id = payment.order_id
        elif order_id is not None:
            payment = await self.payments.get_latest_by_order_id(int(order_id))

        if payment is None:
            logger.warning(
                "Webhook for unknown payment transaction_id=%s",
                verification.transaction_id,
            )
            return False, "payment_not_found"

        if payment.status == PaymentStatus.PAID:
            return True, "duplicate_ignored"

        # Amount check when provider reports amount
        if verification.amount is not None and verification.amount != payment.amount:
            logger.error(
                "Amount mismatch payment_id=%s expected=%s got=%s",
                payment.id,
                payment.amount,
                verification.amount,
            )
            await self.payments.mark_failed(payment.id)
            return False, "amount_mismatch"

        await self.payments.mark_paid(
            payment.id, transaction_id=verification.transaction_id
        )
        order = await self.order_service.mark_paid(payment.order_id)
        if order is None:
            return False, "order_not_found"

        logger.info(
            "Payment confirmed payment_id=%s order_id=%s",
            payment.id,
            payment.order_id,
        )
        return True, "ok"
