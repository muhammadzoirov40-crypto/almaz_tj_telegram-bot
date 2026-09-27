from __future__ import annotations

from aiogram.types import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.bot.keyboards.style import styled, styled_reply
from app.i18n import t


def get_share_phone_keyboard() -> ReplyKeyboardMarkup:
    """One-tap: send the user's own Telegram phone number."""
    return styled_reply(ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=t("btn.share_phone"),
                    request_contact=True,
                )
            ],
            [KeyboardButton(text=t("btn.cancel"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="+992XXXXXXXXX",
    ))


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def get_balance_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t("btn.add_balance"), callback_data="balance:topup"
            ),
            InlineKeyboardButton(
                text=t("btn.back_menu"), callback_data="back:menu"
            ),
        ],
    ]
    if is_admin:
        rows.append(
            [InlineKeyboardButton(text=t("btn.admin"), callback_data="admin:menu")]
        )
    return styled(InlineKeyboardMarkup(inline_keyboard=rows))


def get_topup_amount_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
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
                    text=t("btn.custom_amount"), callback_data="bal:amt:custom"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.back_menu"), callback_data="back:menu"
                ),
            ],
        ]
    ))


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏙 Dushanbe City", callback_data="paymethod:ds"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="balance:topup"
                )
            ],
        ]
    ))


def get_balance_cancel_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="balance:topup"
                ),
                InlineKeyboardButton(
                    text=t("btn.cancel"), callback_data="balance:cancel"
                ),
            ]
        ]
    ))


def get_balance_confirm_keyboard(url: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t("btn.pay_confirm"), callback_data="balance:confirm"
            ),
            InlineKeyboardButton(
                text=t("btn.pay_cancel"), callback_data="balance:cancel"
            ),
        ]
    ]
    if url:
        rows.insert(
            0,
            [InlineKeyboardButton(text=t("btn.pay_go"), url=url)],
        )
    return styled(InlineKeyboardMarkup(inline_keyboard=rows))


def get_balance_receipt_keyboard() -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.back_menu"), callback_data="back:menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.cancel"), callback_data="balance:cancel"
                )
            ],
        ]
    ))


def get_balance_topup_review_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.accept"),
                    callback_data=f"admin:bal:accept:{request_id}",
                ),
                InlineKeyboardButton(
                    text=t("btn.reject"),
                    callback_data=f"admin:bal:reject:{request_id}",
                ),
            ]
        ]
    ))
