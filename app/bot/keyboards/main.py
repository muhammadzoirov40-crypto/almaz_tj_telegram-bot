from __future__ import annotations

from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)

MAIN_MENU_TEXT = "🏠 Асосӣ"
ORDERS_TEXT = "📦 Фармоишҳои ман"
PROFILE_TEXT = "👤 Саҳифаи ман"
BALANCE_TEXT = "💰 Баланс"
PROMO_TEXT = "🎁 Пешниҳодҳо"
SUPPORT_TEXT = "📞 Дастгирӣ"
TOPUP_TEXT = "💎 Донат"
ADMIN_TEXT = "🛠 Идора"
CHANNEL_TEXT = "📢 Канал"


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=TOPUP_TEXT, callback_data="menu:topup"),
            InlineKeyboardButton(text=ORDERS_TEXT, callback_data="menu:orders"),
        ],
        [
            InlineKeyboardButton(text=PROFILE_TEXT, callback_data="menu:profile"),
            InlineKeyboardButton(text=BALANCE_TEXT, callback_data="menu:balance"),
        ],
        [
            InlineKeyboardButton(text=PROMO_TEXT, callback_data="menu:promo"),
            InlineKeyboardButton(text=SUPPORT_TEXT, callback_data="menu:support"),
        ],
        [
            InlineKeyboardButton(
                text=CHANNEL_TEXT, url="https://t.me/_ff_almaz_tj_"
            ),
        ],
    ]
    if is_admin:
        rows.append(
            [InlineKeyboardButton(text=ADMIN_TEXT, callback_data="admin:menu")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


async def get_bot_commands(is_admin: bool = False) -> list[BotCommand]:
    commands = [
        BotCommand(command="start", description="Оғоз"),
        BotCommand(command="menu", description="Менюи асосӣ"),
        BotCommand(command="topup", description="Донат"),
        BotCommand(command="orders", description="Фармоишҳо"),
        BotCommand(command="profile", description="Саҳифаи ман"),
        BotCommand(command="balance", description="Баланс"),
        BotCommand(command="support", description="Дастгирӣ"),
    ]
    if is_admin:
        commands.append(BotCommand(command="admin", description="Идора"))
    return commands
