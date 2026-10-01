from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4


class AcquisitionStatus(Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CONFLICTED = "conflicted"


@dataclass(frozen=True)
class AcquisitionRecord:
    acquisition_id: UUID
    provider: str
    source_symbol: str
    stock_id: UUID
    requested_from: date
    requested_to: date
    actual_from: date | None
    actual_to: date | None
    requested_at: datetime
    completed_at: datetime
    status: AcquisitionStatus
    row_count: int
    raw_artifact_hash: str | None = None
    error: str | None = None

    @classmethod
    def success(cls, **kwargs) -> "AcquisitionRecord":
        return cls(
            acquisition_id=uuid4(),
            status=AcquisitionStatus.SUCCEEDED,
            **kwargs,
        )

    @classmethod
    def failure(
        cls,
        *,
        provider: str,
        source_symbol: str,
        stock_id: UUID,
        requested_from: date,
        requested_to: date,
        requested_at: datetime,
        completed_at: datetime,
        error: str,
        row_count: int = 0,
        actual_from: date | None = None,
        actual_to: date | None = None,
    ) -> "AcquisitionRecord":
        return cls(
            acquisition_id=uuid4(),
            provider=provider,
            source_symbol=source_symbol,
            stock_id=stock_id,
            requested_from=requested_from,
            requested_to=requested_to,
            actual_from=actual_from,
            actual_to=actual_to,
            requested_at=requested_at,
            completed_at=completed_at,
            status=AcquisitionStatus.FAILED,
            row_count=row_count,
            error=error,
        )

    def conflicted(self, *, completed_at: datetime, error: str) -> "AcquisitionRecord":
        return AcquisitionRecord(
            acquisition_id=self.acquisition_id,
            provider=self.provider,
            source_symbol=self.source_symbol,
            stock_id=self.stock_id,
            requested_from=self.requested_from,
            requested_to=self.requested_to,
            actual_from=self.actual_from,
            actual_to=self.actual_to,
            requested_at=self.requested_at,
            completed_at=completed_at,
            status=AcquisitionStatus.CONFLICTED,
            row_count=self.row_count,
            raw_artifact_hash=self.raw_artifact_hash,
            error=error,
        )
