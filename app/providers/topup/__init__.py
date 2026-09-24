from __future__ import annotations

from app.config import settings
from app.providers.base import TopUpProvider
from app.providers.topup.provider import MockTopUpProvider, RealTopUpProvider

__all__ = [
    "MockTopUpProvider",
    "RealTopUpProvider",
    "get_topup_provider",
]


def get_topup_provider() -> TopUpProvider:
    provider = settings.topup_provider.lower()
    if provider == "real":
        api_url = settings.effective_topup_api_url
        api_key = settings.effective_topup_api_key
        if not api_url and not settings.fireloot_api_key:
            raise RuntimeError(
                "TOPUP_PROVIDER=real requires FREE_FIRE_API_URL (or TOPUP_API_URL) "
                "or FIRELOOT_API_KEY"
            )
        # Lookup works without API key on some free endpoints; top-up still needs key.
        return RealTopUpProvider(api_url or None, api_key or None)
    return MockTopUpProvider()
