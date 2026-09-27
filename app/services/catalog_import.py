from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Product
from app.providers.fireloot import FireLootClient
from app.utils.logger import get_logger

logger = get_logger(__name__)

# FireLoot region → (bot game key, product name prefix).
# Only regions sellable in Tajikistan are imported — everything else
# (Indonesia, Brazil, SG, MENA…) is skipped on purpose so a user can never
# order a product that belongs to a different game server.
REGION_TO_GAME: dict[str, tuple[str, str]] = {
    "CIS": ("ff", "FF "),
    "PUBG": ("pubg", "PUBG "),
    "BLOOD STRIKE": ("bloodstrike", "Blood Strike "),
    "ARENA BREAKOUT": ("arena_breakout", "Arena Breakout "),
    "AB INFINITE": ("arena_breakout_infinite", "Arena Breakout Infinite "),
    "HONOR OF KINGS": ("hok", "Honor of Kings "),
    "MARVEL RIVALS": ("marvel_rivals", "Marvel Rivals "),
    "MLBB RUSSIA": ("mlbb_ru", "MLBB RU "),
    "MLBB Кыргызстан, Беларусь": ("mlbb_cis", "MLBB CIS "),
}

# FireLoot category → unit word used in the product name.
UNIT_BY_CATEGORY: dict[str, str] = {
    "diamonds": "Diamonds",
    "uc": "UC",
    "gold": "Gold",
    "tokens": "Tokens",
    "lattice": "Lattice",
    "bonds": "Bonds",
    "wow": "WOW Coins",
}

# Russian catalogue names (CIS Free Fire) → English, the bot UI is
# Tojik/Rus/Eng and product names stay neutral English.
NAME_OVERRIDES: dict[str, str] = {
    "Ваучер на неделю Лайт": "Weekly Lite Voucher",
    "Ваучер на неделю": "Weekly Voucher",
    "Ваучер на месяц": "Monthly Voucher",
    "Пропуск прокачки 6 LVL": "Level Up Pass 6",
    "Пропуск прокачки 10 LVL": "Level Up Pass 10",
    "Пропуск прокачки 15 LVL": "Level Up Pass 15",
    "Пропуск прокачки 20 LVL": "Level Up Pass 20",
    "Пропуск прокачки 25 LVL": "Level Up Pass 25",
    "Пропуск прокачки 30 LVL": "Level Up Pass 30",
}

_SKU_TAIL = re.compile(r"(\d+)$")
_NAME_NUM = re.compile(r"(\d[\d,]*)")

PRICE_STEP = Decimal("0.50")


def extract_qty(item: dict[str, Any]) -> int:
    """Quantity shown in the name: SKU suffix first, first number in name."""
    sku = str(item.get("sku") or "")
    match = _SKU_TAIL.search(sku)
    if match:
        return int(match.group(1))
    match = _NAME_NUM.search(str(item.get("name") or ""))
    if match:
        return int(match.group(1).replace(",", ""))
    return 0


def build_name(item: dict[str, Any]) -> Optional[str]:
    """Product name for the bot catalogue, None if the region is not sold."""
    region = str(item.get("region") or "").strip()
    mapped = REGION_TO_GAME.get(region)
    if mapped is None:
        return None
    _, prefix = mapped

    category = str(item.get("category") or "").strip()
    raw_name = str(item.get("name") or "").strip()
    if category in UNIT_BY_CATEGORY:
        qty = extract_qty(item)
        if qty:
            return f"{prefix}{qty} {UNIT_BY_CATEGORY[category]}"

    name = NAME_OVERRIDES.get(raw_name, raw_name)
    if not name:
        return None
    return f"{prefix}{name}"


def price_tjs(cost_usd: Any) -> Decimal:
    """USD partner price → TJS retail price rounded to 0.50 TJS."""
    try:
        cost = Decimal(str(cost_usd))
    except Exception:
        cost = Decimal("0")
    rate = Decimal(str(settings.catalog_usd_tjs_rate))
    margin = Decimal(str(settings.catalog_margin))
    raw = cost * rate * (Decimal("1") + margin)
    if raw <= 0:
        return PRICE_STEP
    return (raw / PRICE_STEP).to_integral_value(rounding=ROUND_HALF_UP) * PRICE_STEP


def plan_import(
    items: Iterable[dict[str, Any]],
) -> list[tuple[str, int, Decimal, str]]:
    """Catalogue entries → [(name, qty, price_tjs, sku)] for sellable regions."""
    plan: list[tuple[str, int, Decimal, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        sku = str(item.get("sku") or "").strip()
        if not sku or sku in seen:
            continue
        name = build_name(item)
        if not name:
            continue
        seen.add(sku)
        category = str(item.get("category") or "").strip()
        qty = extract_qty(item) if category in UNIT_BY_CATEGORY else 0
        plan.append((name, qty, price_tjs(item.get("price")), sku))
    return plan


async def import_catalog(
    session: AsyncSession,
    products: Optional[list[dict[str, Any]]] = None,
    *,
    client: Optional[FireLootClient] = None,
) -> dict[str, Any]:
    """Upsert the FireLoot catalogue into `products` (1:1 by SKU).

    Every sellable SKU becomes an active product with its own SKU, prices are
    recalculated from the partner price. Products not present in the catalogue
    are deactivated so the bot only sells what FireLoot can deliver.
    """
    if products is None:
        client = client or FireLootClient()
        if not client.configured:
            return {"skipped": True, "reason": "not_configured"}
        try:
            products = await client.products(force=True)
        except Exception as exc:  # keep the current catalogue on API errors
            logger.warning("FireLoot catalogue fetch failed: %s", exc)
            return {"skipped": True, "reason": "fetch_failed"}

    plan = plan_import(products)
    if not plan:
        return {"skipped": True, "reason": "empty_plan"}

    result = await session.execute(select(Product))
    existing = list(result.scalars().all())
    by_sku = {p.sku: p for p in existing if p.sku}
    by_name = {p.name: p for p in existing}

    imported_skus = {sku for _, _, _, sku in plan}
    created = 0
    updated = 0

    for name, qty, price, sku in plan:
        product = by_sku.get(sku) or by_name.get(name)
        if product is None:
            session.add(
                Product(
                    name=name,
                    diamonds=qty,
                    price=price,  # type: ignore[arg-type]
                    currency="TJS",
                    is_active=True,
                    sku=sku,
                )
            )
            created += 1
            continue

        if (
            product.name != name
            or product.sku != sku
            or product.price != price
            or product.diamonds != qty
            or product.currency != "TJS"
            or not product.is_active
        ):
            updated += 1
        product.name = name
        product.sku = sku
        product.price = price  # type: ignore[assignment]
        product.diamonds = qty
        product.currency = "TJS"
        product.is_active = True

    deactivated = 0
    for product in existing:
        if product.sku in imported_skus:
            continue
        if product.is_active:
            product.is_active = False
            deactivated += 1

    await session.flush()

    stats = {
        "catalog": len(list(products)),
        "sellable": len(plan),
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
    }
    logger.info("FireLoot catalogue imported: %s", stats)
    return stats
