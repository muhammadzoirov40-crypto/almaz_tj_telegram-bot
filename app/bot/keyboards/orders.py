from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_orders_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Навсозӣ", callback_data="orders:refresh"
                ),
                InlineKeyboardButton(
                    text="🔙 Назад", callback_data="menu:profile"
                ),
            ]
        ]
    )
