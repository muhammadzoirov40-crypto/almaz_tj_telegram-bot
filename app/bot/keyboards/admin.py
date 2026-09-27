from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import t


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("admin.stats"), callback_data="admin:stats"),
                InlineKeyboardButton(text=t("admin.orders"), callback_data="admin:orders"),
            ],
            [
                InlineKeyboardButton(text=t("admin.pending"), callback_data="admin:pending"),
                InlineKeyboardButton(text=t("admin.users"), callback_data="admin:users"),
            ],
            [
                InlineKeyboardButton(text=t("admin.products"), callback_data="admin:products"),
                InlineKeyboardButton(text=t("admin.payments"), callback_data="admin:payments"),
            ],
            [
                InlineKeyboardButton(text=t("admin.block"), callback_data="admin:block_menu"),
                InlineKeyboardButton(text=t("admin.support"), callback_data="admin:support"),
            ],
            [
                InlineKeyboardButton(text=t("btn.back"), callback_data="back:menu"),
            ],
        ]
    )


def get_block_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("admin.block_ask"), callback_data="admin:block_ask"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("admin.unblock_ask"), callback_data="admin:unblock_ask"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("admin.add_balance"), callback_data="admin:add_bal_ask"
                )
            ],
            [
                InlineKeyboardButton(text=t("btn.back"), callback_data="admin:menu"),
            ],
        ]
    )


def get_order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.accept"), callback_data=f"admin:order:accept:{order_id}"
                ),
                InlineKeyboardButton(
                    text=t("btn.reject"), callback_data=f"admin:order:reject:{order_id}"
                ),
            ]
        ]
    )


def get_pending_orders_keyboard(order_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{t('btn.accept')} №{oid}",
                callback_data=f"admin:order:accept:{oid}",
            ),
            InlineKeyboardButton(
                text=f"{t('btn.reject')} №{oid}",
                callback_data=f"admin:order:reject:{oid}",
            ),
        ]
        for oid in order_ids
    ]
    rows.append([InlineKeyboardButton(text=t("btn.back"), callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn.back"), callback_data="admin:menu")]
        ]
    )


def get_balance_topup_approved_keyboard(
    request_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("admin.refund"),
                    callback_data=f"admin:bal:refund:{request_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.back"), callback_data="admin:menu"
                )
            ],
        ]
    )


def get_product_actions_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("admin.deactivate"),
                    callback_data=f"admin:product:deactivate:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("admin.activate"),
                    callback_data=f"admin:product:activate:{product_id}",
                )
            ],
            [InlineKeyboardButton(text=t("btn.back"), callback_data="admin:products")],
        ]
    )
