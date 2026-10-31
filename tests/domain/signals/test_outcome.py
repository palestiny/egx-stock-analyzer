from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


def test_outcome_requires_valid_reproducibility_metadata():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    record = SignalOutcomeRecord(
        signal_id=uuid4(),
        symbol="COMI",
        outcome=SignalOutcome.TARGET_HIT,
        direction=SignalDirection.BUY,
        observed_at=now,
        entry_price=Decimal("100"),
        exit_price=Decimal("105"),
        realized_return=Decimal("0.05"),
        realized_r=Decimal("1"),
        invalidation=Decimal("95"),
        target_label="T1",
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=now,
    )
    assert record.realized_r == Decimal("1")


def test_outcome_rejects_zero_r():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="realized R"):
        SignalOutcomeRecord(
            signal_id=uuid4(), symbol="COMI", outcome=SignalOutcome.INVALIDATED,
            direction=SignalDirection.BUY,
            observed_at=now, entry_price=Decimal("100"), exit_price=Decimal("95"),
            realized_return=Decimal("-0.05"), realized_r=Decimal("0"),
            invalidation=Decimal("95"), target_label=None,
            strategy_id="breakout-trend", strategy_version="1.0", data_timestamp=now,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "entry_price",
        "exit_price",
        "invalidation",
        "realized_return",
        "realized_r",
    ),
)
@pytest.mark.parametrize(
    "invalid_value",
    (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")),
)
def test_outcome_rejects_non_finite_decimal_values(field_name, invalid_value):
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    valid = SignalOutcomeRecord(
        signal_id=uuid4(),
        symbol="COMI",
        outcome=SignalOutcome.INVALIDATED,
        direction=SignalDirection.BUY,
        observed_at=now,
        entry_price=Decimal("100"),
        exit_price=Decimal("95"),
        realized_return=Decimal("-0.05"),
        realized_r=Decimal("-1"),
        invalidation=Decimal("95"),
        target_label=None,
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=now,
    )
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        replace(valid, **{field_name: invalid_value})


@pytest.mark.parametrize("field_name", ("observed_at", "data_timestamp"))
def test_outcome_requires_timezone_aware_timestamps(field_name):
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    valid = SignalOutcomeRecord(
        signal_id=uuid4(),
        symbol="COMI",
        outcome=SignalOutcome.INVALIDATED,
        direction=SignalDirection.BUY,
        observed_at=now,
        entry_price=Decimal("100"),
        exit_price=Decimal("95"),
        realized_return=Decimal("-0.05"),
        realized_r=Decimal("-1"),
        invalidation=Decimal("95"),
        target_label=None,
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=now,
    )
    with pytest.raises(ValueError, match=f"{field_name} must be timezone-aware"):
        replace(valid, **{field_name: datetime(2026, 10, 7)})


def test_outcome_rejects_data_timestamp_after_observation():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    valid = SignalOutcomeRecord(
        signal_id=uuid4(),
        symbol="COMI",
        outcome=SignalOutcome.INVALIDATED,
        direction=SignalDirection.BUY,
        observed_at=now,
        entry_price=Decimal("100"),
        exit_price=Decimal("95"),
        realized_return=Decimal("-0.05"),
        realized_r=Decimal("-1"),
        invalidation=Decimal("95"),
        target_label=None,
        strategy_id="breakout-trend",
        strategy_version="1.0",
        data_timestamp=now,
    )
    with pytest.raises(ValueError, match="data timestamp cannot be later"):
        replace(valid, data_timestamp=datetime(2026, 10, 7, 13, tzinfo=timezone.utc))
