from typing import Protocol, runtime_checkable

from app.domain.stocks.stock import Stock


@runtime_checkable
class StockCatalog(Protocol):
    def get(self, symbol: str) -> Stock | None:
        ...


class InMemoryStockCatalog:
    def __init__(self, stocks: list[Stock]) -> None:
        self._stocks = {stock.symbol: stock for stock in stocks}

    def get(self, symbol: str) -> Stock | None:
        return self._stocks.get(symbol.strip().upper())
