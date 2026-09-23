from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Омор", callback_data="admin:stats"),
                InlineKeyboardButton(text="📦 Фармоишҳо", callback_data="admin:orders"),
            ],
            [
                InlineKeyboardButton(text="⏳ Қабул", callback_data="admin:pending"),
                InlineKeyboardButton(text="👥 Корбарон", callback_data="admin:users"),
            ],
            [
                InlineKeyboardButton(text="💎 Маҳсулотҳо", callback_data="admin:products"),
                InlineKeyboardButton(text="💰 Пардохтҳо", callback_data="admin:payments"),
            ],
            [
                InlineKeyboardButton(text="🚫 Блок", callback_data="admin:block_menu"),
                InlineKeyboardButton(text="📞 Дастгирӣ", callback_data="admin:support"),
            ],
            [
                InlineKeyboardButton(text="🔙 Бозгашт", callback_data="back:menu"),
            ],
        ]
    )


def get_block_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 Блок кардан", callback_data="admin:block_ask"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Аз блок озод кардан", callback_data="admin:unblock_ask"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Илова кардани баланс", callback_data="admin:add_bal_ask"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Бозгашт", callback_data="admin:menu"),
            ],
        ]
    )


def get_order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Қабул", callback_data=f"admin:order:accept:{order_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Рад", callback_data=f"admin:order:reject:{order_id}"
                ),
            ]
        ]
    )


def get_pending_orders_keyboard(order_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"✅ Қабул №{oid}",
                callback_data=f"admin:order:accept:{oid}",
            ),
            InlineKeyboardButton(
                text=f"❌ Рад №{oid}",
                callback_data=f"admin:order:reject:{oid}",
            ),
        ]
        for oid in order_ids
    ]
    rows.append([InlineKeyboardButton(text="🔙 Бозгашт", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Бозгашт", callback_data="admin:menu")]
        ]
    )


def get_product_actions_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏸ Ғайрифаъол",
                    callback_data=f"admin:product:deactivate:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="▶️ Фаъол",
                    callback_data=f"admin:product:activate:{product_id}",
                )
            ],
            [InlineKeyboardButton(text="🔙 Бозгашт", callback_data="admin:products")],
        ]
    )
