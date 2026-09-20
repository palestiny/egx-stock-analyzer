from uuid import uuid4

from app.domain.analysis_run import (
    AnalysisRun,
    AnalysisRunOutcome,
    AnalysisRunOutcomeState,
)


def test_analysis_run_can_record_success_and_failure_outcomes():
    run = AnalysisRun.create()
    stock_id = uuid4()

    updated = run.with_outcomes(
        (
            AnalysisRunOutcome.success("EGAL", stock_id),
            AnalysisRunOutcome.failed("UNKNOWN", "UNKNOWN_SYMBOL", "UNKNOWN"),
        )
    )

    assert [outcome.symbol for outcome in updated.outcomes] == ["EGAL", "UNKNOWN"]
    assert updated.outcomes[0].state is AnalysisRunOutcomeState.SUCCESS
    assert updated.outcomes[0].stock_id == stock_id
    assert updated.outcomes[1].state is AnalysisRunOutcomeState.FAILED
    assert updated.outcomes[1].failure_code == "UNKNOWN_SYMBOL"
    assert updated.outcomes[1].failure_detail == "UNKNOWN"


def test_analysis_run_rejects_duplicate_outcome_symbols():
    run = AnalysisRun.create()

    try:
        run.with_outcomes(
            (
                AnalysisRunOutcome.success("EGAL"),
                AnalysisRunOutcome.failed("egal", "ANALYSIS_FAILED"),
            )
        )
    except ValueError as error:
        assert str(error) == "Duplicate analysis run outcome symbol: EGAL"
    else:
        raise AssertionError("Expected duplicate outcome validation to fail")


def test_analysis_run_bounds_failure_detail():
    run = AnalysisRun.create()

    updated = run.with_outcomes(
        (
            AnalysisRunOutcome.failed(
                "EGAL",
                "ANALYSIS_FAILED",
                "x" * 1000,
            ),
        )
    )

    assert len(updated.outcomes[0].failure_detail or "") <= 240


def test_analysis_run_legacy_instance_has_no_outcomes():
    run = AnalysisRun.create()

    assert run.outcomes == ()
