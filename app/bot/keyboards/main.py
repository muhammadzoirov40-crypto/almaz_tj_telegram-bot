from __future__ import annotations

from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.config import settings
from app.i18n import t

# Kept for legacy `F.text ==` filters; live buttons use t("btn.*").
MAIN_MENU_TEXT = "🏠 Асосӣ"
ORDERS_TEXT = "📦 Фармоишҳои ман"
PROFILE_TEXT = "👤 Саҳифаи ман"
BALANCE_TEXT = "💰 Баланс"
PROMO_TEXT = "🎁 Пешниҳодҳо"
SUPPORT_TEXT = "📞 Дастгирӣ ба админ"
TOPUP_TEXT = "💎 Донат"
ADMIN_TEXT = "🛠 Админ"
CHANNEL_TEXT = "📢 Канал"

SUBSCRIBE_CALLBACK = "sub:check"
LANGUAGE_CALLBACK = "lang:show"


def _channel_join_url() -> str:
    invite = (settings.required_channel_invite_url or "").strip()
    if invite:
        return invite
    username = (settings.required_channel_username or "").strip().lstrip("@")
    if not username:
        return "https://t.me/"
    return f"https://t.me/{username}"


def get_subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("sub.join"), url=_channel_join_url()
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("sub.check"), callback_data=SUBSCRIBE_CALLBACK
                )
            ],
        ]
    )


def get_language_keyboard() -> InlineKeyboardMarkup:
    from app.i18n import LANGS, LANG_LABELS

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LANG_LABELS[lang], callback_data=f"lang:set:{lang}"
                )
            ]
            for lang in LANGS
        ]
        + [
            [
                InlineKeyboardButton(
                    text=t("btn.back_menu"), callback_data="back:menu"
                )
            ]
        ]
    )


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t("btn.donate"), callback_data="menu:topup")],
        [
            InlineKeyboardButton(
                text=t("btn.add_balance"), callback_data="balance:topup"
            ),
            InlineKeyboardButton(
                text=t("btn.balance"), callback_data="menu:balance"
            ),
        ],
        [InlineKeyboardButton(text=t("btn.promo"), callback_data="menu:promo")],
        [
            InlineKeyboardButton(
                text=t("btn.profile"), callback_data="menu:profile"
            )
        ],
        [
            InlineKeyboardButton(
                text=t("btn.buyers"), callback_data="menu:buyers"
            )
        ],
        [
            InlineKeyboardButton(
                text=t("btn.support"), callback_data="menu:support"
            )
        ],
        [
            InlineKeyboardButton(
                text=t("btn.language"), callback_data=LANGUAGE_CALLBACK
            )
        ],
    ]
    if is_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("btn.admin"), callback_data="admin:menu"
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


async def get_bot_commands(is_admin: bool = False) -> list[BotCommand]:
    commands = [
        BotCommand(command="start", description=t("cmd.start")),
        BotCommand(command="menu", description=t("cmd.menu")),
        BotCommand(command="topup", description=t("cmd.topup")),
        BotCommand(command="orders", description=t("cmd.orders")),
        BotCommand(command="profile", description=t("cmd.profile")),
        BotCommand(command="balance", description=t("cmd.balance")),
        BotCommand(command="support", description=t("cmd.support")),
    ]
    if is_admin:
        commands.append(
            BotCommand(command="admin", description=t("cmd.admin"))
        )
    return commands
