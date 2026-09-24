from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Product
from app.providers.fireloot import FireLootClient, FireLootError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Sync interval: the docs ask to refresh the catalogue every 10-15 minutes
# and never cache it for longer than an hour.
SYNC_INTERVAL = 15 * 60

_FF_DIAMONDS = re.compile(r"^FF\s+(\d+)\s*Diamonds?$", re.IGNORECASE)
_PUBG_UC = re.compile(r"^PUBG\s+(\d+)\s*UC$", re.IGNORECASE)
_BS_GOLD = re.compile(r"^Blood Strike\s+(\d+)\s*Gold$", re.IGNORECASE)


def guess_sku(product_name: str, catalog: list[dict[str, Any]]) -> Optional[str]:
    """Map a bot product to a FireLoot SKU, or None when it cannot be mapped.

    Only exact SKU matches that exist in the live catalogue are used and
    zone-required positions are skipped (the bot does not collect a zone),
    so a wrong mapping can never deliver the wrong product.
    """
    usable: dict[str, dict[str, Any]] = {}
    for item in catalog:
        sku = str(item.get("sku") or "").strip()
        if not sku or item.get("requires_zone"):
            continue
        usable[sku.lower()] = item

    def pick(*candidates: str) -> Optional[str]:
        for candidate in candidates:
            found = usable.get(candidate.lower())
            if found is not None:
                # Free Fire base SKUs must belong to the CIS catalogue.
                if candidate.lower().startswith("diamonds_"):
                    if str(found.get("region", "")).upper() != "CIS":
                        continue
                return str(found["sku"])
        return None

    name = (product_name or "").strip()

    match = _FF_DIAMONDS.match(name)
    if match:
        return pick(f"diamonds_{match.group(1)}")

    match = _PUBG_UC.match(name)
    if match:
        return pick(f"pubg_uc_{match.group(1)}")

    match = _BS_GOLD.match(name)
    if match:
        return pick(f"bs_gold_{match.group(1)}")

    # Mobile Legends needs a zone, MLBB SKUs are zone-required → skip.
    # Vouchers / Stars / Arena Breakout have no reliable naming rule.
    return None


async def sync_product_skus(
    session: AsyncSession,
    client: Optional[FireLootClient] = None,
    products: Optional[list[dict[str, Any]]] = None,
) -> dict[str, str]:
    """Assign FireLoot SKUs to the bot catalogue. Returns {name: sku}."""
    client = client or FireLootClient()
    if not client.configured:
        return {}

    if products is None:
        try:
            products = await client.products(force=True)
        except FireLootError as exc:
            logger.warning(
                "FireLoot catalogue fetch failed err=%s msg=%s", exc.code, exc.message
            )
            return {}

    result = await session.execute(
        select(Product).where(Product.is_active.is_(True))
    )
    assigned: dict[str, str] = {}
    for product in result.scalars().all():
        sku = guess_sku(product.name, products)
        if sku and product.sku != sku:
            product.sku = sku
            assigned[product.name] = sku
        elif sku:
            product.sku = sku

    await session.flush()
    if assigned:
        logger.info("FireLoot SKU mapping updated: %s", assigned)
    return assigned
