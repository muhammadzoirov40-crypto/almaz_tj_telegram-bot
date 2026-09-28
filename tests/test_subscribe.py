from types import SimpleNamespace

from app.bot.keyboards.main import get_subscribe_keyboard, _channel_join_url
from app.services.subscribe_service import default_chat_ref, is_subscribed


class FakeBot:
    def __init__(
        self, status: str = "member", error: bool = False, is_member: bool = True
    ) -> None:
        self.status = status
        self.error = error
        self.is_member = is_member
        self.calls: list[tuple[str | int, int]] = []

    async def get_chat_member(self, chat_ref, user_id):
        self.calls.append((chat_ref, user_id))
        if self.error:
            raise RuntimeError("telegram api down")
        payload = {"status": self.status}
        if self.status == "restricted":
            payload["is_member"] = self.is_member
        return SimpleNamespace(**payload)


async def test_member_passes() -> None:
    bot = FakeBot(status="member")
    assert await is_subscribed(bot, 1, chat_ref="@chan") is True
    assert bot.calls == [("@chan", 1)]


async def test_left_user_blocked() -> None:
    bot = FakeBot(status="left")
    assert await is_subscribed(bot, 1, chat_ref="@chan") is False


async def test_admin_and_owner_pass() -> None:
    for status in ("administrator", "creator"):
        bot = FakeBot(status=status)
        assert await is_subscribed(bot, 1, chat_ref="@chan") is True


async def test_api_error_fails_open() -> None:
    bot = FakeBot(error=True)
    assert await is_subscribed(bot, 1, chat_ref="@chan") is True


async def test_restricted_member_depends_on_is_member() -> None:
    assert await is_subscribed(
        FakeBot(status="restricted", is_member=True), 1, chat_ref="@chan"
    ) is True
    assert await is_subscribed(
        FakeBot(status="restricted", is_member=False), 1, chat_ref="@chan"
    ) is False


async def test_disabled_gate_passes() -> None:
    bot = FakeBot(status="left")
    assert await is_subscribed(bot, 1, chat_ref=None) is True
    assert bot.calls == []


def test_default_chat_ref_prefers_id() -> None:
    assert default_chat_ref() is not None


def test_join_url_uses_username() -> None:
    assert _channel_join_url().startswith("https://t.me/")


def test_join_url_prefers_invite_link(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(
        settings, "required_channel_invite_url", "https://t.me/+abcDEF"
    )
    assert _channel_join_url() == "https://t.me/+abcDEF"


def test_subscribe_keyboard_has_two_buttons() -> None:
    keyboard = get_subscribe_keyboard()
    rows = keyboard.inline_keyboard
    assert len(rows) == 2
    join = rows[0][0]
    check = rows[1][0]
    assert join.url and join.url.startswith("https://t.me/")
    assert check.callback_data == "sub:check"
    assert join.text and check.text


async def test_startup_refreshes_stale_invite_link(monkeypatch) -> None:
    """The join button must follow the channel's current invite link."""
    from types import SimpleNamespace

    import main as main_module
    from app.config import settings

    monkeypatch.setattr(
        settings, "required_channel_invite_url", "https://t.me/+OLD"
    )

    class _Bot:
        async def get_chat(self, ref):
            return SimpleNamespace(invite_link="https://t.me/+NEW")

    await main_module._refresh_invite_link(_Bot())
    assert settings.required_channel_invite_url == "https://t.me/+NEW"


async def test_startup_keeps_matching_invite_link(monkeypatch) -> None:
    from types import SimpleNamespace

    import main as main_module
    from app.config import settings

    monkeypatch.setattr(
        settings, "required_channel_invite_url", "https://t.me/+SAME"
    )

    class _Bot:
        async def get_chat(self, ref):
            return SimpleNamespace(invite_link="https://t.me/+SAME")

    await main_module._refresh_invite_link(_Bot())
    assert settings.required_channel_invite_url == "https://t.me/+SAME"


async def test_startup_survives_api_error(monkeypatch) -> None:
    import main as main_module
    from app.config import settings

    monkeypatch.setattr(
        settings, "required_channel_invite_url", "https://t.me/+KEEP"
    )

    class _Bot:
        async def get_chat(self, ref):
            raise RuntimeError("telegram down")

    await main_module._refresh_invite_link(_Bot())
    assert settings.required_channel_invite_url == "https://t.me/+KEEP"
