from uuid import NAMESPACE_URL, uuid5

from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


_DEVELOPMENT_STOCKS = (
    ("COMI", "Commercial International Bank"),
    ("EGAL", "Egypt Aluminium"),
    ("SWDY", "Elsewedy Electric"),
    ("ETEL", "Telecom Egypt"),
    ("EAST", "Eastern Company"),
    ("TMGH", "Talaat Moustafa Group"),
    ("PHDC", "Palm Hills Developments"),
    ("FWRY", "Fawry for Banking Technology and Electronic Payments"),
    ("EFID", "Edita Food Industries"),
    ("HRHO", "EFG Holding"),
)


def create_development_stock_catalog() -> InMemoryStockCatalog:
    """Create a stable development-only catalog for the bounded M61 cohort.

    IDs are deterministic seed identities, not a claim that they match any
    existing production database. Real dataset manifests must use the Stock
    IDs from the catalog/database that will actually consume them.
    """
    return InMemoryStockCatalog(
        [
            Stock.reconstitute(
                id=uuid5(
                    NAMESPACE_URL,
                    f"https://github.com/palestiny/egx-stock-analyzer/stocks/{symbol}",
                ),
                symbol=symbol,
                name=name,
            )
            for symbol, name in _DEVELOPMENT_STOCKS
        ]
    )
