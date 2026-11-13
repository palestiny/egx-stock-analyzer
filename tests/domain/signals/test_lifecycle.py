from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.signals.lifecycle import (
    CompletedDailyBarObservation,
    SignalMarketState,
    transition_signal,
    transition_signal_from_completed_daily_bar,
)
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
        targets=(
            (Target(Decimal("91"), "T1"), Target(Decimal("87"), "T2"))
            if direction is SignalDirection.SELL
            else (Target(Decimal("109"), "T1"), Target(Decimal("113"), "T2"))
        ),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "test"),),
        strategy_id="test",
        strategy_version="1.0",
        data_timestamp=datetime(2026, 10, 3, tzinfo=timezone.utc),
    )


def state(price: str) -> SignalMarketState:
    observed_at = datetime(2026, 10, 4, tzinfo=timezone.utc)
    return SignalMarketState(observed_at, Decimal(price), observed_at)


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


def test_market_state_requires_timezone_aware_observation_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SignalMarketState(
            datetime(2026, 10, 4), Decimal("100"),
            datetime(2026, 10, 4, tzinfo=timezone.utc),
        )


def test_market_state_rejects_non_finite_or_non_positive_prices() -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        SignalMarketState(
            datetime(2026, 10, 4, tzinfo=timezone.utc), Decimal("NaN"),
            datetime(2026, 10, 4, tzinfo=timezone.utc),
        )
    with pytest.raises(ValueError, match="finite and positive"):
        SignalMarketState(
            datetime(2026, 10, 4, tzinfo=timezone.utc), Decimal("0"),
            datetime(2026, 10, 4, tzinfo=timezone.utc),
        )


def test_market_observation_cannot_precede_signal_generation() -> None:
    earlier_at = datetime(2026, 10, 2, tzinfo=timezone.utc)
    earlier = SignalMarketState(earlier_at, Decimal("100"), earlier_at)
    with pytest.raises(ValueError, match="cannot precede"):
        transition_signal(make_signal(), earlier)

 

def test_market_state_requires_timezone_aware_data_timestamp() -> None:
    observed_at = datetime(2026, 10, 4, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="data_timestamp must be timezone-aware"):
        SignalMarketState(observed_at, Decimal("100"), datetime(2026, 10, 4))


def test_market_state_rejects_data_timestamp_after_observation() -> None:
    observed_at = datetime(2026, 10, 4, tzinfo=timezone.utc)
    future_data = datetime(2026, 10, 4, 0, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="cannot be later"):
        SignalMarketState(observed_at, Decimal("100"), future_data)


def completed_bar(*, high="110", low="98", direction_symbol="COMI", final=True):
    return CompletedDailyBarObservation(
        symbol=direction_symbol,
        provider="verified-test-provider",
        timeframe="DAILY",
        candle_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
        observed_at=datetime(2026, 10, 4, 16, tzinfo=timezone.utc),
        revision="r1",
        source_reference="https://provider.example/daily/COMI/2026-10-04",
        finality_attestation="provider-final-bar-v1",
        is_final=final,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("100"),
    )


def test_completed_daily_bar_triggers_when_high_touches_target():
    result = transition_signal_from_completed_daily_bar(
        make_signal(), completed_bar(high="109", low="98")
    )
    assert result.status is SignalStatus.TRIGGERED


def test_completed_daily_bar_invalidates_when_low_touches_stop():
    result = transition_signal_from_completed_daily_bar(
        make_signal(), completed_bar(high="105", low="95")
    )
    assert result.status is SignalStatus.INVALIDATED


def test_completed_daily_bar_invalidation_wins_when_both_levels_touched():
    result = transition_signal_from_completed_daily_bar(
        make_signal(), completed_bar(high="110", low="94")
    )
    assert result.status is SignalStatus.INVALIDATED


def test_completed_daily_bar_sell_direction_uses_low_for_target_and_high_for_stop():
    signal = make_signal(SignalDirection.SELL)
    result = transition_signal_from_completed_daily_bar(
        signal, completed_bar(high="104", low="90")
    )
    assert result.status is SignalStatus.TRIGGERED


def test_completed_daily_bar_requires_provider_finality_and_valid_ohlc():
    with pytest.raises(ValueError, match="provider-attested final"):
        completed_bar(final=False)
    with pytest.raises(ValueError, match="high cannot be below"):
        CompletedDailyBarObservation(
            symbol="COMI",
            provider="provider",
            timeframe="DAILY",
            candle_at=datetime(2026, 10, 4, tzinfo=timezone.utc),
            observed_at=datetime(2026, 10, 4, 16, tzinfo=timezone.utc),
            revision="r1",
            source_reference="https://provider.example/daily/COMI/2026-10-04",
            finality_attestation="provider-final-bar-v1",
            is_final=True,
            open=Decimal("100"),
            high=Decimal("99"),
            low=Decimal("98"),
            close=Decimal("101"),
        )


def test_completed_daily_bar_identity_is_stable_and_normalized():
    first = completed_bar()
    second = CompletedDailyBarObservation(
        symbol=" comi ",
        provider="VERIFIED-TEST-PROVIDER",
        timeframe="daily",
        candle_at=first.candle_at,
        observed_at=first.observed_at,
        revision="r1",
        source_reference="https://provider.example/daily/COMI/2026-10-04",
        finality_attestation="provider-final-bar-v1",
        is_final=True,
        open=first.open,
        high=first.high,
        low=first.low,
        close=first.close,
    )
    assert first.identity == second.identity


def test_completed_daily_bar_rejects_wrong_symbol_and_pre_generation_candle():
    with pytest.raises(ValueError, match="does not match"):
        transition_signal_from_completed_daily_bar(
            make_signal(), completed_bar(direction_symbol="ABUK")
        )
    earlier = CompletedDailyBarObservation(
        symbol="COMI",
        provider="provider",
        timeframe="DAILY",
        candle_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        observed_at=datetime(2026, 10, 4, 16, tzinfo=timezone.utc),
        revision="r1",
        source_reference="https://provider.example/daily/COMI/2026-10-02",
        finality_attestation="provider-final-bar-v1",
        is_final=True,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("98"),
        close=Decimal("102"),
    )
    with pytest.raises(ValueError, match="precede signal generation"):
        transition_signal_from_completed_daily_bar(make_signal(), earlier)
