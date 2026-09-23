from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants.games import GAMES
from app.database.models import Product

CANCEL_TEXT = "❌ Бекор кардан"


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
                text=f"{p.name} · {p.price} {p.currency}",
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


def get_receipt_keyboard() -> InlineKeyboardMarkup:
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


def get_receipt_keyboard() -> InlineKeyboardMarkup:
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
