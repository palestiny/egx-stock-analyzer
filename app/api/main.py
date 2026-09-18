import logging
from dataclasses import asdict
from datetime import date

from fastapi import FastAPI, HTTPException

from app.api.alert_candidate_response import AlertCandidateResponse
from app.api.analysis_report_response import AnalysisReportResponse
from app.api.analysis_response import AnalysisResultResponse
from app.application.analysis.get_analysis_result import GetAnalysisResult
from app.application.analysis.result_store import AnalysisResultStore
from app.application.analysis.run_stock_analysis_by_symbol import (
    RunStockAnalysisBySymbol,
    UnknownStockSymbolError,
)
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.application.reporting.get_analysis_report import GetAnalysisReport

logger = logging.getLogger(__name__)


def create_app(
    result_store: AnalysisResultStore,
    run_stock_analysis_by_symbol: RunStockAnalysisBySymbol | None = None,
    get_analysis_report: GetAnalysisReport | None = None,
    get_alert_candidate: GetAlertCandidate | None = None,
) -> FastAPI:
    app = FastAPI(title="EGX Stock Analyzer API")
    get_analysis_result = GetAnalysisResult(result_store)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/analysis/{symbol}")
    def get_analysis(symbol: str) -> dict[str, object]:
        result = get_analysis_result.execute(symbol)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis result not found for {symbol}",
            )

        response = AnalysisResultResponse.from_result(symbol, result)
        return asdict(response)

    @app.post("/api/v1/analysis/{symbol}")
    def run_analysis(symbol: str) -> dict[str, object]:
        if run_stock_analysis_by_symbol is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis execution is not configured",
            )

        try:
            run_stock_analysis_by_symbol.execute(symbol, date.today())
        except UnknownStockSymbolError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            logger.exception("Analysis execution failed for symbol %s", symbol, exc_info=error)
            raise HTTPException(
                status_code=500,
                detail="Analysis execution failed",
            ) from error

        result = get_analysis_result.execute(symbol)
        if result is None:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis result was not stored for {symbol}",
            )

        response = AnalysisResultResponse.from_result(symbol, result)
        return asdict(response)

    @app.get("/api/v1/reports/{symbol}")
    def get_report(symbol: str) -> dict[str, object]:
        if get_analysis_report is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis reporting is not configured",
            )

        report = get_analysis_report.execute(symbol)
        if report is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis report not found for {symbol}",
            )

        response = AnalysisReportResponse.from_report(report)
        return asdict(response)

    @app.get("/api/v1/alerts/{symbol}")
    def get_alert(symbol: str) -> dict[str, object]:
        if get_alert_candidate is None:
            raise HTTPException(
                status_code=503,
                detail="Alert reporting is not configured",
            )

        candidate = get_alert_candidate.execute(symbol)
        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail=f"Alert candidate not found for {symbol}",
            )

        response = AlertCandidateResponse.from_candidate(candidate)
        return asdict(response)

    return app
