import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64DecodeError
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)
from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity


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
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
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
        normalized_occurred_from = self._normalize_time(occurred_from, "occurred_from")
        normalized_occurred_to = self._normalize_time(occurred_to, "occurred_to")
        if (
            normalized_occurred_from is not None
            and normalized_occurred_to is not None
            and normalized_occurred_from >= normalized_occurred_to
        ):
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "occurred_from must be earlier than occurred_to"
            )

        after_sequence = (
            self._decode_cursor(
                cursor,
                expected_from_state=normalized_from_state,
                expected_to_state=normalized_to_state,
                expected_occurred_from=normalized_occurred_from,
                expected_occurred_to=normalized_occurred_to,
            )
            if cursor is not None
            else None
        )

        if page_size is None and cursor is None:
            rows = self._store.get_history(
                execution_id,
                from_state=normalized_from_state,
                to_state=normalized_to_state,
                occurred_from=normalized_occurred_from,
                occurred_to=normalized_occurred_to,
            )
            return self._to_read_model(execution, rows)

        effective_page_size = (
            DEFAULT_HISTORY_PAGE_SIZE if page_size is None else page_size
        )
        self._validate_page_size(effective_page_size)

        rows = self._store.get_history(
            execution_id,
            after_sequence=after_sequence,
            limit=effective_page_size + 1,
            from_state=normalized_from_state,
            to_state=normalized_to_state,
            occurred_from=normalized_occurred_from,
            occurred_to=normalized_occurred_to,
        )
        has_more = len(rows) > effective_page_size
        page_rows = rows[:effective_page_size]

        next_cursor = (
            self._encode_cursor(
                page_rows[-1][0],
                from_state=normalized_from_state,
                to_state=normalized_to_state,
                occurred_from=normalized_occurred_from,
                occurred_to=normalized_occurred_to,
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
    def _normalize_state(value: str | None, parameter_name: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        valid = {state.value for state in ScheduledWorkflowExecutionState}
        if normalized not in valid:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                f"{parameter_name} must be a valid scheduled workflow execution state"
            )
        return normalized

    @staticmethod
    def _normalize_time(value: datetime | None, parameter_name: str) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                f"{parameter_name} must include a timezone"
            )
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_page_size(page_size: int) -> None:
        if page_size < 1 or page_size > MAX_HISTORY_PAGE_SIZE:
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                f"page_size must be between 1 and {MAX_HISTORY_PAGE_SIZE}"
            )

    @staticmethod
    def _encode_cursor(
        sequence: int,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> str:
        if from_state is None and to_state is None and occurred_from is None and occurred_to is None:
            payload = str(sequence)
        else:
            payload = json.dumps(
                {
                    "sequence": sequence,
                    "from_state": from_state,
                    "to_state": to_state,
                    "occurred_from": occurred_from.isoformat() if occurred_from else None,
                    "occurred_to": occurred_to.isoformat() if occurred_to else None,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        return urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(
        cursor: str,
        expected_from_state: str | None = None,
        expected_to_state: str | None = None,
        expected_occurred_from: datetime | None = None,
        expected_occurred_to: datetime | None = None,
    ) -> int:
        if not cursor.strip():
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor cannot be empty"
            )

        try:
            padding = "=" * (-len(cursor) % 4)
            decoded = urlsafe_b64decode(
                (cursor + padding).encode("ascii")
            ).decode("utf-8")
        except (Base64DecodeError, UnicodeDecodeError, ValueError):
            raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                "cursor must be a valid history continuation cursor"
            ) from None

        try:
            sequence = int(decoded)
        except ValueError:
            try:
                payload = json.loads(decoded)
            except json.JSONDecodeError:
                raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                    "cursor must be a valid history continuation cursor"
                ) from None

            if not isinstance(payload, dict):
                raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                    "cursor must be a valid history continuation cursor"
                )

            keys = set(payload)
            legacy_keys = {"from_state", "sequence", "to_state"}
            current_keys = legacy_keys | {"occurred_from", "occurred_to"}
            if keys != legacy_keys and keys != current_keys:
                raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                    "cursor must be a valid history continuation cursor"
                )

            if (
                payload["from_state"] != expected_from_state
                or payload["to_state"] != expected_to_state
                or (
                    keys == current_keys
                    and (
                        payload["occurred_from"]
                        != (expected_occurred_from.isoformat() if expected_occurred_from else None)
                        or payload["occurred_to"]
                        != (expected_occurred_to.isoformat() if expected_occurred_to else None)
                    )
                )
                or (
                    keys == legacy_keys
                    and (expected_occurred_from is not None or expected_occurred_to is not None)
                )
            ):
                raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                    "cursor does not match the requested history filters"
                )

            try:
                sequence = int(payload["sequence"])
            except (TypeError, ValueError):
                raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                    "cursor must be a valid history continuation cursor"
                ) from None
        else:
            if expected_from_state is not None or expected_to_state is not None or expected_occurred_from is not None or expected_occurred_to is not None:
                raise InvalidScheduledWorkflowExecutionHistoryQueryError(
                    "cursor does not match the requested history filters"
                )

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
