from datetime import date, datetime, timezone
import hashlib
import json
from typing import Protocol
from uuid import UUID

from app.application.execution.run_configured_market_analysis_with_automatic_alert_delivery import (
    ConfiguredMarketAnalysisDeliveryResult,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)
from app.application.security.authorization import OwnershipAuthorizer
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    ScheduledWorkflowExecutionIdempotencyConflictError,
)
from app.application.security.identity import AuthenticatedIdentity, Permission


class WorkflowClock(Protocol):
    def now(self) -> datetime:
        ...


class UtcWorkflowClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class RunDurableScheduledWorkflow:
    def __init__(
        self,
        scheduled_operation,
        store: ScheduledWorkflowExecutionStore,
        clock: WorkflowClock | None = None,
    ) -> None:
        self._scheduled_operation = scheduled_operation
        self._store = store
        self._clock = clock or UtcWorkflowClock()
        self._ownership_authorizer = OwnershipAuthorizer()

    def execute(
        self,
        occurrence_id: str,
        as_of: date,
        identity: AuthenticatedIdentity | None = None,
    ) -> ScheduledWorkflowExecution:
        owner_user_id: UUID | None = None
        if identity is not None and Permission.OPERATOR not in identity.permissions:
            self._ownership_authorizer.require_authenticated(identity)
            owner_user_id = identity.user_id

        normalized_occurrence = occurrence_id.strip()
        request_fingerprint = self._request_fingerprint(
            normalized_occurrence,
            as_of,
            owner_user_id,
        )
        existing = self._store.get_by_occurrence(normalized_occurrence)
        if existing is not None:
            self._authorize_existing_execution(existing, identity)

        try:
            execution = self._store.create_or_get(
                normalized_occurrence,
                self._clock.now(),
                owner_user_id,
                request_fingerprint,
            )
        except ScheduledWorkflowExecutionIdempotencyConflictError:
            raced = self._store.get_by_occurrence(normalized_occurrence)
            if raced is not None:
                self._authorize_existing_execution(raced, identity)
            raise

        if execution.state is not ScheduledWorkflowExecutionState.CREATED:
            self._authorize_existing_execution(execution, identity)
            return execution

        started = self._store.start_if_created(
            execution.id,
            self._clock.now(),
        )
        if started is None:
            existing = self._store.get(execution.id)
            if existing is None:
                raise ValueError(
                    f"Scheduled workflow execution disappeared: {execution.id}"
                )
            self._authorize_existing_execution(existing, identity)
            return existing

        return self._run(started, as_of)

    def recover(
        self,
        execution_id,
        as_of: date,
        identity: AuthenticatedIdentity | None = None,
    ) -> ScheduledWorkflowExecution:
        execution = self._store.get(execution_id)
        if execution is None:
            raise ValueError(f"Unknown scheduled workflow execution: {execution_id}")

        if identity is not None:
            self._authorize_existing_execution(execution, identity)

        if execution.state is not ScheduledWorkflowExecutionState.INTERRUPTED:
            raise ValueError(
                "Scheduled workflow execution is not interrupted: "
                f"{execution.state.value}"
            )

        execution = execution.start_recovery(self._clock.now())
        return self._run(execution, as_of)

    def _authorize_existing_execution(
        self,
        execution: ScheduledWorkflowExecution,
        identity: AuthenticatedIdentity | None,
    ) -> None:
        if identity is None:
            return
        if execution.owner_user_id is None:
            if Permission.OPERATOR in identity.permissions:
                return
            raise PermissionError("Resource is system-owned")
        self._ownership_authorizer.require_owner(identity, execution.owner_user_id)

    @staticmethod
    def _request_fingerprint(
        occurrence_id: str,
        as_of: date,
        owner_user_id: UUID | None,
    ) -> str:
        payload = {
            "occurrence_id": occurrence_id,
            "as_of": as_of.isoformat(),
            "owner_user_id": str(owner_user_id) if owner_user_id is not None else None,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _run(
        self,
        execution: ScheduledWorkflowExecution,
        as_of: date,
    ) -> ScheduledWorkflowExecution:
        try:
            result: ConfiguredMarketAnalysisDeliveryResult = (
                self._scheduled_operation.execute(as_of)
            )
        except Exception:
            failed = execution.fail(self._clock.now())
            self._store.save(failed)
            raise

        delivery_state = (
            result.delivery_result.state.value
            if result.delivery_result is not None
            else None
        )
        execution = execution.with_outcomes(
            analysis_state=result.analysis_execution.state.value,
            delivery_state=delivery_state,
            now=self._clock.now(),
        )
        self._store.save(execution)

        terminal_state = self._terminal_state(result)
        execution = getattr(execution, terminal_state)(self._clock.now())
        self._store.save(execution)
        return execution

    @staticmethod
    def _terminal_state(
        result: ConfiguredMarketAnalysisDeliveryResult,
    ) -> str:
        if result.analysis_execution.state.value == "failed":
            return "fail"

        if (
            result.analysis_execution.state.value == "completed_with_errors"
            or (
                result.delivery_result is not None
                and result.delivery_result.state.value == "completed_with_errors"
            )
            or (
                result.delivery_result is not None
                and result.delivery_result.state.value == "failed"
            )
        ):
            return "complete_with_errors"

        return "complete"
