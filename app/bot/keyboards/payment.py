from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CANCEL_TOPUP_TEXT = "❌ Бекор кардан"


def get_balance_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="💳 Шарҷ кунед", callback_data="balance:topup"
            ),
            InlineKeyboardButton(text="🔙 Менюи асосӣ", callback_data="back:menu"),
        ],
    ]
    if is_admin:
        rows.append(
            [InlineKeyboardButton(text="🛠 Идора", callback_data="admin:menu")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_topup_amount_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 TJS", callback_data="bal:amt:10"),
                InlineKeyboardButton(text="50 TJS", callback_data="bal:amt:50"),
            ],
            [
                InlineKeyboardButton(text="100 TJS", callback_data="bal:amt:100"),
                InlineKeyboardButton(text="200 TJS", callback_data="bal:amt:200"),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Маблағи дигар", callback_data="bal:amt:custom"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Менюи асосӣ", callback_data="back:menu"),
            ],
        ]
    )


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Карти бонкӣ", callback_data="paymethod:card"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏙 Dushanbe City", callback_data="paymethod:ds"
                )
            ],
            [InlineKeyboardButton(text="🔙 Бозгашт", callback_data="balance:topup")],
        ]
    )


def get_balance_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=CANCEL_TOPUP_TEXT, callback_data="balance:cancel"
                )
            ]
        ]
    )


def get_balance_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Тасдиқи пардохт", callback_data="balance:confirm"
                ),
                InlineKeyboardButton(
                    text="❌ Бекор", callback_data="balance:cancel"
                ),
            ]
        ]
    )
