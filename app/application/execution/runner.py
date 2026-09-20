from collections.abc import Callable, Collection



from app.application.execution.retry import RetryPolicy
from app.domain.execution import Execution


class ExecutionRunner:
    def __init__(
        self,
        retry_policy: RetryPolicy,
        propagate_exceptions: Collection[type[Exception]] = (),
    ) -> None:
        self._retry_policy = retry_policy
        self._propagate_exceptions = tuple(propagate_exceptions)

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
                if isinstance(error, self._propagate_exceptions):
                    raise
                if self._retry_policy.should_retry(error, attempt):
                    attempt += 1
                    continue

                execution.record_stock_failure(stock_id, reason=str(error))
                return
