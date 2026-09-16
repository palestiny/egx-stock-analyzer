from datetime import date

from app.domain.execution import Execution, ExecutionState
from app.application.execution.idempotency import ExecutionIdentity, ExecutionRegistry


def make_identity() -> ExecutionIdentity:
    return ExecutionIdentity(
        analysis_date=date(2026, 9, 15),
        analysis_type="daily_market_analysis",
        strategy_version="v1",
        configuration="default",
    )


def test_same_identity_does_not_create_duplicate_for_running_execution():
    registry = ExecutionRegistry()
    identity = make_identity()

    first = registry.create(identity)
    first.start()

    second = registry.create(identity)

    assert second is first


def test_same_identity_does_not_create_duplicate_for_completed_execution():
    registry = ExecutionRegistry()
    identity = make_identity()

    first = registry.create(identity)
    first.start()
    first.complete()

    second = registry.create(identity)

    assert second is first


def test_failed_execution_allows_recovery_execution():
    registry = ExecutionRegistry()
    identity = make_identity()

    first = registry.create(identity)
    first.start()
    first.fail()

    second = registry.create(identity)

    assert second is not first
    assert second.state == ExecutionState.CREATED


def test_completed_with_errors_allows_recovery_execution():
    registry = ExecutionRegistry()
    identity = make_identity()

    first = registry.create(identity)
    first.start()
    first.record_stock_success("EGAL")
    first.record_stock_failure("IEEC")
    first.finish()

    second = registry.create(identity)

    assert second is not first
    assert second.state == ExecutionState.CREATED
