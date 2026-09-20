from unittest.mock import Mock

from app.application.analysis.daily_market_analysis import StockAnalysisInput
from app.application.execution.manual_trigger import ManualAnalysisTrigger
from app.domain.execution import Execution, ExecutionState


def test_manual_trigger_starts_daily_market_analysis():
    inputs = [Mock(spec=StockAnalysisInput)]
    expected_execution = Execution.create()
    expected_execution.start()

    analysis = Mock()
    analysis.run.return_value.execution = expected_execution

    trigger = ManualAnalysisTrigger(analysis)

    result = trigger.run(inputs)

    assert result is expected_execution
    analysis.run.assert_called_once_with(inputs)
