from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


def test_outcome_requires_valid_reproducibility_metadata():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    record = SignalOutcomeRecord(
        signal_id=uuid4(),
        symbol="COMI",
        outcome=SignalOutcome.TARGET_HIT,
        observed_at=now,
        entry_price=Decimal("100"),
        exit_price=Decimal("105"),
        realized_return=Decimal("0.05"),
        realized_r=Decimal("1"),
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
            observed_at=now, entry_price=Decimal("100"), exit_price=Decimal("95"),
            realized_return=Decimal("-0.05"), realized_r=Decimal("0"),
            strategy_id="breakout-trend", strategy_version="1.0", data_timestamp=now,
        )
