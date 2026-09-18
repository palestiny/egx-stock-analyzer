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
