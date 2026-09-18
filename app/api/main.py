from dataclasses import asdict
from datetime import date

from fastapi import FastAPI, HTTPException

from app.api.analysis_response import AnalysisResultResponse
from app.application.analysis.get_analysis_result import GetAnalysisResult
from app.application.analysis.result_store import AnalysisResultStore
from app.application.analysis.run_stock_analysis_by_symbol import (
    RunStockAnalysisBySymbol,
    UnknownStockSymbolError,
)


def create_app(
    result_store: AnalysisResultStore,
    run_stock_analysis_by_symbol: RunStockAnalysisBySymbol | None = None,
) -> FastAPI:
    app = FastAPI(title="EGX Stock Analyzer API")
    get_analysis_result = GetAnalysisResult(result_store)

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
            raise HTTPException(status_code=500, detail=str(error)) from error

        result = get_analysis_result.execute(symbol)
        if result is None:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis result was not stored for {symbol}",
            )

        response = AnalysisResultResponse.from_result(symbol, result)
        return asdict(response)

    return app
