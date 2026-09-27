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


def test_ff_categories_have_own_colors():
    from app.bot.keyboards.topup import get_ff_category_keyboard

    styles = _styles(get_ff_category_keyboard())
    assert styles["cat:diamonds"] == "success"
    assert styles["cat:vouchers"] == "primary"
    assert styles["cat:levelpass"] is None  # dark / neutral
    assert styles["back:games"] == "danger"


def test_product_buttons_split_by_kind():
    from decimal import Decimal

    from app.bot.keyboards.topup import get_products_keyboard
    from app.database.models import Product

    def _p(pid, name):
        return Product(
            id=pid,
            name=name,
            diamonds=0,
            price=Decimal("9.00"),
            currency="TJS",
            is_active=True,
        )

    markup = get_products_keyboard(
        [
            _p(1, "FF Level Up Pass 6"),
            _p(2, "FF Weekly Voucher"),
            _p(3, "FF 110 Diamonds"),
            _p(4, "PUBG 325 UC"),
        ],
        back_callback="back:cat",
    )
    styles = _styles(markup)
    assert styles["product:1"] is None  # level pass — neutral grey
    assert styles["product:2"] == "primary"  # voucher — blue
    assert styles["product:3"] == "success"  # diamonds — green
    assert styles["product:4"] == "success"  # PUBG — green
    assert styles["back:cat"] == "danger"


def test_ff_level_pass_is_its_own_category():
    from app.bot.handlers.topup import (
        FF_CATEGORIES,
        _ff_category,
        _ff_category_label,
    )
    from app.i18n import set_lang

    assert "levelpass" in FF_CATEGORIES
    assert _ff_category("FF Level Up Pass 6") == "levelpass"
    assert _ff_category("FF Weekly Voucher") == "vouchers"
    assert _ff_category("FF 110 Diamonds") == "diamonds"
    try:
        set_lang("ru")
        assert "Level Up Pass" in _ff_category_label("levelpass")
        assert _ff_category_label("diamonds") != _ff_category_label("levelpass")
    finally:
        set_lang("ru")


def test_i18n_has_levelpass_in_every_language():
    from app.i18n import DEFAULT_LANG, LANGS, MESSAGES

    for lang in LANGS:
        assert "btn.levelpass" in MESSAGES[lang], lang
        assert "btn.vouchers" in MESSAGES[lang], lang
    # the three dictionaries must stay in sync
    reference = set(MESSAGES[DEFAULT_LANG])
    for lang in LANGS:
        assert set(MESSAGES[lang]) == reference, lang
