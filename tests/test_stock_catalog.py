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


def test_catalog_symbols_preserve_constructor_order_and_normalize():
    stocks = [
        Stock.create("egal", "Egypt Aluminum"),
        Stock.create(" ieec ", "Egyptian Electrical"),
    ]
    catalog = InMemoryStockCatalog(stocks)

    assert catalog.symbols() == ("EGAL", "IEEC")


def test_catalog_symbols_are_stable_snapshots():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = InMemoryStockCatalog([stock])

    symbols = catalog.symbols()

    assert isinstance(symbols, tuple)
    assert symbols == ("EGAL",)
