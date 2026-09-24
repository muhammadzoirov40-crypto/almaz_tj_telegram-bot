from app.bot.handlers.balance import _format_payment_number
from app.providers.fireloot import FireLootClient

PRODUCTS = [
    {"sku": "diamonds_110", "category": "diamonds", "region": "CIS", "price": "0.89"},
    {"sku": "diamonds_11", "category": "diamonds", "region": "CIS", "price": "0.11"},
    {"sku": "evo_30d", "category": "pass", "region": "CIS", "price": "2.40"},
    {"sku": "pubg_uc_60", "category": "uc", "region": "PUBG", "price": "0.91"},
    {
        "sku": "mlbb_diamonds_32",
        "category": "diamonds",
        "region": "MLBB RUSSIA",
        "requires_zone": True,
        "price": "0.61",
    },
]


def _client() -> FireLootClient:
    return FireLootClient(api_url="https://partner.firelootshop.com/api/v1", api_key="k")


def test_pick_sku_ff_uses_cheapest_cis_diamonds():
    assert _client().pick_sku(PRODUCTS, "ff") == "diamonds_11"


def test_pick_sku_pubg_uses_prefixed_sku():
    assert _client().pick_sku(PRODUCTS, "pubg") == "pubg_uc_60"


def test_pick_sku_skips_zone_required_and_unknown_game():
    assert _client().pick_sku(PRODUCTS, "mlbb_ru") is None
    assert _client().pick_sku(PRODUCTS, "stars") is None


def test_pick_sku_falls_back_without_catalog():
    assert _client().pick_sku([], "ff") == "diamonds_110"


def test_candidate_skus_appends_static_fallback():
    assert _client().candidate_skus(PRODUCTS, "ff") == [
        "diamonds_11",
        "diamonds_110",
    ]
    assert _client().candidate_skus([], "pubg") == ["pubg_uc_60"]


def test_client_requires_key():
    assert FireLootClient(api_key="").configured is False
    assert _client().configured is True


def test_format_payment_number_adds_country_code():
    assert _format_payment_number("002119831") == "+992 002119831"
    assert _format_payment_number("+992 002119831") == "+992 002119831"
    assert _format_payment_number("") == ""
    assert _format_payment_number("12345") == "12345"
