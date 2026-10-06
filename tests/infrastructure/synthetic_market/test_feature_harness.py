from app.infrastructure.synthetic_market.feature_harness import SyntheticFeatureHarness
from app.infrastructure.synthetic_market.generator import SyntheticMarketGenerator


def test_harness_executes_existing_feature_stack_for_entire_cohort():
    dataset = SyntheticMarketGenerator().generate(
        symbols=("COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO"),
        bars_per_symbol=300,
        seed=61001,
    )

    report = SyntheticFeatureHarness().run(dataset)

    assert report.scenario_name == "m61-controlled-egx-research"
    assert report.seed == 61001
    assert len(report.snapshots) == 10
    assert all(snapshot.support_count >= 0 for snapshot in report.snapshots)
    assert all(snapshot.resistance_count >= 0 for snapshot in report.snapshots)
    assert all(-3 <= snapshot.technical_score <= 3 for snapshot in report.snapshots)


def test_harness_is_reproducible():
    generator = SyntheticMarketGenerator()
    dataset = generator.generate(symbols=("COMI", "EGAL"), bars_per_symbol=300, seed=77)

    first = SyntheticFeatureHarness().run(dataset)
    second = SyntheticFeatureHarness().run(dataset)

    assert first == second
