from uuid import UUID

from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


# Stable identities for the bounded M61 validation cohort.
# These UUIDs are dataset identities, not generated per process.
M61_STOCKS = (
    (UUID("e443c130-8f6d-50dc-b25b-45f495593138"), "COMI", "Commercial International Bank"),
    (UUID("6829da04-8c00-52fa-ba40-982237633681"), "EGAL", "Egypt Aluminum"),
    (UUID("d1f8d494-63db-51e8-9104-aa1743136035"), "SWDY", "Elsewedy Electric"),
    (UUID("78ae054b-f16c-539d-802a-dd30d8a486b9"), "ETEL", "Telecom Egypt"),
    (UUID("270950c5-edad-5525-a40c-f98f3bd844f1"), "EAST", "Eastern Company"),
    (UUID("dbbc8dfc-ff34-50b3-8731-ff6664ca2f5d"), "TMGH", "Talaat Moustafa Group"),
    (UUID("40aa14a8-589a-5cc3-b133-8e8585420f28"), "PHDC", "Palm Hills Developments"),
    (UUID("258a239e-b9c7-5734-82c1-b1490cee6b9d"), "FWRY", "Fawry for Banking Technology and Electronic Payment"),
    (UUID("083b90a7-9817-5ab2-82e2-1ae6f504d2a5"), "EFID", "Edita Food Industries"),
    (UUID("fac6aa86-a2b7-5de2-8526-2638cb84a790"), "HRHO", "EFG Holding"),
)


def create_m61_stock_catalog() -> InMemoryStockCatalog:
    return InMemoryStockCatalog(
        [
            Stock.reconstitute(id=stock_id, symbol=symbol, name=name)
            for stock_id, symbol, name in M61_STOCKS
        ]
    )
