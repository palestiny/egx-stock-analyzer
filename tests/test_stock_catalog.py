from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def test_catalog_returns_stock_by_symbol():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = InMemoryStockCatalog([stock])

    result = catalog.get("egal")

    assert result is stock


def test_catalog_returns_none_for_unknown_symbol():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = InMemoryStockCatalog([stock])

    assert catalog.get("UNKNOWN") is None


def test_catalog_normalizes_symbol_on_lookup():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = InMemoryStockCatalog([stock])

    assert catalog.get("  egal  ") is stock


def test_catalog_returns_deterministic_normalized_symbols():
    stocks = [
        Stock.create("egal", "Egypt Aluminum"),
        Stock.create("IEEC", "Egyptian Electrical"),
    ]
    catalog = InMemoryStockCatalog(stocks)

    assert catalog.symbols() == ("EGAL", "IEEC")


def test_catalog_rejects_duplicate_normalized_symbols():
    stocks = [
        Stock.create("EGAL", "Egypt Aluminum"),
        Stock.create(" egal ", "Duplicate Egypt Aluminum"),
    ]

    try:
        InMemoryStockCatalog(stocks)
    except ValueError as error:
        assert "Duplicate stock symbol" in str(error)
    else:
        raise AssertionError("Expected duplicate stock symbol validation")
