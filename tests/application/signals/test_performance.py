from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.application.signals.performance import SignalTrackRecordAnalyzer
from app.domain.signals.model import SignalDirection
from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


def outcome(r: str, result: SignalOutcome, day: int, strategy="breakout-trend"):
    observed = datetime(2026, 10, day, tzinfo=timezone.utc)
    return SignalOutcomeRecord(
        signal_id=uuid4(),
        symbol="COMI",
        outcome=result,
        direction=SignalDirection.BUY,
        observed_at=observed,
        entry_price=Decimal("100"),
        exit_price=Decimal("110") if result is SignalOutcome.TARGET_HIT else Decimal("95"),
        realized_return=Decimal(r) / Decimal("10"),
        realized_r=Decimal(r),
        invalidation=Decimal("95"),
        target_label="T1" if result is SignalOutcome.TARGET_HIT else None,
        strategy_id=strategy,
        strategy_version="1.0",
        data_timestamp=observed,
    )


def test_summarize_calculates_core_metrics_and_loss_streak():
    records = (
        outcome("2", SignalOutcome.TARGET_HIT, 1),
        outcome("-1", SignalOutcome.INVALIDATED, 2),
        outcome("-1", SignalOutcome.INVALIDATED, 3),
        outcome("3", SignalOutcome.TARGET_HIT, 4),
    )

    metrics = SignalTrackRecordAnalyzer().summarize(records)

    assert metrics.sample_size == 4
    assert metrics.target_hits == 2
    assert metrics.invalidations == 2
    assert metrics.win_rate == Decimal("0.5")
    assert metrics.total_realized_r == Decimal("3")
    assert metrics.average_realized_r == Decimal("0.75")
    assert metrics.expectancy_r == Decimal("0.75")
    assert metrics.max_loss_streak == 2


def test_summarize_can_filter_strategy_identity():
    records = (
        outcome("2", SignalOutcome.TARGET_HIT, 1, "A"),
        outcome("-1", SignalOutcome.INVALIDATED, 2, "B"),
    )

    metrics = SignalTrackRecordAnalyzer().summarize(records, strategy_id="A")

    assert metrics.sample_size == 1
    assert metrics.total_realized_r == Decimal("2")
    assert metrics.win_rate == Decimal("1")


def test_empty_summary_is_zeroed():
    metrics = SignalTrackRecordAnalyzer().summarize(())

    assert metrics.sample_size == 0
    assert metrics.win_rate == Decimal("0")
    assert metrics.expectancy_r == Decimal("0")
    assert metrics.max_loss_streak == 0
