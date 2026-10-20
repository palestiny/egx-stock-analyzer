from tools.m61_public_comi_signal_diagnostic import run_signal_diagnostic


def test_public_comi_forward_signal_diagnostic_is_deterministic() -> None:
    first = run_signal_diagnostic()
    second = run_signal_diagnostic()

    assert first == second
    assert first["source"] == (
        "M-Abdelmegeed/Project-EGX, "
        "EGX Stock data/COMI Historical Data.csv"
    )
    groups = first["forward_returns_by_group_and_horizon"]
    assert groups["all_eligible_sessions"]["1"]["samples"] > 100
    assert set(groups) == {
        "all_eligible_sessions",
        "positive_momentum",
        "positive_momentum_and_volume_at_least_1_5x",
        "strategy_buy",
    }
    assert set(groups["all_eligible_sessions"]) == {"1", "3", "5", "10"}
    assert first["signal_definitions"]["execution_assumption"].startswith(
        "entry at next session open"
    )
    assert any("not an investment recommendation" in item for item in first["limitations"])
