def test_poller_watches_unprefixed_fireloot_refs():
    """FireLoot order refs are short codes — the poller must not require a
    prefix, otherwise delivered orders stay PROCESSING forever."""
    from sqlalchemy.dialects import sqlite

    from main import _processing_orders_stmt

    stmt = _processing_orders_stmt().compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )
    sql = str(stmt)
    assert "FL-%" not in sql
    assert "mocktop_%" in sql
    assert "realtop_%" in sql
    assert "provider_order_id IS NOT NULL" in sql
    assert "PROCESSING" in sql
