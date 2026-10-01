from __future__ import annotations

from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException

from app.api.analysis_run_response import AnalysisRunResponse
from app.api.analysis_run_list_response import AnalysisRunListResponse
from app.api.authentication import ApiAuthentication
from app.application.analysis.delete_analysis_run import AnalysisLifecycleNotFoundError, DeleteAnalysisRun
from app.application.analysis.delete_analysis_snapshot import DeleteAnalysisSnapshot
from app.application.analysis.get_analysis_run import AnalysisRunNotFoundError, GetAnalysisRun, InvalidAnalysisRunQueryError
from app.application.analysis.list_analysis_runs import InvalidAnalysisRunListQueryError, ListAnalysisRuns
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity
from app.domain.execution import ExecutionState


def register_analysis_lifecycle_routes(app: FastAPI, *, api_authentication: ApiAuthentication,
    get_analysis_run: GetAnalysisRun | None, list_analysis_runs: ListAnalysisRuns | None,
    delete_analysis_run: DeleteAnalysisRun | None, delete_analysis_snapshot: DeleteAnalysisSnapshot | None) -> None:
    @app.delete("/api/v1/analysis-runs/{run_id}")
    def delete_analysis_run_route(run_id: UUID, identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated)) -> dict[str, object]:
        if delete_analysis_run is None:
            raise HTTPException(status_code=503, detail="Analysis lifecycle is not configured")
        try: result = delete_analysis_run.execute(run_id, identity)
        except AnalysisLifecycleNotFoundError as error: raise HTTPException(status_code=404, detail="Analysis run not found") from error
        except AuthorizationError as error: raise HTTPException(status_code=403, detail="Forbidden") from error
        except ValueError as error: raise HTTPException(status_code=409, detail=str(error)) from error
        return {"run_id": str(run_id), "deleted": result.deleted}

    @app.delete("/api/v1/analysis-snapshots/{snapshot_id}")
    def delete_analysis_snapshot_route(snapshot_id: UUID, identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated)) -> dict[str, object]:
        if delete_analysis_snapshot is None:
            raise HTTPException(status_code=503, detail="Analysis lifecycle is not configured")
        try: result = delete_analysis_snapshot.execute(snapshot_id, identity)
        except AuthorizationError as error: raise HTTPException(status_code=403, detail="Forbidden") from error
        except ValueError as error: raise HTTPException(status_code=409, detail=str(error)) from error
        if not result.deleted: raise HTTPException(status_code=404, detail="Analysis snapshot not found")
        return {"snapshot_id": str(snapshot_id), "deleted": True}

    @app.get("/api/v1/analysis-runs")
    def list_analysis_runs_route(state: str | None = None, page_size: int = 50, cursor: str | None = None,
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated)) -> dict[str, object]:
        if list_analysis_runs is None: raise HTTPException(status_code=503, detail="Analysis run history is not configured")
        requested_state = None
        if state is not None:
            try: requested_state = ExecutionState(state)
            except ValueError as error: raise HTTPException(status_code=400, detail="Invalid analysis run state") from error
        try: view = list_analysis_runs.execute(state=requested_state, page_size=page_size, cursor=cursor, identity=identity)
        except InvalidAnalysisRunListQueryError as error: raise HTTPException(status_code=400, detail=str(error)) from error
        return AnalysisRunListResponse.from_view(view).to_dict()

    @app.get("/api/v1/analysis-runs/{run_id}")
    def get_analysis_run_route(run_id: UUID, page_size: int = 50, cursor: str | None = None,
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated)) -> dict[str, object]:
        if get_analysis_run is None: raise HTTPException(status_code=503, detail="Analysis run history is not configured")
        try: view = get_analysis_run.execute(run_id, page_size=page_size, cursor=cursor, identity=identity)
        except AnalysisRunNotFoundError as error: raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidAnalysisRunQueryError as error: raise HTTPException(status_code=400, detail=str(error)) from error
        return AnalysisRunResponse.from_view(view).to_dict()
