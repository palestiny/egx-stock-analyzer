from fastapi import FastAPI

from app.application.analysis.get_analysis_result import GetAnalysisResult
from app.application.analysis.result_store import AnalysisResultStore


def create_app(result_store: AnalysisResultStore) -> FastAPI:
    app = FastAPI(title="EGX Stock Analyzer API")
    get_analysis_result = GetAnalysisResult(result_store)

    @app.get("/api/v1/analysis/{symbol}")
    def get_analysis(symbol: str) -> dict[str, str]:
        result = get_analysis_result.execute(symbol)

        if result is None:
            return {"symbol": symbol, "status": "not_found"}

        return {"symbol": symbol, "status": "available"}

    return app
