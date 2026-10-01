from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date

from fastapi import Depends, FastAPI, HTTPException

from app.api.analysis_history_response import AnalysisHistoryResponse
from app.api.analysis_report_response import AnalysisReportResponse
from app.api.analysis_response import AnalysisResultResponse
from app.api.authentication import ApiAuthentication
from app.application.analysis.get_analysis_result import GetAnalysisResult
from app.application.analysis.run_stock_analysis_by_symbol import (
    RunStockAnalysisBySymbol,
    UnknownStockSymbolError,
)
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.application.security.identity import AuthenticatedIdentity

logger = logging.getLogger(__name__)


def register_analysis_routes(
    app: FastAPI,
    *,
    api_authentication: ApiAuthentication,
    get_analysis_result: GetAnalysisResult,
    run_stock_analysis_by_symbol: RunStockAnalysisBySymbol | None,
    get_analysis_history: GetAnalysisHistory | None,
    get_analysis_report: GetAnalysisReport | None,
) -> None:
    @app.get("/api/v1/analysis/{symbol}")
    def get_analysis(
        symbol: str,
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
    ) -> dict[str, object]:
        result = get_analysis_result.execute(symbol, identity=identity)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Analysis result not found for {symbol}")
        return asdict(AnalysisResultResponse.from_result(symbol, result))

    @app.post("/api/v1/analysis/{symbol}")
    def run_analysis(
        symbol: str,
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
    ) -> dict[str, object]:
        if run_stock_analysis_by_symbol is None:
            raise HTTPException(status_code=503, detail="Analysis execution is not configured")
        try:
            run_stock_analysis_by_symbol.execute(symbol, date.today(), identity=identity)
        except UnknownStockSymbolError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            logger.exception("Analysis execution failed for symbol %s", symbol, exc_info=error)
            raise HTTPException(status_code=500, detail="Analysis execution failed") from error

        result = get_analysis_result.execute(symbol, identity=identity)
        if result is None:
            raise HTTPException(status_code=500, detail=f"Analysis result was not stored for {symbol}")
        return asdict(AnalysisResultResponse.from_result(symbol, result))

    @app.get("/api/v1/history/{symbol}")
    def get_history(
        symbol: str,
        from_date: date | None = None,
        to_date: date | None = None,
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
    ) -> dict[str, object]:
        if get_analysis_history is None:
            raise HTTPException(status_code=503, detail="Analysis history is not configured")
        try:
            items = get_analysis_history.execute(
                symbol, start_date=from_date, end_date=to_date, identity=identity
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if items is None:
            raise HTTPException(status_code=404, detail=f"Analysis history not found for {symbol}")
        return AnalysisHistoryResponse.from_items(symbol.strip().upper(), items).to_dict()

    @app.get("/api/v1/reports/{symbol}")
    def get_report(
        symbol: str,
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
    ) -> dict[str, object]:
        if get_analysis_report is None:
            raise HTTPException(status_code=503, detail="Analysis reporting is not configured")
        report = get_analysis_report.execute(symbol, identity=identity)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Analysis report not found for {symbol}")
        return asdict(AnalysisReportResponse.from_report(report))
