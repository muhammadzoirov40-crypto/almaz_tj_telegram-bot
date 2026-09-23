from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.providers.base import (
    PaymentProvider,
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MockPaymentProvider(PaymentProvider):
    """Development-only payment provider.

    Simulates a payment gateway. NEVER use in production.
    """

    name = "mock"

    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        provider_payment_id = f"mockpay_{uuid4().hex[:16]}"
        payment_url = f"https://example.invalid/pay/{provider_payment_id}"
        logger.info(
            "Mock payment created order_id=%s provider_payment_id=%s",
            request.order_id,
            provider_payment_id,
        )
        return PaymentResponse(
            payment_url=payment_url,
            provider_payment_id=provider_payment_id,
            raw={"order_id": request.order_id, "amount": str(request.amount)},
        )

    async def verify_payment(self, payload: dict[str, Any]) -> PaymentVerification:
        transaction_id = str(payload.get("transaction_id") or payload.get("id") or "")
        if not transaction_id:
            return PaymentVerification(success=False, transaction_id="")

        amount_raw = payload.get("amount")
        amount: Decimal | None = None
        if amount_raw is not None:
            try:
                amount = Decimal(str(amount_raw))
            except Exception:
                amount = None

        status = str(payload.get("status", "success")).lower()
        success = status in {"success", "paid", "completed", "ok"}

        return PaymentVerification(
            success=success,
            transaction_id=transaction_id,
            amount=amount,
            currency=payload.get("currency"),
            raw=payload,
        )
