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
