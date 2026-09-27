from decimal import Decimal
from types import SimpleNamespace

from app.bot.handlers.topup import _game_prompt
from app.i18n import set_lang, t


def test_prompt_without_user_keeps_plain_text() -> None:
    set_lang("tj")
    assert _game_prompt(None) == t("top.game_prompt")


def test_prompt_shows_balance() -> None:
    set_lang("tj")
    text = _game_prompt(SimpleNamespace(balance=Decimal("12.50")))
    assert "12.50" in text
    assert text.startswith(t("top.game_prompt"))


def test_prompt_balance_is_quantized() -> None:
    set_lang("tj")
    text = _game_prompt(SimpleNamespace(balance=Decimal("3")))
    assert "3.00" in text
