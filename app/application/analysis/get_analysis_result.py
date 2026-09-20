from uuid import UUID

from app.application.analysis.result_store import AnalysisResultStore
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.analysis.stock_analysis import StockAnalysisResult


class GetAnalysisResult:
    def __init__(self, result_store: AnalysisResultStore) -> None:
        self._result_store = result_store

    def execute(
        self,
        symbol: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> StockAnalysisResult | None:
        if identity is None or Permission.OPERATOR in identity.permissions:
            return self._result_store.get(symbol)

        if identity.user_id is None:
            return None

        return self._result_store.get(symbol, owner_user_id=identity.user_id)
