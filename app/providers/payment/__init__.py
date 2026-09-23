from __future__ import annotations

from app.config import settings
from app.providers.base import PaymentProvider
from app.providers.payment.provider import MockPaymentProvider


class RealPaymentProvider(PaymentProvider):
    """Placeholder for a real, authorized payment provider.

    Implement create_payment / verify_payment against your contracted
    payment gateway. Credentials come from .env only.
    """

    name = "real"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    async def create_payment(self, request):  # type: ignore[no-untyped-def]
        raise NotImplementedError(
            "Real payment provider is not configured yet. "
            "Set PAYMENT_PROVIDER=mock for development."
        )

    async def verify_payment(self, payload):  # type: ignore[no-untyped-def]
        raise NotImplementedError(
            "Real payment provider is not configured yet."
        )


def get_payment_provider() -> PaymentProvider:
    provider = settings.payment_provider.lower()
    if provider == "real":
        if not settings.payment_api_url or not settings.payment_api_key:
            raise RuntimeError(
                "PAYMENT_PROVIDER=real requires PAYMENT_API_URL and PAYMENT_API_KEY"
            )
        return RealPaymentProvider(settings.payment_api_url, settings.payment_api_key)
    return MockPaymentProvider()
