from app.domain.alerts.model import (
    AlertEvidenceSnapshot,
    AlertSignalSnapshot,
    AlertTargetSnapshot,
)
from app.domain.signals.model import Signal


def snapshot_signal(signal: Signal) -> AlertSignalSnapshot:
    """Capture the immutable, user-facing signal fields at event creation time."""
    return AlertSignalSnapshot(
        direction=signal.direction.value,
        status=signal.status.value,
        timeframe=signal.timeframe,
        entry_lower=signal.entry_zone.lower,
        entry_upper=signal.entry_zone.upper,
        invalidation=signal.invalidation,
        targets=tuple(
            AlertTargetSnapshot(price=target.price, label=target.label)
            for target in signal.targets
        ),
        evidence=tuple(
            AlertEvidenceSnapshot(kind=item.kind, description=item.description)
            for item in signal.evidence
        ),
        strategy_id=signal.strategy_id,
        strategy_version=signal.strategy_version,
        generated_at=signal.generated_at,
        data_timestamp=signal.data_timestamp,
    )
