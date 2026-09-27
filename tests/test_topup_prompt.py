from decimal import Decimal
from types import SimpleNamespace

from app.bot.handlers.topup import GAME_PROMPT, _game_prompt


def test_prompt_without_user_keeps_plain_text() -> None:
    assert _game_prompt(None) == GAME_PROMPT


def test_prompt_shows_balance() -> None:
    text = _game_prompt(SimpleNamespace(balance=Decimal("12.50")))
    assert "💳 Хисоби шумо: 12.50 с." in text
    assert text.startswith(GAME_PROMPT)


def test_prompt_balance_is_quantized() -> None:
    text = _game_prompt(SimpleNamespace(balance=Decimal("3")))
    assert "3.00" in text
