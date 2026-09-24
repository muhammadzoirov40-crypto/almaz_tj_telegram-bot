from __future__ import annotations

import re
from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants.games import GAMES
from app.database.models import Product

CANCEL_TEXT = "❌ Бекор кардан"

# Product name → (emoji, unit label)
_UNIT_RULES: tuple[tuple[str, str, str], ...] = (
    ("Diamond", "💎", "Алмаз"),
    ("Ваучер", "🎟️", "Ваучер"),
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
        return f"💎 {m.group(1)} Алмаз — {price} с."

    # Vouchers
    if "Ваучер" in name:
        short = name.replace("FF ", "").strip()
        return f"🎟️ {short} — {price} с."

    # Stars: "Stars 500" → ⭐ 500 Stars — 45.00 с.
    m = re.search(r"Stars\s*(\d+)", name, flags=re.IGNORECASE)
    if m:
        return f"⭐ {m.group(1)} Stars — {price} с."

    # Generic: number + unit (UC, Gold, CR, Tokens, Lattice…)
    for needle, emoji, unit in _UNIT_RULES:
        if needle in name:
            m = re.search(
                r"(\d+)\s*" + re.escape(needle), name, flags=re.IGNORECASE
            )
            if m:
                return f"{emoji} {m.group(1)} {unit} — {price} с."
            # "PUBG 60 UC" — number before unit at end
            m = re.search(r"(\d+)\s+([A-Za-z]+)$", name)
            if m:
                return f"{emoji} {m.group(1)} {m.group(2)} — {price} с."
            break

    # Fallback: strip game prefix
    m = re.match(r"^[A-Za-z: ]+?(\d+)\s+(.+)$", name)
    if m:
        return f"{m.group(1)} {m.group(2)} — {price} с."
    return f"{name} — {price} с."


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
        [InlineKeyboardButton(text=CANCEL_TEXT, callback_data="topup:cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_uid_request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=CANCEL_TEXT, callback_data="topup:cancel"
                )
            ]
        ]
    )


def get_account_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ҳа, ҳамин ҳисобам",
                    callback_data="account:yes",
                ),
                InlineKeyboardButton(
                    text="❌ Не", callback_data="account:no"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=CANCEL_TEXT, callback_data="topup:cancel"
                )
            ],
        ]
    )


def get_ff_category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 Алмазҳо", callback_data="cat:diamonds"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎟️ Ваучер / Гузарнома", callback_data="cat:vouchers"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Бозгашт", callback_data="back:games"
                ),
            ],
        ]
    )


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
        [InlineKeyboardButton(text="🔙 Бозгашт", callback_data=back_callback)]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Пардохт кардан",
                    callback_data="order:pay",
                )
            ],
            [
                InlineKeyboardButton(
                    text=CANCEL_TEXT, callback_data="topup:cancel"
                )
            ],
        ]
    )


def get_payment_receipt_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Менюи асосӣ", callback_data="back:menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text=CANCEL_TEXT, callback_data="order:cancel"
                )
            ],
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=CANCEL_TEXT, callback_data="order:cancel")]
        ]
    )
