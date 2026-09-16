from collections.abc import Callable, Iterable

from app.application.execution.retry import RetryPolicy
from app.application.execution.runner import ExecutionRunner
from app.domain.execution import Execution


class ExecutionOrchestrator:
    def __init__(self, retry_policy: RetryPolicy) -> None:
        self._runner = ExecutionRunner(retry_policy)

    def run(
        self,
        stock_ids: Iterable[str],
        operation: Callable[[str], None],
    ) -> Execution:
        execution = Execution.create()
        execution.start()

        for stock_id in stock_ids:
            self._runner.run_stock(
                execution,
                stock_id,
                lambda stock_id=stock_id: operation(stock_id),
            )

        execution.finish()
        return execution
