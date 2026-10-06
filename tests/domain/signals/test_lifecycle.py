from datetime import datetime, timezone
from decimal import Decimal

from app.domain.signals.lifecycle import SignalMarketState, transition_signal
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)


def make_signal(direction: SignalDirection = SignalDirection.BUY) -> Signal:
    return Signal(
        symbol="COMI",
        direction=direction,
        status=SignalStatus.ACTIVE,
        generated_at=datetime(2026, 10, 3, tzinfo=timezone.utc),
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95") if direction is SignalDirection.BUY else Decimal("105"),
        targets=(Target(Decimal("109"), "T1"), Target(Decimal("113"), "T2")),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "test"),),
        strategy_id="test",
        strategy_version="1.0",
        data_timestamp=datetime(2026, 10, 3, tzinfo=timezone.utc),
    )


def state(price: str) -> SignalMarketState:
    return SignalMarketState(datetime(2026, 10, 4, tzinfo=timezone.utc), Decimal(price))


def test_buy_signal_triggers_at_target():
    result = transition_signal(make_signal(), state("109"))
    assert result.status is SignalStatus.TRIGGERED


def test_buy_signal_invalidates_at_invalidation():
    result = transition_signal(make_signal(), state("95"))
    assert result.status is SignalStatus.INVALIDATED


def test_invalidation_wins_when_single_observation_crosses_both():
    result = transition_signal(make_signal(), state("94"))
    assert result.status is SignalStatus.INVALIDATED


def test_terminal_signal_does_not_move_back_to_active():
    signal = make_signal()
    triggered = Signal(
        **{**signal.__dict__, "status": SignalStatus.TRIGGERED}
    )
    result = transition_signal(triggered, state("100"))
    assert result.status is SignalStatus.TRIGGERED
