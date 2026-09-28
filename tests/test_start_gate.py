"""The bot must stay closed for users who are not subscribed to the channel."""
from types import SimpleNamespace

from app.bot.handlers import start as start_module
from app.i18n import t


class _FakeMessage:
    def __init__(self) -> None:
        self.photo = self.video = self.document = None
        self.animation = self.audio = self.voice = self.sticker = None
        self.replies: list[tuple[str, object]] = []
        self.edits: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None, **kwargs):
        self.replies.append((text, reply_markup))
        return SimpleNamespace()

    async def edit_text(self, text, reply_markup=None, **kwargs):
        self.edits.append((text, reply_markup))
        return True


def _message(user_id: int = 1) -> _FakeMessage:
    msg = _FakeMessage()
    msg.from_user = SimpleNamespace(id=user_id, username="tester", first_name="Tester")
    msg.bot = object()
    return msg


def _call(user_id: int = 1) -> SimpleNamespace:
    call = SimpleNamespace()
    call.from_user = SimpleNamespace(id=user_id, username="tester", first_name="Tester")
    call.bot = object()
    call.message = _message(user_id)
    call.replies: list[tuple[str | None, bool]] = []

    async def _answer(text=None, show_alert=False, **kwargs):
        call.replies.append((text, show_alert))

    call.answer = _answer
    return call


def _db_user() -> SimpleNamespace:
    return SimpleNamespace(
        telegram_id=1,
        username="tester",
        first_name="Tester",
        balance=0,
        is_admin=False,
    )


def _patch(monkeypatch, member: bool) -> None:
    async def _is_subscribed(bot, user_id, *args, **kwargs):
        return member

    class _UserService:
        def __init__(self, session) -> None:
            self.session = session

        async def register_user(self, **kwargs):
            return _db_user(), False

    monkeypatch.setattr(start_module, "is_subscribed", _is_subscribed)
    monkeypatch.setattr(start_module, "UserService", _UserService)


def _callbacks(markup) -> set[str]:
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    }


async def test_start_is_blocked_without_subscription(monkeypatch) -> None:
    _patch(monkeypatch, member=False)
    message = _message()
    await start_module.cmd_start(message)

    assert len(message.replies) == 1
    _, markup = message.replies[0]
    callbacks = _callbacks(markup)
    assert "sub:check" in callbacks  # join / check buttons only
    assert not any(c.startswith("menu:") for c in callbacks)


async def test_start_opens_menu_for_member(monkeypatch) -> None:
    _patch(monkeypatch, member=True)
    message = _message()
    await start_module.cmd_start(message)

    assert len(message.replies) == 1
    _, markup = message.replies[0]
    assert "menu:topup" in _callbacks(markup)


async def test_check_button_rejects_non_member(monkeypatch) -> None:
    _patch(monkeypatch, member=False)
    call = _call()
    await start_module.on_subscribe_check(call, db_user=_db_user(), session=None)

    assert call.replies, "the user must get feedback"
    text, show_alert = call.replies[0]
    assert show_alert is True
    assert text == t("sub.not_joined")
    assert call.message.edits == []  # menu must NOT open


async def test_check_button_opens_menu_for_member(monkeypatch) -> None:
    _patch(monkeypatch, member=True)
    call = _call()
    await start_module.on_subscribe_check(call, db_user=_db_user(), session=None)

    assert call.replies and call.replies[0][0] == t("sub.ok")
    assert len(call.message.edits) == 1
    _, markup = call.message.edits[0]
    assert "menu:topup" in _callbacks(markup)
