import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64DecodeError
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)
from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import UserStatus
from app.application.security.identity import Permission


DEFAULT_CROSS_EXECUTION_HISTORY_PAGE_SIZE = 50
MAX_CROSS_EXECUTION_HISTORY_PAGE_SIZE = 100


class InvalidScheduledWorkflowHistoryQueryError(ValueError):
    """Raised when a cross-execution history query is invalid."""


@dataclass(frozen=True)
class ScheduledWorkflowHistoryItem:
    execution_id: UUID
    occurrence_id: str
    sequence: int
    from_state: str | None
    to_state: str
    occurred_at: datetime
    reason: str | None


@dataclass(frozen=True)
class ScheduledWorkflowHistoryReadModel:
    items: tuple[ScheduledWorkflowHistoryItem, ...]
    has_more: bool
    next_cursor: str | None


class GetScheduledWorkflowHistory:
    def __init__(self, store: ScheduledWorkflowExecutionStore) -> None:
        self._store = store
        self._authorizer = OwnershipAuthorizer()

    def execute(
        self,
        identity: AuthenticatedIdentity,
        page_size: int | None = None,
        cursor: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> ScheduledWorkflowHistoryReadModel:
        self._authorizer.require_authenticated(identity)

        normalized_from_state = self._normalize_state(from_state, "from_state")
        normalized_to_state = self._normalize_state(to_state, "to_state")
        normalized_occurred_from = self._normalize_time(occurred_from, "occurred_from")
        normalized_occurred_to = self._normalize_time(occurred_to, "occurred_to")
        if (
            normalized_occurred_from is not None
            and normalized_occurred_to is not None
            and normalized_occurred_from >= normalized_occurred_to
        ):
            raise InvalidScheduledWorkflowHistoryQueryError(
                "occurred_from must be earlier than occurred_to"
            )

        if page_size is None:
            effective_page_size = DEFAULT_CROSS_EXECUTION_HISTORY_PAGE_SIZE
        else:
            effective_page_size = page_size
        self._validate_page_size(effective_page_size)

        cursor_key = self._decode_cursor(
            cursor,
            from_state=normalized_from_state,
            to_state=normalized_to_state,
            occurred_from=normalized_occurred_from,
            occurred_to=normalized_occurred_to,
        ) if cursor is not None else None

        is_operator_scope = Permission.OPERATOR in identity.permissions
        owner_user_id = None if is_operator_scope else identity.user_id

        rows = self._store.get_cross_execution_history(
            owner_user_id=owner_user_id,
            global_only=is_operator_scope,
            after_cursor=cursor_key,
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
                page_rows[-1][4],
                page_rows[-1][0],
                page_rows[-1][1],
                from_state=normalized_from_state,
                to_state=normalized_to_state,
                occurred_from=normalized_occurred_from,
                occurred_to=normalized_occurred_to,
            )
            if has_more and page_rows
            else None
        )

        return ScheduledWorkflowHistoryReadModel(
            items=tuple(
                ScheduledWorkflowHistoryItem(
                    execution_id=execution_id,
                    occurrence_id=occurrence_id,
                    sequence=sequence,
                    from_state=from_state,
                    to_state=to_state,
                    occurred_at=occurred_at,
                    reason=reason,
                )
                for execution_id, occurrence_id, sequence, from_state, to_state, occurred_at, reason in page_rows
            ),
            has_more=has_more,
            next_cursor=next_cursor,
        )

    @staticmethod
    def _normalize_state(value: str | None, parameter_name: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {state.value for state in ScheduledWorkflowExecutionState}:
            raise InvalidScheduledWorkflowHistoryQueryError(
                f"{parameter_name} must be a valid scheduled workflow execution state"
            )
        return normalized

    @staticmethod
    def _normalize_time(value: datetime | None, parameter_name: str) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise InvalidScheduledWorkflowHistoryQueryError(
                f"{parameter_name} must include a timezone"
            )
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_page_size(page_size: int) -> None:
        if page_size < 1 or page_size > MAX_CROSS_EXECUTION_HISTORY_PAGE_SIZE:
            raise InvalidScheduledWorkflowHistoryQueryError(
                f"page_size must be between 1 and {MAX_CROSS_EXECUTION_HISTORY_PAGE_SIZE}"
            )

    @staticmethod
    def _encode_cursor(
        occurred_at: datetime,
        execution_id: UUID,
        sequence: int,
        *,
        from_state: str | None,
        to_state: str | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
    ) -> str:
        payload = json.dumps(
            {
                "occurred_at": occurred_at.astimezone(timezone.utc).isoformat(),
                "execution_id": str(execution_id),
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
        *,
        from_state: str | None,
        to_state: str | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
    ) -> tuple[datetime, UUID, int]:
        if not cursor.strip():
            raise InvalidScheduledWorkflowHistoryQueryError("cursor cannot be empty")
        try:
            padding = "=" * (-len(cursor) % 4)
            payload = json.loads(
                urlsafe_b64decode((cursor + padding).encode("ascii")).decode("utf-8")
            )
        except (Base64DecodeError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            raise InvalidScheduledWorkflowHistoryQueryError(
                "cursor must be a valid history continuation cursor"
            ) from None

        required = {
            "occurred_at",
            "execution_id",
            "sequence",
            "from_state",
            "to_state",
            "occurred_from",
            "occurred_to",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise InvalidScheduledWorkflowHistoryQueryError(
                "cursor must be a valid history continuation cursor"
            )

        if (
            payload["from_state"] != from_state
            or payload["to_state"] != to_state
            or payload["occurred_from"] != (occurred_from.isoformat() if occurred_from else None)
            or payload["occurred_to"] != (occurred_to.isoformat() if occurred_to else None)
        ):
            raise InvalidScheduledWorkflowHistoryQueryError(
                "cursor does not match the requested history filters"
            )

        try:
            occurred_at = datetime.fromisoformat(payload["occurred_at"]).astimezone(timezone.utc)
            execution_id = UUID(payload["execution_id"])
            sequence = int(payload["sequence"])
        except (TypeError, ValueError):
            raise InvalidScheduledWorkflowHistoryQueryError(
                "cursor must be a valid history continuation cursor"
            ) from None

        if sequence < 1:
            raise InvalidScheduledWorkflowHistoryQueryError(
                "cursor sequence must be positive"
            )
        return occurred_at, execution_id, sequence
