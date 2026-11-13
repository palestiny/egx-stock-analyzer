from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.signals.model import Signal, SignalStatus


@dataclass(frozen=True)
class SignalMarketState:
    observed_at: datetime
    price: Decimal
    data_timestamp: datetime

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.data_timestamp.tzinfo is None or self.data_timestamp.utcoffset() is None:
            raise ValueError("data_timestamp must be timezone-aware")
        if self.data_timestamp > self.observed_at:
            raise ValueError("data_timestamp cannot be later than observed_at")
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError("observed price must be finite and positive")


@dataclass(frozen=True)
class CompletedDailyBarObservation:
    """Provider-attested, immutable identity for one completed daily OHLC candle."""

    symbol: str
    provider: str
    timeframe: str
    candle_at: datetime
    observed_at: datetime
    revision: str
    source_reference: str
    finality_attestation: str
    is_final: bool
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        for name in ("symbol", "provider", "timeframe", "revision", "source_reference", "finality_attestation"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} is required")
        if self.timeframe.strip().upper() != "DAILY":
            raise ValueError("lifecycle observation requires DAILY timeframe")
        if not isinstance(self.is_final, bool):
            raise ValueError("is_final must be an explicit boolean attestation")
        if not self.is_final:
            raise ValueError("daily candle must be provider-attested final")
        for name, value in (
            ("candle_at", self.candle_at),
            ("observed_at", self.observed_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.candle_at > self.observed_at:
            raise ValueError("candle timestamp cannot be later than observation")
        for name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if not value.is_finite() or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.high < max(self.open, self.close):
            raise ValueError("high cannot be below open or close")
        if self.low > min(self.open, self.close):
            raise ValueError("low cannot be above open or close")
        if self.low > self.high:
            raise ValueError("low cannot exceed high")

    @property
    def identity(self) -> tuple[str, str, str, datetime, str]:
        return (
            self.provider.strip().casefold(),
            self.symbol.strip().upper(),
            self.timeframe.strip().upper(),
            self.candle_at,
            self.revision.strip(),
        )


def transition_signal(signal: Signal, state: SignalMarketState) -> Signal:
    """Legacy single-price transition retained for compatibility only.

    New lifecycle processing must use transition_signal_from_completed_daily_bar.
    """
    if state.observed_at < signal.generated_at:
        raise ValueError("market observation cannot precede signal generation")
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
        data_timestamp=signal.data_timestamp,
    )


def transition_signal_from_completed_daily_bar(
    signal: Signal,
    bar: CompletedDailyBarObservation,
) -> Signal:
    """Apply DEC-138 completed-candle crossing semantics to an active signal."""
    if bar.symbol.strip().upper() != signal.symbol.strip().upper():
        raise ValueError("daily candle symbol does not match signal")
    if bar.candle_at < signal.generated_at:
        raise ValueError("daily candle cannot precede signal generation")
    if signal.status is not SignalStatus.ACTIVE:
        return signal

    if signal.direction.value == "BUY":
        invalidated = bar.low <= signal.invalidation
        target_touched = any(bar.high >= target.price for target in signal.targets)
    else:
        invalidated = bar.high >= signal.invalidation
        target_touched = any(bar.low <= target.price for target in signal.targets)

    status = (
        SignalStatus.INVALIDATED
        if invalidated
        else SignalStatus.TRIGGERED
        if target_touched
        else SignalStatus.ACTIVE
    )
    if status is signal.status:
        return signal
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
        data_timestamp=signal.data_timestamp,
    )
