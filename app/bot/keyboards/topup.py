from __future__ import annotations

import re
from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.style import styled
from app.constants.games import GAMES
from app.database.models import Product
from app.i18n import t

# Product name → (emoji, unit label key)
_UNIT_RULES: tuple[tuple[str, str, str], ...] = (
    ("Diamond", "💎", "unit.diamond"),
    ("Ваучер", "🎟️", "unit.voucher"),
    ("UC", "🎯", "UC"),
    ("Stars", "⭐", "Stars"),
    ("Gold", "🩸", "Gold"),
    ("CR", "🔫", "CR"),
    ("Tokens", "👑", "Tokens"),
    ("Lattice", "🦸", "Lattice"),
)


def _price_str(value: Decimal | str | float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def format_product_button(product: Product) -> str:
    """Pretty label: 💎 110 Алмаз — 9.00 с."""
    name = product.name or ""
    price = _price_str(product.price)

    # FF / MLBB diamonds: "FF 110 Diamonds" → 💎 110 Алмаз — 9.00 с.
    m = re.search(r"(\d+)\s*Diamonds?", name, flags=re.IGNORECASE)
    if m:
        return (
            f"💎 {m.group(1)} {t('unit.diamond')} — "
            f"{price} {t('unit.currency')}"
        )

    # Vouchers
    if "Ваучер" in name:
        short = name.replace("FF ", "").strip()
        return f"🎟️ {short} — {price} {t('unit.currency')}"

    # Stars: "Stars 500" → ⭐ 500 Stars — 45.00 с.
    m = re.search(r"Stars\s*(\d+)", name, flags=re.IGNORECASE)
    if m:
        return f"⭐ {m.group(1)} Stars — {price} {t('unit.currency')}"

    # Generic: number + unit (UC, Gold, CR, Tokens, Lattice…)
    for needle, emoji, unit in _UNIT_RULES:
        if needle in name:
            m = re.search(
                r"(\d+)\s*" + re.escape(needle), name, flags=re.IGNORECASE
            )
            if m:
                return (
                    f"{emoji} {m.group(1)} {t(unit)} — "
                    f"{price} {t('unit.currency')}"
                )
            # "PUBG 60 UC" — number before unit at end
            m = re.search(r"(\d+)\s+([A-Za-z]+)$", name)
            if m:
                return (
                    f"{emoji} {m.group(1)} {m.group(2)} — "
                    f"{price} {t('unit.currency')}"
                )
            break

    # Fallback: strip game prefix
    m = re.match(r"^[A-Za-z: ]+?(\d+)\s+(.+)$", name)
    if m:
        return f"{m.group(1)} {m.group(2)} — {price} {t('unit.currency')}"
    return f"{name} — {price} {t('unit.currency')}"


def get_game_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=game.button_text,
            callback_data=f"game:{game.key}",
        )
        for game in GAMES
    ]
    rows: list[list[InlineKeyboardButton]] = [
        buttons[i : i + 2] for i in range(0, len(buttons), 2)
    ]
    rows.append(
        [InlineKeyboardButton(text=t("btn.back"), callback_data="back:menu")]
    )
    return styled(InlineKeyboardMarkup(inline_keyboard=rows))


def get_uid_request_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="back:products"
                ),
                InlineKeyboardButton(
                    text=t("btn.cancel"), callback_data="topup:cancel"
                ),
            ]
        ]
    ))


def get_account_confirm_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.yes_account"),
                    callback_data="account:yes",
                ),
                InlineKeyboardButton(
                    text=t("btn.no"), callback_data="account:no"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="back:uid"
                ),
                InlineKeyboardButton(
                    text=t("btn.cancel"), callback_data="topup:cancel"
                ),
            ],
        ]
    ))


def get_ff_category_keyboard() -> InlineKeyboardMarkup:
    markup = styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.diamonds"), callback_data="cat:diamonds"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.vouchers"),
                    callback_data="cat:vouchers",
                    style="primary",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.levelpass"),
                    callback_data="cat:levelpass",
                    style="primary",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="back:games"
                ),
            ],
        ]
    ))
    # Level Up Pass keeps its own neutral (dark) colour.
    markup.inline_keyboard[2][0].style = None
    return markup


def get_products_keyboard(
    products: list[Product],
    balance: str | None = None,
    back_callback: str = "back:menu",
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=format_product_button(p),
                callback_data=f"product:{p.id}",
            )
        ]
        for p in products
    ]
    buttons.append(
        [InlineKeyboardButton(text=t("btn.back"), callback_data=back_callback)]
    )
    markup = styled(InlineKeyboardMarkup(inline_keyboard=buttons))
    _paint_product_buttons(markup)
    return markup


def _paint_product_buttons(markup: InlineKeyboardMarkup) -> None:
    """Level passes / vouchers get their own colour next to the diamonds."""
    for row in markup.inline_keyboard:
        for button in row:
            if not (button.callback_data or "").startswith("product:"):
                continue
            if "Level Up Pass" in button.text:
                button.style = None  # neutral grey, so it stands apart
            elif "Voucher" in button.text:
                button.style = "primary"  # blue


def get_order_confirm_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.pay"),
                    callback_data="order:pay",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="back:products"
                ),
                InlineKeyboardButton(
                    text=t("btn.cancel"), callback_data="topup:cancel"
                ),
            ],
        ]
    ))


def get_payment_receipt_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.back_menu"), callback_data="back:menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.cancel"), callback_data="order:cancel"
                )
            ],
        ]
    ))


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn.cancel"), callback_data="order:cancel")]
        ]
    ))
