from __future__ import annotations

from types import SimpleNamespace

from app.bot.middlewares.subscription import is_subscribed_status


def _member(status: str, is_member: bool | None = None) -> SimpleNamespace:
    data = {"status": status}
    if is_member is not None:
        data["is_member"] = is_member
    return SimpleNamespace(**data)


def test_subscribed_statuses():
    assert is_subscribed_status(_member("creator"))
    assert is_subscribed_status(_member("administrator"))
    assert is_subscribed_status(_member("member"))


def test_not_subscribed_statuses():
    assert not is_subscribed_status(_member("left"))
    assert not is_subscribed_status(_member("kicked"))


def test_restricted_with_membership():
    assert is_subscribed_status(_member("restricted", is_member=True))
    assert not is_subscribed_status(_member("restricted", is_member=False))
