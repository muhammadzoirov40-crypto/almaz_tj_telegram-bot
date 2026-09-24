from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
VALIDATE_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
# Docs: sync the product list every 10-15 minutes, never cache longer than an hour.
PRODUCTS_TTL = 15 * 60

APP_UA = "DanatelTopupBot/1.0 (+https://t.me/danatel_bot)"

# Fallback SKUs if /products is unreachable (base CIS Free Fire / regional).
FALLBACK_SKUS: dict[str, str] = {
    "ff": "diamonds_110",
    "pubg": "pubg_uc_60",
    "bloodstrike": "bs_gold_100",
}

_GAME_SKU_PREFIXES: dict[str, tuple[str, ...]] = {
    "pubg": ("pubg_",),
    "bloodstrike": ("bs_",),
    "mlbb_ru": ("mlbb_",),
    "mlbb_cis": ("mlbb_",),
}


class FireLootError(Exception):
    """FireLoot partner API error (HTTP, network or payload)."""

    def __init__(self, code: str, message: str = "", status: Optional[int] = None):
        super().__init__(message or code)
        self.code = code
        self.message = message
        self.status = status


class FireLootClient:
    """Thin async client for https://partner.firelootshop.com/api/v1"""

    name = "fireloot"

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        base = api_url if api_url is not None else settings.fireloot_api_url
        self.api_url = (base or "").rstrip("/")
        self.api_key = api_key if api_key is not None else settings.fireloot_api_key
        self.timeout = timeout
        self._products: list[dict[str, Any]] = []
        self._products_at: float = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.api_url and self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": APP_UA,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, str]] = None,
        timeout: Optional[httpx.Timeout] = None,
    ) -> Any:
        if not self.configured:
            raise FireLootError("unconfigured", "FIRELOOT_API_KEY is not set")

        url = f"{self.api_url}/{path.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                response = await client.request(
                    method, url, json=json, params=params, headers=self._headers()
                )
        except httpx.HTTPError as exc:
            raise FireLootError("network", type(exc).__name__) from exc

        try:
            data: Any = response.json()
        except ValueError:
            data = None

        if response.status_code >= 400:
            code = ""
            message = ""
            if isinstance(data, dict):
                code = str(data.get("code") or data.get("error") or "")
                message = str(data.get("message") or data.get("error_description") or "")
            raise FireLootError(
                code or f"http_{response.status_code}",
                message or f"HTTP {response.status_code}",
                status=response.status_code,
            )

        if data is None:
            raise FireLootError("invalid_response", "Empty response from FireLoot")
        return data

    async def ping(self) -> dict[str, Any]:
        data = await self._request("GET", "/ping")
        if not isinstance(data, dict) or data.get("ok") is False:
            raise FireLootError("unauthorized", "FireLoot key is not valid")
        return data

    async def balance(self) -> dict[str, Any]:
        data = await self._request("GET", "/balance")
        if not isinstance(data, dict):
            raise FireLootError("invalid_response", "Bad /balance payload")
        return data

    async def products(self, *, force: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if (
            not force
            and self._products
            and (now - self._products_at) < PRODUCTS_TTL
        ):
            return self._products

        data = await self._request("GET", "/products")
        if not isinstance(data, list):
            raise FireLootError("invalid_response", "Bad /products payload")

        products = [item for item in data if isinstance(item, dict) and item.get("sku")]
        if not products:
            raise FireLootError("empty_catalog", "No products returned")

        self._products = products
        self._products_at = now
        logger.info("FireLoot products synced count=%s", len(products))
        return products

    def pick_sku(
        self, products: list[dict[str, Any]], game: str
    ) -> Optional[str]:
        """Pick a zone-less SKU suitable for a game (used for UID validation)."""
        usable = [
            p
            for p in products
            if p.get("sku") and not p.get("requires_zone")
        ]

        if game == "ff":
            diamonds = [
                p
                for p in usable
                if p.get("category") == "diamonds"
                and str(p.get("region", "")).upper() == "CIS"
            ]
            if diamonds:
                diamonds.sort(key=lambda p: _price_key(p.get("price")))
                return str(diamonds[0]["sku"])
            return FALLBACK_SKUS["ff"]

        prefixes = _GAME_SKU_PREFIXES.get(game, ())
        for prefix in prefixes:
            for product in usable:
                if str(product.get("sku", "")).startswith(prefix):
                    return str(product["sku"])
        return FALLBACK_SKUS.get(game)

    def candidate_skus(
        self, products: list[dict[str, Any]], game: str
    ) -> list[str]:
        """SKUs to try for /validate: the picked one, then the static fallback."""
        candidates: list[str] = []
        picked = self.pick_sku(products, game)
        if picked:
            candidates.append(picked)
        fallback = FALLBACK_SKUS.get(game)
        if fallback and fallback not in candidates:
            candidates.append(fallback)
        return candidates

    async def validate(
        self, uid: str, sku: str, zone: Optional[str] = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"sku": sku, "uid": uid}
        if zone:
            payload["zone"] = zone
        data = await self._request(
            "POST", "/validate", json=payload, timeout=VALIDATE_TIMEOUT
        )
        if not isinstance(data, dict):
            raise FireLootError("invalid_response", "Bad /validate payload")
        return data

    async def order(
        self,
        external_id: str,
        sku: str,
        uid: str,
        zone: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "external_id": external_id,
            "sku": sku,
            "uid": uid,
        }
        if zone:
            payload["zone"] = zone
        # Creating an order may take up to 15s on their side.
        data = await self._request("POST", "/order", json=payload)
        if not isinstance(data, dict):
            raise FireLootError("invalid_response", "Bad /order payload")
        return data

    async def order_status(
        self, reference: str, *, by_external: bool = False
    ) -> dict[str, Any]:
        params = {"by": "external"} if by_external else None
        data = await self._request("GET", f"/order/{reference}", params=params)
        if not isinstance(data, dict):
            raise FireLootError("invalid_response", "Bad /order payload")
        return data


def _price_key(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")
