from datetime import date
from unittest.mock import Mock

from app.application.execution.run_configured_market_analysis_with_automatic_alert_delivery import (
    RunConfiguredMarketAnalysisWithAutomaticAlertDelivery,
)
from app.application.notifications.automatic_alert_delivery import (
    AutomaticAlertDeliveryResult,
    AutomaticAlertDeliveryState,
)
from app.domain.execution import Execution, ExecutionState


AS_OF = date(2026, 9, 19)


def make_execution(state: ExecutionState, successful: set[str] | None = None) -> Execution:
    execution = Execution.create()
    execution.start()

    for symbol in successful or set():
        execution.record_stock_success(symbol)

    if state is ExecutionState.COMPLETED:
        if successful:
            execution.finish()
        else:
            execution.complete()
    elif state is ExecutionState.COMPLETED_WITH_ERRORS:
        execution.record_stock_failure("FAILED")
        execution.finish()
    elif state is ExecutionState.FAILED:
        execution.record_stock_failure("FAILED")
        execution.finish()
    else:
        raise AssertionError(f"Unsupported fixture state: {state}")

    return execution


def delivery_result(state: AutomaticAlertDeliveryState) -> AutomaticAlertDeliveryResult:
    return AutomaticAlertDeliveryResult(
        state=state,
        attempted_count=1,
        delivered_count=1 if state is AutomaticAlertDeliveryState.COMPLETED else 0,
        skipped_count=0,
        failed_count=0 if state is AutomaticAlertDeliveryState.COMPLETED else 1,
        failure_reasons={},
    )


def test_successful_analysis_is_followed_by_one_delivery_call():
    analysis = Mock()
    delivery = Mock()
    execution = make_execution(ExecutionState.COMPLETED, {"EGAL"})
    analysis.execute.return_value = execution
    delivery.execute.return_value = delivery_result(AutomaticAlertDeliveryState.COMPLETED)

    workflow = RunConfiguredMarketAnalysisWithAutomaticAlertDelivery(analysis, delivery)

    result = workflow.execute(AS_OF)

    assert result.analysis_execution is execution
    assert result.delivery_result.state is AutomaticAlertDeliveryState.COMPLETED
    analysis.execute.assert_called_once_with(AS_OF)
    delivery.execute.assert_called_once_with(execution)


def test_partial_analysis_still_delivers_successful_symbols():
    analysis = Mock()
    delivery = Mock()
    execution = make_execution(ExecutionState.COMPLETED_WITH_ERRORS, {"EGAL"})
    analysis.execute.return_value = execution
    delivery.execute.return_value = delivery_result(AutomaticAlertDeliveryState.COMPLETED)

    workflow = RunConfiguredMarketAnalysisWithAutomaticAlertDelivery(analysis, delivery)

    result = workflow.execute(AS_OF)

    assert result.analysis_execution is execution
    delivery.execute.assert_called_once_with(execution)


def test_failed_analysis_execution_is_still_passed_to_delivery():
    analysis = Mock()
    delivery = Mock()
    execution = make_execution(ExecutionState.FAILED)
    analysis.execute.return_value = execution
    delivery.execute.return_value = delivery_result(AutomaticAlertDeliveryState.COMPLETED)

    workflow = RunConfiguredMarketAnalysisWithAutomaticAlertDelivery(analysis, delivery)

    result = workflow.execute(AS_OF)

    assert result.analysis_execution is execution
    delivery.execute.assert_called_once_with(execution)


def test_analysis_exception_prevents_delivery():
    analysis = Mock()
    delivery = Mock()
    analysis.execute.side_effect = RuntimeError("analysis failed")

    workflow = RunConfiguredMarketAnalysisWithAutomaticAlertDelivery(analysis, delivery)

    try:
        workflow.execute(AS_OF)
    except RuntimeError as error:
        assert str(error) == "analysis failed"
    else:
        raise AssertionError("Expected analysis exception")

    delivery.execute.assert_not_called()


def test_delivery_outcome_does_not_change_analysis_execution():
    analysis = Mock()
    delivery = Mock()
    execution = make_execution(ExecutionState.COMPLETED, {"EGAL"})
    analysis.execute.return_value = execution
    delivery.execute.return_value = delivery_result(
        AutomaticAlertDeliveryState.FAILED
    )

    workflow = RunConfiguredMarketAnalysisWithAutomaticAlertDelivery(analysis, delivery)

    result = workflow.execute(AS_OF)

    assert result.analysis_execution.state is ExecutionState.COMPLETED
    assert result.delivery_result.state is AutomaticAlertDeliveryState.FAILED
