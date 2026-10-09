from app.infrastructure.stocks.development_catalog import create_development_stock_catalog


def test_development_catalog_contains_egal():
    catalog = create_development_stock_catalog()

    stock = catalog.get("egal")

    assert stock is not None
    assert stock.symbol == "EGAL"
    assert stock.name == "Egypt Aluminum"


def test_development_catalog_returns_none_for_unknown_symbol():
    catalog = create_development_stock_catalog()

    assert catalog.get("UNKNOWN") is None



def test_development_catalog_contains_the_bounded_m61_cohort():
    catalog = create_development_stock_catalog()

    assert set(catalog.symbols()) == {
        "COMI",
        "EGAL",
        "SWDY",
        "ETEL",
        "EAST",
        "TMGH",
        "PHDC",
        "FWRY",
        "EFID",
        "HRHO",
    }


def test_development_stock_ids_are_stable_across_catalog_recreation():
    first = create_development_stock_catalog()
    second = create_development_stock_catalog()

    for symbol in first.symbols():
        assert first.get(symbol) is not None
        assert second.get(symbol) is not None
        assert first.get(symbol).id == second.get(symbol).id
