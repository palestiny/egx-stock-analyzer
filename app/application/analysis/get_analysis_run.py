import base64
import binascii
import json
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.application.analysis.result_store import AnalysisResultRecord, AnalysisResultStore
from app.application.analysis.run_store import AnalysisRunStore
from app.application.security.authorization import OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.domain.analysis_run import AnalysisRunOutcomeState
from app.domain.execution import ExecutionState


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class AnalysisRunNotFoundError(LookupError):
    """Raised when the requested analysis run does not exist."""


class InvalidAnalysisRunQueryError(ValueError):
    """Raised when analysis-run pagination input is invalid."""


@dataclass(frozen=True)
class AnalysisRunSnapshotView:
    snapshot_id: UUID
    symbol: str
    analysis_date: date | None


@dataclass(frozen=True)
class AnalysisRunOutcomeView:
    symbol: str
    state: str
    stock_id: UUID | None
    failure_code: str | None
    failure_detail: str | None


@dataclass(frozen=True)
class AnalysisRunView:
    run_id: UUID
    created_at: datetime
    state: ExecutionState
    outcomes_available: bool
    outcomes: tuple[AnalysisRunOutcomeView, ...]
    snapshots: tuple[AnalysisRunSnapshotView, ...]
    next_cursor: str | None


class GetAnalysisRun:
    def __init__(
        self,
        run_store: AnalysisRunStore,
        result_store: AnalysisResultStore,
    ) -> None:
        self._run_store = run_store
        self._result_store = result_store
        self._ownership_authorizer = OwnershipAuthorizer()

    def execute(
        self,
        run_id: UUID,
        page_size: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        identity: AuthenticatedIdentity | None = None,
    ) -> AnalysisRunView:
        self._validate_page_size(page_size)
        run = self._run_store.get(run_id)
        if run is None:
            raise AnalysisRunNotFoundError(
                f"Analysis run not found: {run_id}"
            )

        effective_identity = identity or AuthenticatedIdentity.operator()
        try:
            self._ownership_authorizer.require_owner_or_operator(
                effective_identity,
                run.owner_user_id,
            )
        except Exception as error:
            raise AnalysisRunNotFoundError(
                f"Analysis run not found: {run_id}"
            ) from error

        after = self._decode_cursor(cursor, run_id, page_size) if cursor else None
        owner_user_id = (
            None
            if Permission.OPERATOR in effective_identity.permissions
            else effective_identity.user_id
        )
        records = sorted(
            self._result_store.get_history_by_analysis_run(
                run_id,
                owner_user_id=owner_user_id,
            ),
            key=lambda record: (record.symbol or "", str(record.snapshot_id)),
        )

        if after is not None:
            records = [
                record
                for record in records
                if self._is_after(record, after)
            ]

        page_records = records[:page_size]
        next_cursor = None
        if len(records) > page_size:
            last = page_records[-1]
            next_cursor = self._encode_cursor(
                run_id,
                page_size,
                last.symbol or "",
                last.snapshot_id,
            )

        return AnalysisRunView(
            run_id=run.id,
            created_at=run.created_at,
            state=run.state,
            outcomes_available=run.outcomes_available,
            outcomes=tuple(
                AnalysisRunOutcomeView(
                    symbol=outcome.symbol,
                    state=outcome.state.value,
                    stock_id=outcome.stock_id,
                    failure_code=outcome.failure_code,
                    failure_detail=outcome.failure_detail,
                )
                for outcome in sorted(run.outcomes, key=lambda item: item.symbol)
            ),
            snapshots=tuple(
                self._to_snapshot_view(record)
                for record in page_records
            ),
            next_cursor=next_cursor,
        )

    @staticmethod
    def _validate_page_size(page_size: int) -> None:
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise InvalidAnalysisRunQueryError(
                f"page_size must be between 1 and {MAX_PAGE_SIZE}"
            )

    @staticmethod
    def _encode_cursor(
        run_id: UUID,
        page_size: int,
        symbol: str,
        snapshot_id: UUID,
    ) -> str:
        payload = json.dumps(
            {
                "run_id": str(run_id),
                "page_size": page_size,
                "symbol": symbol,
                "snapshot_id": str(snapshot_id),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(
        cursor: str,
        run_id: UUID,
        page_size: int,
    ) -> tuple[str, UUID]:
        try:
            padding = "=" * (-len(cursor) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
            )
            if not isinstance(payload, dict):
                raise ValueError
            if (
                payload.get("run_id") != str(run_id)
                or payload.get("page_size") != page_size
                or not isinstance(payload.get("symbol"), str)
            ):
                raise ValueError
            return payload["symbol"], UUID(payload["snapshot_id"])
        except (
            ValueError,
            KeyError,
            TypeError,
            binascii.Error,
            json.JSONDecodeError,
        ) as error:
            raise InvalidAnalysisRunQueryError(
                "Invalid analysis-run cursor"
            ) from error

    @staticmethod
    def _is_after(
        record: AnalysisResultRecord,
        after: tuple[str, UUID],
    ) -> bool:
        symbol = record.symbol or ""
        return (symbol, str(record.snapshot_id)) > (after[0], str(after[1]))

    @staticmethod
    def _to_snapshot_view(record: AnalysisResultRecord) -> AnalysisRunSnapshotView:
        return AnalysisRunSnapshotView(
            snapshot_id=record.snapshot_id,
            symbol=record.symbol or "",
            analysis_date=record.analysis_date,
        )
