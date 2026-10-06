from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.signals.model import Signal, SignalStatus


@dataclass(frozen=True)
class SignalMarketState:
    observed_at: datetime
    price: Decimal

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("observed price must be positive")


def transition_signal(signal: Signal, state: SignalMarketState) -> Signal:
    """Apply one deterministic market observation to an active signal.

    Lifecycle rules are intentionally conservative:
    - ACTIVE enters TRIGGERED when a target is reached.
    - ACTIVE becomes INVALIDATED when its invalidation is crossed.
    - Terminal states never move backwards.
    - If both a target and invalidation are crossed in one observation,
      invalidation wins because the observation cannot establish path order.
    """
    if signal.status is not SignalStatus.ACTIVE:
        return signal

    price = state.price
    if signal.direction.value == "BUY":
        invalidated = price <= signal.invalidation
        triggered = price >= min(target.price for target in signal.targets)
    else:
        invalidated = price >= signal.invalidation
        triggered = price <= max(target.price for target in signal.targets)

    status = SignalStatus.INVALIDATED if invalidated else SignalStatus.TRIGGERED if triggered else SignalStatus.ACTIVE

    return Signal(
        symbol=signal.symbol,
        direction=signal.direction,
        status=status,
        generated_at=signal.generated_at,
        timeframe=signal.timeframe,
        entry_zone=signal.entry_zone,
        invalidation=signal.invalidation,
        targets=signal.targets,
        confidence=signal.confidence,
        risk_score=signal.risk_score,
        evidence=signal.evidence,
        strategy_id=signal.strategy_id,
        strategy_version=signal.strategy_version,
        data_timestamp=state.observed_at,
    )
