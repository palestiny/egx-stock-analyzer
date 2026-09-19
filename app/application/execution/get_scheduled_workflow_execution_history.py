from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionStore,
)
from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity


DEFAULT_HISTORY_PAGE_SIZE = 50
MAX_HISTORY_PAGE_SIZE = 100


class ScheduledWorkflowExecutionHistoryNotFoundError(ValueError):
    """Raised when a requested scheduled workflow execution does not exist."""


class InvalidScheduledWorkflowExecutionHistoryQueryError(ValueError):
    """Raised when history pagination parameters are invalid."""


@dataclass(frozen=True)
class ScheduledWorkflowExecutionHistoryItem:
    sequence: int
    from_state: str | None
    to_state: str
    occurred_at: datetime
    reason: str | None


@dataclass(frozen=True)
class ScheduledWorkflowExecutionHistoryReadModel:
    execution_id: UUID
    occurrence_id: str
    history: tuple[ScheduledWorkflowExecutionHistoryItem, ...]
    has_more: bool = False
    next_cursor: str | None = None


class GetScheduledWorkflowExecutionHistory:
    def __init__(self, store: ScheduledWorkflowExecutionStore) -> None:
        self._store = store
        self._authorizer = OwnershipAuthorizer()

    def execute(
        self,
        execution_id: UUID,
        identity: AuthenticatedIdentity,
        page_size: int | None = None,
        cursor: str | None = None,
    ) -> ScheduledWorkflowExecutionHistoryReadModel:
        execution = self._store.get(execution_id)
        if execution is None:
            raise ScheduledWorkflowExecutionHistoryNotFoundError(
                f"Unknown scheduled workflow execution: {execution_id}"
            )

        self._authorizer.require_owner_or_global(
            identity,
            execution.owner_user_id,
        )

        after_sequence = self._decode_cursor(cursor) if cursor is not None else None

        if page_size is None and cursor is None:
            rows = self._store.get_history(execution_id)
            return self._to_read_model(execution, rows)

        effective_page_size = (
            DEFAULT_HISTORY_PAGE_SIZE if page_size is None else page_size
        )
        self._validate_page_size(effective_page_size)

        rows = self._store.get_history(
            execution_id,
            after_sequence=after_sequence,
            limit=effective_page_size + 1,
        )
        has_more = len(rows) > effective_page_size
        page_rows = rows[:effective_page_size]

        next_cursor = (
            self._encode_cursor(page_rows[-1][0])
            if has_more and page_rows
            else None
        )

        return self._to_read_model(
            execution,
            page_rows,
            has_more=has_more,
            next_cursor=next_cursor,
        )

    @staticmethod
    def _validate_page_size(page_size: int) -> None:
        if page_size < 1 or page_size > MAX_HISTORY_PAGE_SIZE:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                f"page_size must be between 1 and {MAX_HISTORY_PAGE_SIZE}"
            )

    @staticmethod
    def _encode_cursor(sequence: int) -> str:
        return urlsafe_b64encode(str(sequence).encode("ascii")).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> int:
        if not cursor.strip():
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor cannot be empty"
            )
        try:
            padding = "=" * (-len(cursor) % 4)
            sequence = int(
                urlsafe_b64decode((cursor + padding).encode("ascii")).decode("ascii")
            )
        except (ValueError, UnicodeDecodeError):
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor must be a valid history continuation cursor"
            ) from None

        if sequence < 1:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor sequence must be positive"
            )
        return sequence

    @staticmethod
    def _to_read_model(
        execution: ScheduledWorkflowExecution,
        rows: tuple[tuple[int, str | None, str, datetime, str | None], ...],
        has_more: bool = False,
        next_cursor: str | None = None,
    ) -> ScheduledWorkflowExecutionHistoryReadModel:
        history = tuple(
            ScheduledWorkflowExecutionHistoryItem(
                sequence=sequence,
                from_state=from_state,
                to_state=to_state,
                occurred_at=occurred_at,
                reason=reason,
            )
            for sequence, from_state, to_state, occurred_at, reason in rows
        )
        return ScheduledWorkflowExecutionHistoryReadModel(
            execution_id=execution.id,
            occurrence_id=execution.occurrence_id,
            history=history,
            has_more=has_more,
            next_cursor=next_cursor,
        )
