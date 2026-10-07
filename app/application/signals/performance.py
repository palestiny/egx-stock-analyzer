from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.signals.outcome import SignalOutcome, SignalOutcomeRecord


@dataclass(frozen=True)
class TrackRecordMetrics:
    sample_size: int
    target_hits: int
    invalidations: int
    win_rate: Decimal
    total_realized_r: Decimal
    average_realized_r: Decimal
    expectancy_r: Decimal
    max_loss_streak: int


class SignalTrackRecordAnalyzer:
    """Deterministic descriptive metrics over recorded terminal outcomes.

    These metrics summarize observed records only. They are not backtest
    statistics and make no claim about future or live strategy performance.
    """

    def summarize(
        self,
        outcomes: tuple[SignalOutcomeRecord, ...],
        *,
        strategy_id: str | None = None,
        strategy_version: str | None = None,
    ) -> TrackRecordMetrics:
        selected = tuple(
            outcome
            for outcome in outcomes
            if (strategy_id is None or outcome.strategy_id == strategy_id)
            and (strategy_version is None or outcome.strategy_version == strategy_version)
        )
        if not selected:
            return TrackRecordMetrics(
                sample_size=0,
                target_hits=0,
                invalidations=0,
                win_rate=Decimal("0"),
                total_realized_r=Decimal("0"),
                average_realized_r=Decimal("0"),
                expectancy_r=Decimal("0"),
                max_loss_streak=0,
            )

        target_hits = sum(o.outcome is SignalOutcome.TARGET_HIT for o in selected)
        invalidations = len(selected) - target_hits
        total_r = sum((o.realized_r for o in selected), Decimal("0"))
        win_rate = Decimal(target_hits) / Decimal(len(selected))
        average_r = total_r / Decimal(len(selected))

        # For a realized-outcome record, expectancy equals the arithmetic mean
        # of realized R. Keeping it explicit makes the metric contract clear.
        losses = tuple(o.realized_r for o in selected if o.realized_r < 0)
        wins = tuple(o.realized_r for o in selected if o.realized_r > 0)
        loss_probability = Decimal(len(losses)) / Decimal(len(selected))
        average_loss = (
            sum(losses, Decimal("0")) / Decimal(len(losses)) if losses else Decimal("0")
        )
        average_win = (
            sum(wins, Decimal("0")) / Decimal(len(wins)) if wins else Decimal("0")
        )
        expectancy = (
            (Decimal(len(wins)) / Decimal(len(selected))) * average_win
            + loss_probability * average_loss
        )

        max_streak = current_streak = 0
        for outcome in sorted(selected, key=lambda item: item.observed_at):
            if outcome.realized_r < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return TrackRecordMetrics(
            sample_size=len(selected),
            target_hits=target_hits,
            invalidations=invalidations,
            win_rate=win_rate,
            total_realized_r=total_r,
            average_realized_r=average_r,
            expectancy_r=expectancy,
            max_loss_streak=max_streak,
        )
