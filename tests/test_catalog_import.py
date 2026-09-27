from decimal import Decimal

from app.constants.games import GAMES, match_products
from app.services.catalog_import import (
    REGION_TO_GAME,
    build_name,
    extract_qty,
    plan_import,
    price_tjs,
)
from app.utils.validators import normalize_zone, validate_zone


class _P:
    def __init__(self, name: str) -> None:
        self.name = name


def _item(sku, name, category, region, price="1.00"):
    return {
        "sku": sku,
        "name": name,
        "category": category,
        "region": region,
        "price": price,
    }


SAMPLE = [
    _item("diamonds_110", "110 алмазов", "diamonds", "CIS", "0.821"),
    _item("voucher_week", "Ваучер на неделю", "voucher", "CIS", "1.619"),
    _item("levelpass_6", "Пропуск прокачки 6 LVL", "pass", "CIS", "0.303"),
    _item("pubg_uc_325", "300 + 25 UC", "uc", "PUBG", "4.704"),
    _item("bs_gold_100", "100 + 5 Gold", "gold", "BLOOD STRIKE", "0.821"),
    _item("ab_bonds_60", "60 + 6 Bonds", "bonds", "ARENA BREAKOUT", "0.838"),
    _item(
        "abi_bonds_100",
        "100 Bonds",
        "bonds",
        "AB INFINITE",
        "1.103",
    ),
    _item("hok_tokens_80", "80 Tokens", "tokens", "HONOR OF KINGS", "0.897"),
    _item("mr_lattice_100", "100 Lattice", "lattice", "MARVEL RIVALS", "0.931"),
    _item("mlbb_diamonds_32", "32 + 3 Diamonds", "diamonds", "MLBB RUSSIA"),
    _item(
        "mlbbcis_diamonds_50",
        "50 + 5 Diamonds",
        "diamonds",
        "MLBB Кыргызстан, Беларусь",
    ),
    # Regions that must NOT be imported (other game servers)
    _item("id_diamonds_5", "5 Diamonds", "diamonds", "INDONESIA"),
    _item("br_diamonds_110", "100 + 10 Diamonds", "diamonds", "BRAZIL"),
    _item("bd_diamonds_25", "25 Diamonds", "diamonds", "BANGLADESH"),
]


def test_build_name_ff_cis():
    assert build_name(SAMPLE[0]) == "FF 110 Diamonds"
    assert build_name(SAMPLE[1]) == "FF Weekly Voucher"
    assert build_name(SAMPLE[2]) == "FF Level Up Pass 6"


def test_build_name_other_games():
    assert build_name(SAMPLE[3]) == "PUBG 325 UC"
    assert build_name(SAMPLE[4]) == "Blood Strike 100 Gold"
    assert build_name(SAMPLE[5]) == "Arena Breakout 60 Bonds"
    assert build_name(SAMPLE[6]) == "Arena Breakout Infinite 100 Bonds"
    assert build_name(SAMPLE[7]) == "Honor of Kings 80 Tokens"
    assert build_name(SAMPLE[8]) == "Marvel Rivals 100 Lattice"
    assert build_name(SAMPLE[9]) == "MLBB RU 32 Diamonds"
    assert build_name(SAMPLE[10]) == "MLBB CIS 50 Diamonds"


def test_foreign_regions_are_skipped():
    for item in SAMPLE[11:]:
        assert build_name(item) is None


def test_qty_prefers_sku_suffix():
    # "300 + 25 UC" → the SKU holds the real amount (300 + 25 bonus)
    assert extract_qty(SAMPLE[3]) == 325
    assert extract_qty(SAMPLE[0]) == 110
    assert extract_qty({"sku": "voucher_week", "name": "Ваучер на неделю"}) == 0


def test_price_is_tjs_with_margin_and_half_step():
    # 0.821 USD × 10.7 × 1.05 = 9.23 → 9.00 TJS (rounded to 0.50)
    assert price_tjs("0.821") == Decimal("9.00")
    # 4.704 × 10.7 × 1.05 = 53.04 → 53.00 TJS
    assert price_tjs("4.704") == Decimal("53.00")
    assert price_tjs("garbage") == Decimal("0.50")


def test_plan_import_only_sellable_regions():
    plan = plan_import(SAMPLE)
    skus = {sku for _, _, _, sku in plan}
    assert len(plan) == 11
    assert "id_diamonds_5" not in skus
    assert "br_diamonds_110" not in skus
    assert "diamonds_110" in skus
    assert "mlbbcis_diamonds_50" in skus


def test_plan_import_dedupes_and_prices():
    plan = plan_import(SAMPLE + SAMPLE)
    assert len(plan) == 11
    by_sku = {sku: (name, qty, price) for name, qty, price, sku in plan}
    name, qty, price = by_sku["diamonds_110"]
    assert (name, qty) == ("FF 110 Diamonds", 110)
    assert isinstance(price, Decimal) and price > 0


def test_every_imported_name_belongs_to_exactly_one_game():
    plan = plan_import(SAMPLE)
    for name, _, _, sku in plan:
        owners = [game.key for game in GAMES if match_products(game.key, [_P(name)])]
        assert len(owners) == 1, f"{sku} -> {name} owned by {owners}"


def test_region_map_points_to_known_games():
    from app.constants.games import GAME_BY_KEY

    for region, (game_key, prefix) in REGION_TO_GAME.items():
        assert game_key in GAME_BY_KEY, region
        assert prefix.startswith(GAME_BY_KEY[game_key].product_prefixes[0]) or any(
            prefix.startswith(p) for p in GAME_BY_KEY[game_key].product_prefixes
        ), (region, prefix)


def test_mlbb_requires_zone():
    from app.constants.games import game_needs_zone

    assert game_needs_zone("mlbb_ru")
    assert game_needs_zone("mlbb_cis")
    assert not game_needs_zone("ff")
    assert not game_needs_zone("pubg")


def test_zone_validator():
    assert validate_zone("2001") == (True, None)
    assert validate_zone(" 2001 ") == (True, None)
    assert normalize_zone("@2001") == "2001"
    ok, error = validate_zone("abc")
    assert not ok and error
    assert not validate_zone("")[0]
    assert not validate_zone("1")[0]


def test_button_labels_are_rendered_in_every_language():
    from app.bot.keyboards.topup import format_product_button
    from app.i18n import LANGS, set_lang, t

    class _Prod:
        def __init__(self, name, price):
            self.name = name
            self.price = price

    try:
        for name, qty, price, sku in plan_import(SAMPLE):
            for lang in LANGS:
                set_lang(lang)
                label = format_product_button(_Prod(name, price))
                assert f"{price} {t('unit.currency')}" in label, (sku, lang, label)
                # FireLoot's own Russian wording must never leak into the UI
                assert "алмазов" not in label, (sku, lang, label)
                assert "Ваучер на" not in label, (sku, lang, label)
                assert "Пропуск" not in label, (sku, lang, label)
    finally:
        set_lang("ru")


class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _FakeSession:
    def __init__(self, products):
        self.products = list(products)
        self.added = []

    async def execute(self, stmt):
        return _FakeResult(list(self.products))

    def add(self, obj):
        self.added.append(obj)
        self.products.append(obj)

    async def flush(self):
        return None


def _product(name, price, *, diamonds=0, sku=None, active=True):
    from app.database.models import Product

    return Product(
        name=name,
        diamonds=diamonds,
        price=Decimal(price),
        currency="TJS",
        is_active=active,
        sku=sku,
    )


async def test_import_keeps_owner_prices_and_deactivates_unknown():
    from app.services.catalog_import import import_catalog

    kept = _product("FF 110 Diamonds", "12.34", diamonds=110)
    legacy = _product("FF 10 Diamonds", "5.00", diamonds=10)
    session = _FakeSession([kept, legacy])

    stats = await import_catalog(session, products=SAMPLE)

    # price set by the owner must never be touched on re-import
    assert kept.price == Decimal("12.34")
    assert kept.sku == "diamonds_110"
    assert kept.is_active is True
    # unknown products stop selling
    assert legacy.is_active is False

    added = {p.name: p for p in session.added}
    assert added["PUBG 325 UC"].price == price_tjs("4.704")
    assert added["PUBG 325 UC"].sku == "pubg_uc_325"
    assert len(added) == stats["created"] == 10
    assert stats["deactivated"] == 1
