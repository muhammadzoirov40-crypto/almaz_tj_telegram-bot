from app.bot.keyboards.payment import get_payment_method_keyboard


def test_only_dushanbe_city_offered() -> None:
    rows = get_payment_method_keyboard().inline_keyboard
    callbacks = [btn.callback_data for row in rows for btn in row]
    assert callbacks == ["paymethod:ds", "balance:topup"]


def test_no_alif_button() -> None:
    texts = [
        btn.text
        for row in get_payment_method_keyboard().inline_keyboard
        for btn in row
    ]
    assert not any("Alif" in t for t in texts)
