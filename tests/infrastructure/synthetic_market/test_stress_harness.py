from app.domain.market_intelligence.stress import StressLevel
from app.infrastructure.synthetic_market.generator import SyntheticMarketGenerator
from app.infrastructure.synthetic_market.stress_harness import SyntheticStressHarness


SYMBOLS = ("COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO")


def test_synthetic_stress_harness_runs_complete_cohort():
    dataset = SyntheticMarketGenerator().generate(
        symbols=SYMBOLS,
        bars_per_symbol=300,
        seed=61004,
    )

    report = SyntheticStressHarness().run(dataset)

    assert report.scenario_name == "m61-controlled-egx-research"
    assert report.seed == 61004
    assert len(report.stock_signals) == 10
    assert 0 <= report.market.score <= 100
    assert report.market.level in StressLevel


def test_synthetic_stress_harness_is_reproducible():
    dataset = SyntheticMarketGenerator().generate(
        symbols=("COMI", "EGAL", "SWDY"),
        bars_per_symbol=300,
        seed=61005,
    )

    first = SyntheticStressHarness().run(dataset)
    second = SyntheticStressHarness().run(dataset)

    assert first == second
