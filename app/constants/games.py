from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Game:
    key: str
    label: str
    emoji: str
    product_prefixes: tuple[str, ...] = field(default_factory=tuple)
    product_excludes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def button_text(self) -> str:
        return f"{self.emoji} {self.label}"


# Catalog shown in the bot. Product names in DEFAULT_PRODUCTS must start
# with one of `product_prefixes` (and none of `product_excludes`).
GAMES: tuple[Game, ...] = (
    Game(
        key="ff",
        label="Free Fire",
        emoji="🔥",
        product_prefixes=("FF ",),
    ),
    Game(
        key="pubg",
        label="PUBG Mobile",
        emoji="🎯",
        product_prefixes=("PUBG ",),
    ),
    Game(
        key="stars",
        label="Stars",
        emoji="⭐",
        product_prefixes=("Stars",),
    ),
    Game(
        key="bloodstrike",
        label="Blood Strike",
        emoji="🩸",
        product_prefixes=("Blood Strike ",),
    ),
    Game(
        key="arena_breakout",
        label="Arena Breakout",
        emoji="🔫",
        product_prefixes=("Arena Breakout ",),
        product_excludes=("Arena Breakout Infinite", "Arena Breakout:"),
    ),
    Game(
        key="arena_breakout_infinite",
        label="Arena Breakout: Infinite",
        emoji="💥",
        product_prefixes=("Arena Breakout Infinite", "Arena Breakout:"),
    ),
    Game(
        key="hok",
        label="Honor of Kings",
        emoji="👑",
        product_prefixes=("Honor of Kings ", "HoK "),
    ),
    Game(
        key="marvel_rivals",
        label="Marvel Rivals",
        emoji="🦸",
        product_prefixes=("Marvel Rivals ",),
    ),
    Game(
        key="mlbb_ru",
        label="Mobile Legends (RU)",
        emoji="🇷🇺",
        product_prefixes=("MLBB RU ",),
    ),
    Game(
        key="mlbb_cis",
        label="Mobile Legends (CIS)",
        emoji="🌏",
        product_prefixes=("MLBB CIS ",),
    ),
)

GAME_BY_KEY: dict[str, Game] = {game.key: game for game in GAMES}

GAME_LABELS: dict[str, str] = {game.key: game.label for game in GAMES}


def is_known_game(key: str) -> bool:
    return key in GAME_BY_KEY


def game_label(key: str) -> str:
    return GAME_LABELS.get(key, key)


def match_products(game_key: str, products: list) -> list:
    """Filter products belonging to `game_key` by name prefix."""
    game = GAME_BY_KEY.get(game_key)
    if game is None:
        return []
    matched = []
    for product in products:
        name = product.name
        if not any(name.startswith(p) for p in game.product_prefixes):
            continue
        if any(name.startswith(p) for p in game.product_excludes):
            continue
        matched.append(product)
    return matched
