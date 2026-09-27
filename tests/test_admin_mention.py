from decimal import Decimal

from app.bot.handlers.admin import _user_mention
from app.database.models import User


def _user(**kwargs) -> User:
    data = {
        "id": 1,
        "telegram_id": 123456,
        "username": None,
        "first_name": "Ali",
        "balance": Decimal("0.00"),
        "is_admin": False,
        "is_active": True,
    }
    data.update(kwargs)
    return User(**data)


def test_mention_with_username() -> None:
    assert (
        _user_mention(_user(username="ali_dev"))
        == '<a href="https://t.me/ali_dev">Ali</a>'
    )


def test_mention_without_username() -> None:
    assert _user_mention(_user()) == '<a href="tg://user?id=123456">Ali</a>'


def test_mention_missing_name_falls_back_to_id() -> None:
    assert (
        _user_mention(_user(first_name=None))
        == '<a href="tg://user?id=123456">ID 123456</a>'
    )


def test_mention_none_user() -> None:
    assert _user_mention(None) == "—"


def test_mention_escapes_html() -> None:
    assert "&lt;b&gt;" in _user_mention(_user(first_name="<b>"))
