from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def create_development_stock_catalog() -> InMemoryStockCatalog:
    return InMemoryStockCatalog(
        [
            Stock.create("EGAL", "Egypt Aluminum"),
        ]
    )
