import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.scheduled_workflow_execution_history_response import ScheduledWorkflowExecutionHistoryResponse
from app.api.scheduled_workflow_execution_response import (
    ScheduledWorkflowExecutionResponse,
    ScheduledWorkflowExecutionsResponse,
)
from app.api.scheduled_workflow_history_response import ScheduledWorkflowHistoryResponse
from app.application.clock import egx_today
from app.application.execution.get_scheduled_workflow_execution_history import (
    GetScheduledWorkflowExecutionHistory,
    InvalidScheduledWorkflowExecutionHistoryQueryError,
    ScheduledWorkflowExecutionHistoryNotFoundError,
)
from app.application.execution.get_scheduled_workflow_executions import GetScheduledWorkflowExecutions
from app.application.execution.get_scheduled_workflow_history import (
    GetScheduledWorkflowHistory,
    InvalidScheduledWorkflowHistoryQueryError,
)
from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
    WorkflowExecutionNotFoundError,
    WorkflowExecutionNotRecoverableError,
)
from app.application.security.authentication import Authenticator
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity

logger = logging.getLogger(__name__)


def create_scheduled_workflow_router(
    *,
    get_scheduled_workflow_executions: GetScheduledWorkflowExecutions | None,
    get_scheduled_workflow_execution_history: GetScheduledWorkflowExecutionHistory | None,
    get_scheduled_workflow_history: GetScheduledWorkflowHistory | None,
    recover_durable_scheduled_workflow: RecoverDurableScheduledWorkflow | None,
    authenticator: Authenticator | None,
    require_authenticated: Callable[..., AuthenticatedIdentity],
) -> APIRouter:
    """Register scheduled-workflow read/recovery routes behind app authentication."""
    router = APIRouter()

    @router.get("/api/v1/workflows/executions")
    def list_scheduled_workflow_executions(
        occurrence_id: str | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_scheduled_workflow_executions is None:
            raise HTTPException(
                status_code=503,
                detail="Scheduled workflow execution reporting is not configured",
            )

        if occurrence_id is not None and not occurrence_id.strip():
            raise HTTPException(status_code=422, detail="occurrence_id cannot be empty")

        try:
            if authenticator is None:
                items = get_scheduled_workflow_executions.execute(
                    occurrence_id=occurrence_id,
                )
            else:
                items = get_scheduled_workflow_executions.execute(
                    occurrence_id=occurrence_id,
                    identity=identity,
                )
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception("Scheduled workflow execution history failed", exc_info=error)
            raise HTTPException(
                status_code=500,
                detail="Scheduled workflow execution reporting failed",
            ) from error

        if occurrence_id is not None and not items:
            raise HTTPException(
                status_code=404,
                detail=f"Scheduled workflow execution not found for {occurrence_id}",
            )

        response = ScheduledWorkflowExecutionsResponse.from_items(items)
        return asdict(response)

    @router.get("/api/v1/workflows/history")
    def get_scheduled_workflow_history_route(
        page_size: int | None = None,
        cursor: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_scheduled_workflow_history is None:
            raise HTTPException(status_code=503, detail="Scheduled workflow history is not configured")

        try:
            history = get_scheduled_workflow_history.execute(
                identity,
                page_size=page_size,
                cursor=cursor,
                from_state=from_state,
                to_state=to_state,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            )
        except InvalidScheduledWorkflowHistoryQueryError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception("Scheduled workflow cross-execution history failed", exc_info=error)
            raise HTTPException(status_code=500, detail="Scheduled workflow history failed") from error

        response = ScheduledWorkflowHistoryResponse.from_read_model(history)
        return asdict(response)
    @router.get("/api/v1/workflows/executions/{execution_id}/history")
    def get_scheduled_workflow_execution_history_route(
        execution_id: UUID,
        page_size: int | None = None,
        cursor: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_scheduled_workflow_execution_history is None:
            raise HTTPException(
                status_code=503,
                detail="Scheduled workflow execution history is not configured",
            )

        try:
            history = get_scheduled_workflow_execution_history.execute(
                execution_id,
                identity,
                page_size=page_size,
                cursor=cursor,
                from_state=from_state,
                to_state=to_state,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            )
        except ScheduledWorkflowExecutionHistoryNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidScheduledWorkflowExecutionHistoryQueryError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception(
                "Scheduled workflow execution history failed for %s",
                execution_id,
                exc_info=error,
            )
            raise HTTPException(
                status_code=500,
                detail="Scheduled workflow execution history failed",
            ) from error

        response = ScheduledWorkflowExecutionHistoryResponse.from_read_model(history)
        return asdict(response)

    @router.post("/api/v1/workflows/executions/{execution_id}/recover")
    def recover_scheduled_workflow_execution(
        execution_id: UUID,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if recover_durable_scheduled_workflow is None:
            raise HTTPException(
                status_code=503,
                detail="Scheduled workflow recovery is not configured",
            )

        try:
            if authenticator is None:
                execution = recover_durable_scheduled_workflow.execute(
                    execution_id,
                    egx_today(),
                )
            else:
                execution = recover_durable_scheduled_workflow.execute(
                    execution_id,
                    egx_today(),
                    identity,
                )
        except WorkflowExecutionNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except WorkflowExecutionNotRecoverableError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception(
                "Scheduled workflow recovery failed for %s",
                execution_id,
                exc_info=error,
            )
            raise HTTPException(
                status_code=500,
                detail="Scheduled workflow recovery failed",
            ) from error

        response = ScheduledWorkflowExecutionResponse.from_execution(execution)
        return asdict(response)


    return router
