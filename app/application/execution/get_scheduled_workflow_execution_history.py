import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64DecodeError
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionStore,
)
from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity
from app.application.execution.scheduled_workflow_execution import ScheduledWorkflowExecutionState


DEFAULT_HISTORY_PAGE_SIZE = 50
MAX_HISTORY_PAGE_SIZE = 100


class ScheduledWorkflowExecutionHistoryNotFoundError(ValueError):
    """Raised when a requested scheduled workflow execution does not exist."""


class InvalidScheduledWorkflowExecutionHistoryQueryError(ValueError):
    """Raised when history pagination or filter parameters are invalid."""


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
        from_state: str | None = None,
        to_state: str | None = None,
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

        normalized_from_state = self._normalize_state(from_state, "from_state")
        normalized_to_state = self._normalize_state(to_state, "to_state")
        after_sequence = (
            self._decode_cursor(
                cursor,
                from_state=normalized_from_state,
                to_state=normalized_to_state,
            )
            if cursor is not None
            else None
        )

        if page_size is None and cursor is None:
            rows = self._store.get_history(
                execution_id,
                from_state=normalized_from_state,
                to_state=normalized_to_state,
            )
            return self._to_read_model(execution, rows)

        effective_page_size = (
            DEFAULT_HISTORY_PAGE_SIZE if page_size is None else page_size
        )
        self._validate_page_size(effective_page_size)

        rows = self._store.get_history(
            execution_id,
            from_state=normalized_from_state,
            to_state=normalized_to_state,
            after_sequence=after_sequence,
            limit=effective_page_size + 1,
        )
        has_more = len(rows) > effective_page_size
        page_rows = rows[:effective_page_size]

        next_cursor = (
            self._encode_cursor(
                page_rows[-1][0],
                from_state=normalized_from_state,
                to_state=normalized_to_state,
            )
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
    def _normalize_state(state: str | None, parameter: str) -> str | None:
        if state is None:
            return None
        normalized = state.strip().lower()
        valid_states = {item.value for item in ScheduledWorkflowExecutionState}
        if normalized not in valid_states:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                f"{parameter} must be one of: {', '.join(sorted(valid_states))}"
            )
        return normalized

    @staticmethod
    def _encode_cursor(
        sequence: int,
        *,
        from_state: str | None,
        to_state: str | None,
    ) -> str:
        if from_state is None and to_state is None:
            payload = str(sequence)
        else:
            payload = json.dumps(
                {
                    "version": 1,
                    "sequence": sequence,
                    "from_state": from_state,
                    "to_state": to_state,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        return urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(
        cursor: str,
        *,
        from_state: str | None,
        to_state: str | None,
    ) -> int:
        if not cursor.strip():
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor cannot be empty"
            )
        try:
            padding = "=" * (-len(cursor) % 4)
            payload = urlsafe_b64decode((cursor + padding).encode("ascii")).decode("utf-8")
        except (Base64DecodeError, UnicodeDecodeError):
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor must be a valid history continuation cursor"
            ) from None

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            if from_state is None and to_state is None:
                try:
                    sequence = int(payload)
                except ValueError:
                    sequence = -1
            else:
                sequence = -1
            if sequence < 1:
                raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                    "cursor does not match the requested history filters"
                    if from_state is not None or to_state is not None
                    else "cursor must be a valid history continuation cursor"
                )
            return sequence

        if not isinstance(parsed, dict) or parsed.get("version") != 1:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor must be a valid history continuation cursor"
            )

        if parsed.get("from_state") != from_state or parsed.get("to_state") != to_state:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor does not match the requested history filters"
            )

        sequence = parsed.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
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
