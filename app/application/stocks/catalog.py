from typing import Protocol, runtime_checkable

from app.domain.stocks.stock import Stock


@runtime_checkable
class StockCatalog(Protocol):
    def get(self, symbol: str) -> Stock | None:
        ...

    def symbols(self) -> tuple[str, ...]:
        ...

    def symbols(self) -> tuple[str, ...]:
        ...


class InMemoryStockCatalog:
    def __init__(self, stocks: list[Stock]) -> None:
        normalized: dict[str, Stock] = {}

        for stock in stocks:
            if stock.symbol in normalized:
                raise ValueError(f"Duplicate stock symbol in catalog: {stock.symbol}")
            normalized[stock.symbol] = stock

        self._stocks = normalized

    def get(self, symbol: str) -> Stock | None:
        return self._stocks.get(symbol.strip().upper())

    def symbols(self) -> tuple[str, ...]:
        return tuple(self._stocks.keys())

    def symbols(self) -> tuple[str, ...]:
        return tuple(self._stocks)
