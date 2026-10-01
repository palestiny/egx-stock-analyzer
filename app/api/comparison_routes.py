from __future__ import annotations

from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException

from app.api.analysis_comparison_response import AnalysisComparisonResponse
from app.api.analysis_snapshot_performance_response import AnalysisSnapshotPerformanceResponse
from app.api.authentication import ApiAuthentication
from app.application.reporting.calculate_snapshot_performance import (
    AnalysisSnapshotPerformanceNotFoundError,
    CalculateSnapshotPerformance,
    InvalidSnapshotPerformanceError,
)
from app.application.reporting.compare_analysis_snapshots import (
    AnalysisSnapshotNotFoundError,
    CompareAnalysisSnapshots,
    InvalidSnapshotComparisonError,
)
from app.application.security.identity import AuthenticatedIdentity


def register_comparison_routes(
    app: FastAPI,
    *,
    api_authentication: ApiAuthentication,
    compare_analysis_snapshots: CompareAnalysisSnapshots | None,
    calculate_snapshot_performance: CalculateSnapshotPerformance | None,
) -> None:
    @app.get("/api/v1/comparisons/{symbol}")
    def compare_analysis(
        symbol: str,
        before: UUID,
        after: UUID,
        _identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
    ) -> dict[str, object]:
        if compare_analysis_snapshots is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis comparison is not configured",
            )

        try:
            comparison = compare_analysis_snapshots.execute(
                symbol,
                before_snapshot_id=before,
                after_snapshot_id=after,
            )
        except AnalysisSnapshotNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidSnapshotComparisonError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return AnalysisComparisonResponse.from_comparison(comparison).to_dict()

    @app.get("/api/v1/performance/{symbol}")
    def calculate_performance(
        symbol: str,
        before: UUID,
        after: UUID,
        _identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
    ) -> dict[str, object]:
        if calculate_snapshot_performance is None:
            raise HTTPException(status_code=503, detail="Historical performance is not configured")
        try:
            performance = calculate_snapshot_performance.execute(
                symbol, before_snapshot_id=before, after_snapshot_id=after
            )
        except AnalysisSnapshotPerformanceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidSnapshotPerformanceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return AnalysisSnapshotPerformanceResponse.from_performance(performance).to_dict()

