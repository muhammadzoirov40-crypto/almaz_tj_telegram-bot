from app.services.fireloot_catalog import guess_sku

CATALOG = [
    {"sku": "diamonds_110", "category": "diamonds", "region": "CIS", "price": "0.89"},
    {"sku": "diamonds_341", "category": "diamonds", "region": "CIS", "price": "2.5"},
    {"sku": "pubg_uc_60", "category": "uc", "region": "PUBG", "price": "0.91"},
    {"sku": "bs_gold_100", "category": "gold", "region": "BLOOD STRIKE", "price": "0.77"},
    {"sku": "mlbb_diamonds_32", "category": "diamonds", "region": "MLBB RUSSIA",
     "requires_zone": True, "price": "0.61"},
    {"sku": "ind_diamonds_110", "category": "diamonds", "region": "IND", "price": "0.89"},
]


def test_ff_diamonds_maps_to_cis_sku():
    assert guess_sku("FF 110 Diamonds", CATALOG) == "diamonds_110"
    assert guess_sku("FF 341 Diamonds", CATALOG) == "diamonds_341"


def test_ff_unknown_amount_returns_none():
    assert guess_sku("FF 1166 Diamonds", CATALOG) is None


def test_pubg_maps_to_uc_sku():
    assert guess_sku("PUBG 60 UC", CATALOG) == "pubg_uc_60"
    assert guess_sku("PUBG 325 UC", CATALOG) is None


def test_blood_strike_maps_to_gold_sku():
    assert guess_sku("Blood Strike 100 Gold", CATALOG) == "bs_gold_100"
    assert guess_sku("Blood Strike 80 Gold", CATALOG) is None


def test_mlbb_never_mapped_because_zone_required():
    assert guess_sku("MLBB RU 32 Diamonds", CATALOG) is None


def test_non_cis_diamonds_sku_is_ignored():
    catalog = [i for i in CATALOG if i["region"] != "CIS"]
    assert guess_sku("FF 110 Diamonds", catalog) is None


def test_vouchers_and_unknown_games_return_none():
    assert guess_sku("FF Ваучер ҳафтаи Сабук", CATALOG) is None
    assert guess_sku("Stars 100", CATALOG) is None
    assert guess_sku("", CATALOG) is None
