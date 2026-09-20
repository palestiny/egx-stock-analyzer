from datetime import date
from uuid import UUID

from app.application.analysis.daily_market_analysis import DailyMarketAnalysis, StockAnalysisInput
from app.application.analysis.input_assembler import AnalysisInputAssembler
from app.application.analysis.result_store import AnalysisResultStore
from app.application.execution.retry import RetryPolicy
from app.domain.execution import ExecutionState
from app.domain.stocks.stock import Stock


class RunStockAnalysis:
    def __init__(
        self,
        input_assembler: AnalysisInputAssembler,
        result_store: AnalysisResultStore,
        retry_policy: RetryPolicy,
    ) -> None:
        self._input_assembler = input_assembler
        self._daily_analysis = DailyMarketAnalysis(retry_policy, result_store)

    def execute(
        self,
        stock: Stock,
        as_of: date,
        analysis_run_id: UUID | None = None,
        owner_user_id: UUID | None = None,
    ) -> None:
        analysis_input: StockAnalysisInput = self._input_assembler.assemble(stock, as_of)
        result = self._daily_analysis.run(
            [analysis_input],
            analysis_date=as_of,
            analysis_run_id=analysis_run_id,
            owner_user_id=owner_user_id,
        )

        if result.execution.state is not ExecutionState.COMPLETED:
            reason = result.execution.failure_reasons.get(stock.symbol)
            detail = f": {reason}" if reason else ""
            raise RuntimeError(
                f"Stock analysis did not complete successfully: {result.execution.state}{detail}"
            )
