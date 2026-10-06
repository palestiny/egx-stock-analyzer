from datetime import date

from app.domain.technical_analysis.scoring import TechnicalScore
from app.infrastructure.synthetic_market.generator import SyntheticMarketGenerator
from app.infrastructure.synthetic_market.research_scenarios import SyntheticResearchScenarioBuilder
from app.infrastructure.synthetic_market.quality_harness import SyntheticQualityHarness


SYMBOLS = ("COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO")


def test_quality_harness_uses_only_pit_available_financials():
    dataset = SyntheticMarketGenerator().generate(
        symbols=SYMBOLS, bars_per_symbol=300, seed=61002
    )
    scenario = SyntheticResearchScenarioBuilder().build(dataset)
    technical = {
        series.stock_id: TechnicalScore(1, 1, 1, 3)
        for series in dataset.series
    }

    report = SyntheticQualityHarness().run(
        scenario,
        technical,
        decision_date=date(2025, 12, 1),
    )

    assert len(report.snapshots) == 10
    assert all(item.current_period_end == date(2024, 12, 31) for item in report.snapshots)
    assert all(item.previous_period_end == date(2023, 12, 31) for item in report.snapshots)
    assert all(item.fundamental_score == 3 for item in report.snapshots)
    assert all(item.total_score == 6 for item in report.snapshots)


def test_quality_harness_is_deterministic():
    dataset = SyntheticMarketGenerator().generate(
        symbols=("COMI", "EGAL"), bars_per_symbol=300, seed=61003
    )
    scenario = SyntheticResearchScenarioBuilder().build(dataset)
    technical = {
        series.stock_id: TechnicalScore(0, 1, 0, 1)
        for series in dataset.series
    }

    first = SyntheticQualityHarness().run(
        scenario, technical, decision_date=date(2025, 12, 1)
    )
    second = SyntheticQualityHarness().run(
        scenario, technical, decision_date=date(2025, 12, 1)
    )

    assert first == second
