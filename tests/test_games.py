from __future__ import annotations

from types import SimpleNamespace

from app.constants.games import (
    GAME_BY_KEY,
    GAMES,
    game_label,
    is_known_game,
    match_products,
)


def _product(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def test_catalog_has_provider_games():
    expected = {
        "ff",
        "pubg",
        "stars",
        "bloodstrike",
        "arena_breakout",
        "arena_breakout_infinite",
        "hok",
        "marvel_rivals",
        "mlbb_ru",
        "mlbb_cis",
    }
    assert expected == {g.key for g in GAMES}


def test_known_games_and_labels():
    assert is_known_game("bloodstrike")
    assert not is_known_game("unknown_game")
    assert game_label("pubg") == "PUBG Mobile"
    assert game_label("nope") == "nope"


def test_callback_data_fits_telegram_limit():
    for game in GAMES:
        assert len(f"game:{game.key}".encode()) <= 64


def test_match_products_by_prefix():
    products = [
        _product("FF 110 Diamonds"),
        _product("PUBG 60 UC"),
        _product("Stars 100"),
        _product("Blood Strike 80 Gold"),
        _product("Arena Breakout 60 CR"),
        _product("Arena Breakout: Infinite 60 CR"),
        _product("Honor of Kings 80 Tokens"),
        _product("Marvel Rivals 100 Lattice"),
        _product("MLBB RU 86 Diamonds"),
        _product("MLBB CIS 86 Diamonds"),
    ]

    assert [p.name for p in match_products("ff", products)] == ["FF 110 Diamonds"]
    assert [p.name for p in match_products("pubg", products)] == ["PUBG 60 UC"]
    assert [p.name for p in match_products("bloodstrike", products)] == [
        "Blood Strike 80 Gold"
    ]
    assert [p.name for p in match_products("arena_breakout", products)] == [
        "Arena Breakout 60 CR"
    ]
    assert [p.name for p in match_products("arena_breakout_infinite", products)] == [
        "Arena Breakout: Infinite 60 CR"
    ]
    assert [p.name for p in match_products("hok", products)] == [
        "Honor of Kings 80 Tokens"
    ]
    assert [p.name for p in match_products("marvel_rivals", products)] == [
        "Marvel Rivals 100 Lattice"
    ]
    assert [p.name for p in match_products("mlbb_ru", products)] == [
        "MLBB RU 86 Diamonds"
    ]
    assert [p.name for p in match_products("mlbb_cis", products)] == [
        "MLBB CIS 86 Diamonds"
    ]


def test_match_products_unknown_game():
    assert match_products("nope", [_product("FF 110 Diamonds")]) == []


def test_game_keys_unique():
    keys = [g.key for g in GAMES]
    assert len(keys) == len(set(keys))
    assert set(GAME_BY_KEY) == set(keys)
