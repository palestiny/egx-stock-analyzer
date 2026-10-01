from uuid import UUID

from app.infrastructure.stocks.m61_catalog import create_m61_stock_catalog


EXPECTED_IDS = {
    "COMI": UUID("e443c130-8f6d-50dc-b25b-45f495593138"),
    "EGAL": UUID("6829da04-8c00-52fa-ba40-982237633681"),
    "SWDY": UUID("d1f8d494-63db-51e8-9104-aa1743136035"),
    "ETEL": UUID("78ae054b-f16c-539d-802a-dd30d8a486b9"),
    "EAST": UUID("270950c5-edad-5525-a40c-f98f3bd844f1"),
    "TMGH": UUID("dbbc8dfc-ff34-50b3-8731-ff6664ca2f5d"),
    "PHDC": UUID("40aa14a8-589a-5cc3-b133-8e8585420f28"),
    "FWRY": UUID("258a239e-b9c7-5734-82c1-b1490cee6b9d"),
    "EFID": UUID("083b90a7-9817-5ab2-82e2-1ae6f504d2a5"),
    "HRHO": UUID("fac6aa86-a2b7-5de2-8526-2638cb84a790"),
}


def test_m61_catalog_has_stable_canonical_identity_for_cohort() -> None:
    catalog = create_m61_stock_catalog()

    assert catalog.symbols() == tuple(EXPECTED_IDS)

    for symbol, expected_id in EXPECTED_IDS.items():
        stock = catalog.get(symbol)
        assert stock is not None
        assert stock.id == expected_id


def test_m61_catalog_identity_is_reproducible_across_instances() -> None:
    first = create_m61_stock_catalog()
    second = create_m61_stock_catalog()

    for symbol in EXPECTED_IDS:
        assert first.get(symbol) is not None
        assert second.get(symbol) is not None
        assert first.get(symbol).id == second.get(symbol).id


def test_m61_catalog_rejects_unknown_symbols_by_returning_none() -> None:
    assert create_m61_stock_catalog().get("UNKNOWN") is None
