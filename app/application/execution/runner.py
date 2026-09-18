from collections.abc import Callable

from app.application.execution.retry import RetryPolicy
from app.domain.execution import Execution


class ExecutionRunner:
    def __init__(self, retry_policy: RetryPolicy) -> None:
        self._retry_policy = retry_policy

    def run_stock(
        self,
        execution: Execution,
        stock_id: str,
        operation: Callable[[], None],
    ) -> None:
        attempt = 1

        while True:
            try:
                operation()
                execution.record_stock_success(stock_id)
                return
            except Exception as error:
                if self._retry_policy.should_retry(error, attempt):
                    attempt += 1
                    continue

                execution.record_stock_failure(stock_id, reason=str(error))
                return
