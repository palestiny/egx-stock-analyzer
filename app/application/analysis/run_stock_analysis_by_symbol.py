from datetime import date
from uuid import UUID

from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.stocks.catalog import StockCatalog
from app.application.security.identity import AuthenticatedIdentity, Permission


class UnknownStockSymbolError(ValueError):
    """Raised when a requested symbol is not present in the stock catalog."""


class RunStockAnalysisBySymbol:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        run_stock_analysis: RunStockAnalysis,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._run_stock_analysis = run_stock_analysis

    def execute(
        self,
        symbol: str,
        as_of: date,
        identity: AuthenticatedIdentity | None = None,
        owner_user_id: UUID | None = None,
    ) -> None:
        stock = self._stock_catalog.get(symbol)
        if stock is None:
            raise UnknownStockSymbolError(f"Unknown stock symbol: {symbol}")
        effective_owner = owner_user_id
        if identity is not None and Permission.OPERATOR not in identity.permissions:
            effective_owner = identity.user_id
        if effective_owner is None:
            self._run_stock_analysis.execute(stock, as_of)
        else:
            self._run_stock_analysis.execute(
                stock,
                as_of,
                owner_user_id=effective_owner,
            )
