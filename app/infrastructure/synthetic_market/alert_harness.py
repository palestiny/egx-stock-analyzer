from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid5

from app.domain.alerts.model import AlertEvent, AlertEventType
from app.domain.market_intelligence.stress import StressLevel
from app.domain.reporting.alerts import AlertCandidate, AlertGenerator

from .generator import SyntheticDataset
from .opportunity_harness import SyntheticOpportunityReport
from .stress_harness import SyntheticStressReport


@dataclass(frozen=True)
class SyntheticAlertReport:
    scenario_name: str
    seed: int
    candidates: tuple[AlertCandidate, ...]
    events: tuple[AlertEvent, ...]


class SyntheticAlertHarness:
    """Composes existing alert contracts over synthetic opportunity/stress outputs.

    This validates alert plumbing only. It does not imply notification delivery
    or real-market predictive validity.
    """

    NAMESPACE = UUID("f4c1a2f6-3e13-4a0b-a0a2-4e58f4a6f4e1")

    def run(
        self,
        dataset: SyntheticDataset,
        opportunity: SyntheticOpportunityReport,
        stress: SyntheticStressReport,
    ) -> SyntheticAlertReport:
        candidates: list[AlertCandidate] = []
        events: list[AlertEvent] = []

        opportunity_by_stock = {item.stock_id: item for item in opportunity.snapshots}
        stress_by_stock = {item.stock_id: item for item in stress.stock_signals}

        for series in dataset.series:
            opportunity_snapshot = opportunity_by_stock.get(series.stock_id)
            if opportunity_snapshot is not None:
                candidate = AlertGenerator.generate(
                    stock_id=series.stock_id,
                    stock_quality=_stock_quality(opportunity_snapshot.stock_quality_score),
                    entry_quality=opportunity_snapshot.entry_quality_score,
                    classification=opportunity_snapshot.classification,
                )
                if candidate is not None:
                    candidates.append(candidate)
                    observed_at = series.bars[-1].timestamp
                    signal_id = uuid5(
                        self.NAMESPACE,
                        f"{series.stock_id}:opportunity",
                    )
                    events.append(
                        AlertEvent(
                            event_id=uuid5(self.NAMESPACE, f"{signal_id}:triggered"),
                            signal_id=signal_id,
                            symbol=series.symbol,
                            event_type=AlertEventType.SIGNAL_TRIGGERED,
                            occurred_at=observed_at,
                            message=(
                                f"{series.symbol} BUY opportunity: "
                                f"quality={candidate.stock_quality_score}, "
                                f"entry={candidate.entry_quality_score}"
                            ),
                        )
                    )

            stress_signal = stress_by_stock.get(series.stock_id)
            if stress_signal is not None and stress_signal.level in (
                StressLevel.HIGH,
                StressLevel.EXTREME,
            ):
                observed_at = series.bars[-1].timestamp
                signal_id = uuid5(
                    self.NAMESPACE,
                    f"{series.stock_id}:crash-radar",
                )
                events.append(
                    AlertEvent(
                        event_id=uuid5(self.NAMESPACE, f"{signal_id}:triggered"),
                        signal_id=signal_id,
                        symbol=series.symbol,
                        event_type=AlertEventType.SIGNAL_TRIGGERED,
                        occurred_at=observed_at,
                        message=(
                            f"{series.symbol} Crash Radar {stress_signal.level.value}: "
                            f"score={stress_signal.score}"
                        ),
                    )
                )

        return SyntheticAlertReport(
            scenario_name=dataset.scenario.name,
            seed=dataset.scenario.seed,
            candidates=tuple(candidates),
            events=tuple(events),
        )


def _stock_quality(total_score: int):
    from app.domain.fundamental_analysis.scoring import FundamentalScore
    from app.domain.scoring.stock_quality import StockQualityScore
    from app.domain.technical_analysis.scoring import TechnicalScore

    return StockQualityScore(
        fundamental_score=FundamentalScore(total=0, contributions=()),
        technical_score=TechnicalScore(
            trend_points=0,
            momentum_points=0,
            volume_points=total_score,
            total_score=total_score,
        ),
        total_score=total_score,
    )
