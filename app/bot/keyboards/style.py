"""Button colour styles (Telegram Bot API 9.4 `style` field).

Buttons are painted after the keyboard is built, so every keyboard builder can
stay declarative. Rules are based on the callback_data tokens:

- destructive actions (cancel / reject / no / delete / block) → red
- navigation (back, admin section pages, edit/page)             → blue
- neutral helpers (custom amount, copy)                         → no style
- everything else (menu, buying, accepting, url calls to action)→ green
"""

from __future__ import annotations

from typing import Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

STYLE_SUCCESS = "success"  # green — positive actions
STYLE_PRIMARY = "primary"  # blue — main/navigation actions
STYLE_DANGER = "danger"  # red — destructive actions

_DANGER_TOKENS = frozenset(
    {"cancel", "reject", "no", "delete", "block", "unblock", "stop"}
)
_PRIMARY_TOKENS = frozenset({"back", "edit", "page", "next", "prev", "set"})
_NEUTRAL_TOKENS = frozenset({"custom", "copy"})
# Admin section pages are navigation, not actions.
_ADMIN_NAV_TOKENS = frozenset(
    {"menu", "pending", "users", "orders", "products", "payments", "stats", "support"}
)

_DANGER_MARKS = "❌✖🗑"
_PRIMARY_MARKS = "🔙"
_SUCCESS_MARKS = "✅💰💳🔗📱"


def _tokens(callback_data: str) -> set[str]:
    return {part for part in callback_data.replace("_", ":").split(":") if part}


def derive_style(
    *,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    text: Optional[str] = None,
) -> Optional[str]:
    if callback_data:
        tokens = _tokens(callback_data)
        first = callback_data.split(":", 1)[0]
        if tokens & _DANGER_TOKENS:
            return STYLE_DANGER
        if first == "admin" and tokens & _ADMIN_NAV_TOKENS:
            return STYLE_PRIMARY
        if tokens & _PRIMARY_TOKENS:
            return STYLE_PRIMARY
        if tokens & _NEUTRAL_TOKENS:
            return None
        return STYLE_SUCCESS
    if url:
        return STYLE_SUCCESS
    if text:
        if any(mark in text for mark in _DANGER_MARKS):
            return STYLE_DANGER
        if any(mark in text for mark in _PRIMARY_MARKS):
            return STYLE_PRIMARY
        if any(mark in text for mark in _SUCCESS_MARKS):
            return STYLE_SUCCESS
    return None


def style_inline_button(button: InlineKeyboardButton) -> InlineKeyboardButton:
    if button.style is None:
        button.style = derive_style(
            callback_data=button.callback_data,
            url=button.url,
            text=button.text,
        )
    return button


def styled(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    for row in markup.inline_keyboard:
        for button in row:
            style_inline_button(button)
    return markup


def style_reply_button(button: KeyboardButton) -> KeyboardButton:
    if button.style is None:
        button.style = derive_style(text=button.text)
    return button


def styled_reply(markup: ReplyKeyboardMarkup) -> ReplyKeyboardMarkup:
    for row in markup.keyboard:
        for button in row:
            style_reply_button(button)
    return markup
