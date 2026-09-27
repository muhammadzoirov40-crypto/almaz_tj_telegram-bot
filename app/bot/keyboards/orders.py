from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.style import styled
from app.i18n import t


def get_orders_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.refresh"), callback_data="orders:refresh"
                ),
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="menu:profile"
                ),
            ]
        ]
    ))
