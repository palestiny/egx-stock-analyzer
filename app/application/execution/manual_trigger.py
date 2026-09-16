from app.application.analysis.daily_market_analysis import (
    DailyMarketAnalysis,
    DailyMarketAnalysisResult,
    StockAnalysisInput,
)
from app.domain.execution import Execution


class ManualAnalysisTrigger:
    def __init__(self, analysis: DailyMarketAnalysis) -> None:
        self._analysis = analysis

    def run(self, inputs: list[StockAnalysisInput]) -> Execution:
        result: DailyMarketAnalysisResult = self._analysis.run(inputs)
        return result.execution
