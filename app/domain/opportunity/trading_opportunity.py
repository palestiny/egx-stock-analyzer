from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class OpportunityDirection(StrEnum):
    LONG = "long"


class OpportunityStatus(StrEnum):
    DRAFT = "draft"
    WATCHING = "watching"
    ACTIVE = "active"
    ENTRY_TRIGGERED = "entry_triggered"
    IN_PROGRESS = "in_progress"
    TARGET_PARTIAL = "target_partial"
    TARGET_REACHED = "target_reached"
    INVALIDATED = "invalidated"
    STOPPED_OUT = "stopped_out"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    DATA_UNRELIABLE = "data_unreliable"


TERMINAL_OPPORTUNITY_STATUSES = frozenset(
    {
        OpportunityStatus.TARGET_REACHED,
        OpportunityStatus.INVALIDATED,
        OpportunityStatus.STOPPED_OUT,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.CANCELLED,
    }
)

_ALLOWED_TRANSITIONS: dict[OpportunityStatus, frozenset[OpportunityStatus]] = {
    OpportunityStatus.DRAFT: frozenset(
        {OpportunityStatus.WATCHING, OpportunityStatus.CANCELLED, OpportunityStatus.DATA_UNRELIABLE}
    ),
    OpportunityStatus.WATCHING: frozenset(
        {OpportunityStatus.ACTIVE, OpportunityStatus.INVALIDATED, OpportunityStatus.EXPIRED,
         OpportunityStatus.CANCELLED, OpportunityStatus.DATA_UNRELIABLE}
    ),
    OpportunityStatus.ACTIVE: frozenset(
        {OpportunityStatus.ENTRY_TRIGGERED, OpportunityStatus.INVALIDATED, OpportunityStatus.EXPIRED,
         OpportunityStatus.CANCELLED, OpportunityStatus.DATA_UNRELIABLE}
    ),
    OpportunityStatus.ENTRY_TRIGGERED: frozenset(
        {OpportunityStatus.IN_PROGRESS, OpportunityStatus.TARGET_PARTIAL, OpportunityStatus.TARGET_REACHED,
         OpportunityStatus.STOPPED_OUT, OpportunityStatus.INVALIDATED, OpportunityStatus.DATA_UNRELIABLE}
    ),
    OpportunityStatus.IN_PROGRESS: frozenset(
        {OpportunityStatus.TARGET_PARTIAL, OpportunityStatus.TARGET_REACHED, OpportunityStatus.STOPPED_OUT,
         OpportunityStatus.INVALIDATED, OpportunityStatus.DATA_UNRELIABLE}
    ),
    OpportunityStatus.TARGET_PARTIAL: frozenset(
        {OpportunityStatus.IN_PROGRESS, OpportunityStatus.TARGET_REACHED, OpportunityStatus.STOPPED_OUT,
         OpportunityStatus.INVALIDATED, OpportunityStatus.DATA_UNRELIABLE}
    ),
    OpportunityStatus.DATA_UNRELIABLE: frozenset(
        {OpportunityStatus.WATCHING, OpportunityStatus.ACTIVE, OpportunityStatus.ENTRY_TRIGGERED,
         OpportunityStatus.IN_PROGRESS, OpportunityStatus.TARGET_PARTIAL, OpportunityStatus.TARGET_REACHED,
         OpportunityStatus.INVALIDATED, OpportunityStatus.STOPPED_OUT, OpportunityStatus.EXPIRED,
         OpportunityStatus.CANCELLED}
    ),
    OpportunityStatus.TARGET_REACHED: frozenset(),
    OpportunityStatus.INVALIDATED: frozenset(),
    OpportunityStatus.STOPPED_OUT: frozenset(),
    OpportunityStatus.EXPIRED: frozenset(),
    OpportunityStatus.CANCELLED: frozenset(),
}


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class OpportunityEvidence:
    evidence_type: str
    description: str
    observed_at: datetime
    source: str
    source_version: str

    def __post_init__(self) -> None:
        for field_name in ("evidence_type", "description", "source", "source_version"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} is required")
        _require_aware(self.observed_at, "observed_at")


@dataclass(frozen=True)
class OpportunityTarget:
    price: Decimal
    rationale: str

    def __post_init__(self) -> None:
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError("Target price must be finite and greater than zero")
        if not self.rationale.strip():
            raise ValueError("Target rationale is required")


@dataclass(frozen=True)
class OpportunityLifecycleEvent:
    event_id: UUID
    opportunity_id: UUID
    from_status: OpportunityStatus
    to_status: OpportunityStatus
    occurred_at: datetime
    reason: str
    actor: str
    evidence_version: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.occurred_at, "occurred_at")
        if not self.reason.strip():
            raise ValueError("Transition reason is required")
        if not self.actor.strip():
            raise ValueError("Transition actor is required")


@dataclass(frozen=True)
class TradingOpportunity:
    """Immutable snapshot of a proposed long setup; not proof of an executed trade."""

    opportunity_id: UUID
    symbol: str
    timeframe: str
    strategy_version: str
    created_at: datetime
    expires_at: datetime
    entry_low: Decimal
    entry_high: Decimal
    invalidation_price: Decimal
    targets: tuple[OpportunityTarget, ...]
    evidence: tuple[OpportunityEvidence, ...]
    status: OpportunityStatus = OpportunityStatus.DRAFT
    version: int = 1
    lifecycle_events: tuple[OpportunityLifecycleEvent, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        timeframe: str,
        strategy_version: str,
        created_at: datetime,
        expires_at: datetime,
        entry_low: Decimal,
        entry_high: Decimal,
        invalidation_price: Decimal,
        targets: tuple[OpportunityTarget, ...],
        evidence: tuple[OpportunityEvidence, ...],
    ) -> "TradingOpportunity":
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol is required")
        if not timeframe.strip():
            raise ValueError("timeframe is required")
        if not strategy_version.strip():
            raise ValueError("strategy_version is required")
        _require_aware(created_at, "created_at")
        _require_aware(expires_at, "expires_at")
        if expires_at <= created_at:
            raise ValueError("expires_at must be later than created_at")
        prices = (entry_low, entry_high, invalidation_price)
        if any(not price.is_finite() or price <= 0 for price in prices):
            raise ValueError("Entry and invalidation prices must be finite and greater than zero")
        if entry_low > entry_high:
            raise ValueError("entry_low must be less than or equal to entry_high")
        if invalidation_price >= entry_low:
            raise ValueError("Long opportunity invalidation price must be below the entry zone")
        normalized_targets = tuple(targets)
        if not normalized_targets:
            raise ValueError("At least one target is required")
        if any(target.price <= entry_high for target in normalized_targets):
            raise ValueError("Long opportunity targets must be above the entry zone")
        if tuple(sorted(target.price for target in normalized_targets)) != tuple(
            target.price for target in normalized_targets
        ):
            raise ValueError("Targets must be ordered from nearest to farthest")
        normalized_evidence = tuple(evidence)
        if not normalized_evidence:
            raise ValueError("At least one evidence item is required")
        return cls(
            opportunity_id=uuid4(),
            symbol=normalized_symbol,
            timeframe=timeframe.strip().lower(),
            strategy_version=strategy_version.strip(),
            created_at=created_at,
            expires_at=expires_at,
            entry_low=entry_low,
            entry_high=entry_high,
            invalidation_price=invalidation_price,
            targets=normalized_targets,
            evidence=normalized_evidence,
        )

    def transition_to(
        self,
        new_status: OpportunityStatus,
        *,
        occurred_at: datetime,
        reason: str,
        actor: str,
        evidence_version: str | None = None,
    ) -> "TradingOpportunity":
        _require_aware(occurred_at, "occurred_at")
        if occurred_at < self.created_at:
            raise ValueError("Transition cannot occur before opportunity creation")
        if new_status == self.status:
            raise ValueError("Transition must change the opportunity status")
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(
                f"Transition from {self.status.value} to {new_status.value} is not allowed"
            )
        event = OpportunityLifecycleEvent(
            event_id=uuid4(),
            opportunity_id=self.opportunity_id,
            from_status=self.status,
            to_status=new_status,
            occurred_at=occurred_at,
            reason=reason,
            actor=actor,
            evidence_version=evidence_version,
        )
        return replace(
            self,
            status=new_status,
            lifecycle_events=self.lifecycle_events + (event,),
        )
