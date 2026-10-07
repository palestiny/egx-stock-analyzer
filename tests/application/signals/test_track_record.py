from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.signals.track_record import InMemoryTrackRecordStore
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


def make_outcome():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    return SignalOutcomeRecord(
        signal_id=uuid4(), symbol="COMI", outcome=SignalOutcome.TARGET_HIT,
        observed_at=now, entry_price=Decimal("100"), exit_price=Decimal("105"),
        realized_return=Decimal("0.05"), realized_r=Decimal("1"),
        strategy_id="breakout-trend", strategy_version="1.0", data_timestamp=now,
    )


def test_store_is_idempotent_by_signal_id():
    store = InMemoryTrackRecordStore()
    outcome = make_outcome()
    store.record(outcome)
    with pytest.raises(ValueError, match="already recorded"):
        store.record(outcome)
    assert store.get(outcome.signal_id) == outcome
