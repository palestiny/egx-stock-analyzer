from datetime import date
from unittest.mock import Mock

from app.application.analysis.run_configured_market_analysis_with_automatic_alerts import (
    RunConfiguredMarketAnalysisWithAutomaticAlerts,
)
from app.application.notifications.automatic_alert_delivery import (
    AutomaticAlertDeliveryResult,
    AutomaticAlertDeliveryState,
)
from app.domain.execution import Execution, ExecutionState


AS_OF = date(2026, 9, 19)


def make_execution(state: ExecutionState, successes: tuple[str, ...] = ()) -> Execution:
    execution = Execution.create()
    execution.start()
    for symbol in successes:
        execution.record_stock_success(symbol)
    if state is ExecutionState.COMPLETED:
        execution.complete()
    elif state is ExecutionState.COMPLETED_WITH_ERRORS:
        execution.complete_with_errors()
    else:
        execution.fail()
    return execution


def make_delivery(state: AutomaticAlertDeliveryState) -> AutomaticAlertDeliveryResult:
    return AutomaticAlertDeliveryResult(
        state=state,
        attempted_count=1,
        delivered_count=1 if state is AutomaticAlertDeliveryState.COMPLETED else 0,
        skipped_count=0,
        failed_count=0 if state is AutomaticAlertDeliveryState.COMPLETED else 1,
        failure_reasons={},
    )


def test_completed_analysis_invokes_automatic_delivery_once():
    analysis = Mock()
    execution = make_execution(ExecutionState.COMPLETED, ("EGAL",))
    analysis.execute.return_value = execution
    delivery = Mock()
    delivery.execute.return_value = make_delivery(AutomaticAlertDeliveryState.COMPLETED)

    result = RunConfiguredMarketAnalysisWithAutomaticAlerts(analysis, delivery).execute(AS_OF)

    assert result.execution is execution
    assert result.automatic_alert_delivery is not None
    delivery.execute.assert_called_once_with(execution)


def test_partial_analysis_delivers_successful_symbols():
    analysis = Mock()
    execution = make_execution(ExecutionState.COMPLETED_WITH_ERRORS, ("EGAL",))
    analysis.execute.return_value = execution
    delivery = Mock()
    delivery.execute.return_value = make_delivery(AutomaticAlertDeliveryState.COMPLETED_WITH_ERRORS)

    result = RunConfiguredMarketAnalysisWithAutomaticAlerts(analysis, delivery).execute(AS_OF)

    assert result.execution.state is ExecutionState.COMPLETED_WITH_ERRORS
    delivery.execute.assert_called_once_with(execution)


def test_failed_analysis_does_not_invoke_delivery():
    analysis = Mock()
    execution = make_execution(ExecutionState.FAILED)
    analysis.execute.return_value = execution
    delivery = Mock()

    result = RunConfiguredMarketAnalysisWithAutomaticAlerts(analysis, delivery).execute(AS_OF)

    assert result.automatic_alert_delivery is None
    delivery.execute.assert_not_called()


def test_delivery_failure_does_not_change_analysis_execution():
    analysis = Mock()
    execution = make_execution(ExecutionState.COMPLETED, ("EGAL",))
    analysis.execute.return_value = execution
    delivery = Mock()
    delivery_result = make_delivery(AutomaticAlertDeliveryState.FAILED)
    delivery.execute.return_value = delivery_result

    result = RunConfiguredMarketAnalysisWithAutomaticAlerts(analysis, delivery).execute(AS_OF)

    assert result.execution is execution
    assert result.execution.state is ExecutionState.COMPLETED
    assert result.automatic_alert_delivery is delivery_result
