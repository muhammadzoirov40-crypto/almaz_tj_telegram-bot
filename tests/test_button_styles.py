from app.bot.keyboards.style import derive_style, styled
from app.bot.keyboards.main import get_main_menu_keyboard
from app.bot.keyboards.payment import (
    get_balance_confirm_keyboard,
    get_topup_amount_keyboard,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _styles(markup: InlineKeyboardMarkup) -> dict[str, str | None]:
    return {
        button.callback_data: button.style
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    }


def test_derive_style_rules():
    assert derive_style(callback_data="topup:cancel") == "danger"
    assert derive_style(callback_data="account:no") == "danger"
    assert derive_style(callback_data="admin:block_ask") == "danger"
    assert derive_style(callback_data="admin:accept") == "success"
    assert derive_style(callback_data="balance:topup") == "success"
    assert derive_style(callback_data="menu:promo") == "success"
    assert derive_style(callback_data="admin:pending") == "primary"
    assert derive_style(callback_data="back:menu") == "danger"
    assert derive_style(callback_data="bal:amt:custom") is None
    assert derive_style(url="https://t.me/+abc") == "success"
    assert derive_style(text="❌ Бекор") == "danger"
    assert derive_style(text="🔙 Бозгашт") == "danger"
    assert derive_style(text="💰 Пардохт") == "success"
    assert derive_style(text="Hello") is None


def test_main_menu_is_colored():
    styles = _styles(get_main_menu_keyboard(is_admin=True))
    assert styles["menu:topup"] == "success"
    assert styles["balance:topup"] == "success"
    assert styles["menu:support"] == "success"
    assert styles["admin:menu"] == "primary"


def test_pay_and_cancel_colors():
    styles = _styles(get_balance_confirm_keyboard())
    assert styles["balance:confirm"] == "success"
    assert styles["balance:cancel"] == "danger"


def test_amount_buttons_and_back():
    styles = _styles(get_topup_amount_keyboard())
    assert styles["bal:amt:10"] == "success"
    assert styles["bal:amt:custom"] is None
    assert styles["back:menu"] == "danger"


def test_styled_is_idempotent_and_serializes_style():
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Pay", callback_data="x", style="primary"
                )
            ],
            [InlineKeyboardButton(text="Go", url="https://t.me/")],
        ]
    )
    styled(markup)
    # explicit style wins over the derived one
    assert markup.inline_keyboard[0][0].style == "primary"
    assert markup.inline_keyboard[1][0].style == "success"
    assert '"style":' in markup.model_dump_json(exclude_none=True)


def test_back_button_is_red_even_when_callback_is_not_back():
    """Payment screens label the Back button with a normal callback."""
    from app.bot.keyboards.payment import get_payment_method_keyboard

    styles = _styles(get_payment_method_keyboard())
    assert styles["paymethod:ds"] == "success"  # Dushanbe City
    back = [
        b
        for row in get_payment_method_keyboard().inline_keyboard
        for b in row
        if b.text.startswith("🔙")
    ]
    assert back and all(b.style == "danger" for b in back)
