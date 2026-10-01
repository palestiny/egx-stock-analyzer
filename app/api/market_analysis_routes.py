from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import Depends, FastAPI, HTTPException

from app.api.authentication import ApiAuthentication
from app.api.market_analysis_execution_response import MarketAnalysisExecutionResponse
from app.api.market_opportunity_view_response import MarketOpportunityViewResponse
from app.application.analysis.get_market_opportunity_ranking import GetMarketOpportunityRanking
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.security.identity import AuthenticatedIdentity, Permission


def register_market_analysis_routes(
    app: FastAPI,
    *,
    api_authentication: ApiAuthentication,
    run_configured_market_analysis: RunConfiguredMarketAnalysis | None,
    get_market_opportunity_ranking: GetMarketOpportunityRanking | None,
) -> None:
    @app.post("/api/v1/market-analysis")
    def run_market_analysis(
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
    ) -> dict[str, object]:
        if run_configured_market_analysis is None:
            raise HTTPException(status_code=503, detail="Market analysis execution is not configured")
        try:
            execution = run_configured_market_analysis.execute(
                date.today(),
                owner_user_id=identity.user_id if Permission.OPERATOR not in identity.permissions else None,
            )
        except Exception as error:
            raise HTTPException(status_code=500, detail="Market-wide analysis execution failed") from error
        response_execution = getattr(execution, "execution", execution)
        response = MarketAnalysisExecutionResponse.from_execution(response_execution)
        return asdict(response)

    @app.get("/api/v1/opportunities")
    def get_opportunities(
        symbols: str = "",
        _identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
    ) -> dict[str, object]:
        if get_market_opportunity_ranking is None:
            raise HTTPException(status_code=503, detail="Market opportunity reporting is not configured")
        requested_symbols = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
        try:
            view = get_market_opportunity_ranking.execute(requested_symbols)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        response = MarketOpportunityViewResponse.from_view(view)
        return asdict(response)
