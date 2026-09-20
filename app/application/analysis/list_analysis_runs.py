import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.analysis.run_store import AnalysisRunStore
from app.application.security.identity import AuthenticatedIdentity
from app.application.security.identity import Permission
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class InvalidAnalysisRunListQueryError(ValueError):
    """Raised when analysis-run list input or continuation state is invalid."""


@dataclass(frozen=True)
class AnalysisRunListItem:
    run_id: UUID
    created_at: datetime
    state: ExecutionState


@dataclass(frozen=True)
class AnalysisRunListView:
    items: tuple[AnalysisRunListItem, ...]
    next_cursor: str | None


class ListAnalysisRuns:
    def __init__(self, run_store: AnalysisRunStore) -> None:
        self._run_store = run_store

    def execute(
        self,
        *,
        state: ExecutionState | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        identity: AuthenticatedIdentity | None = None,
    ) -> AnalysisRunListView:
        self._validate_page_size(page_size)
        after = self._decode_cursor(cursor, state, page_size) if cursor else None

        effective_identity = identity or AuthenticatedIdentity.operator()
        is_operator = Permission.OPERATOR in effective_identity.permissions
        owner_user_id = None if is_operator else effective_identity.user_id
        if owner_user_id is None and not is_operator:
            raise ValueError("Authenticated user identity is required")

        runs = self._run_store.list_runs(
            state=state,
            owner_user_id=owner_user_id,
            include_global=is_operator,
            before_created_at=after[0] if after else None,
            before_run_id=after[1] if after else None,
            limit=page_size + 1,
        )

        page = runs[:page_size]
        next_cursor = None
        if len(runs) > page_size:
            last = page[-1]
            next_cursor = self._encode_cursor(
                state=state,
                page_size=page_size,
                created_at=last.created_at,
                run_id=last.id,
            )

        return AnalysisRunListView(
            items=tuple(self._to_item(run) for run in page),
            next_cursor=next_cursor,
        )

    @staticmethod
    def _validate_page_size(page_size: int) -> None:
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise InvalidAnalysisRunListQueryError(
                f"page_size must be between 1 and {MAX_PAGE_SIZE}"
            )

    @staticmethod
    def _encode_cursor(
        *,
        state: ExecutionState | None,
        page_size: int,
        created_at: datetime,
        run_id: UUID,
    ) -> str:
        payload = json.dumps(
            {
                "state": state.value if state is not None else None,
                "page_size": page_size,
                "created_at": created_at.isoformat(),
                "run_id": str(run_id),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(
        cursor: str,
        state: ExecutionState | None,
        page_size: int,
    ) -> tuple[datetime, UUID]:
        try:
            padding = "=" * (-len(cursor) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
            )
            if not isinstance(payload, dict):
                raise ValueError
            expected_state = state.value if state is not None else None
            if (
                payload.get("state") != expected_state
                or payload.get("page_size") != page_size
                or not isinstance(payload.get("created_at"), str)
            ):
                raise ValueError
            return datetime.fromisoformat(payload["created_at"]), UUID(payload["run_id"])
        except (
            ValueError,
            KeyError,
            TypeError,
            binascii.Error,
            json.JSONDecodeError,
        ) as error:
            raise InvalidAnalysisRunListQueryError(
                "Invalid analysis-run cursor"
            ) from error

    @staticmethod
    def _to_item(run: AnalysisRun) -> AnalysisRunListItem:
        return AnalysisRunListItem(
            run_id=run.id,
            created_at=run.created_at,
            state=run.state,
        )
