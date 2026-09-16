from dataclasses import dataclass

from app.application.analysis.stock_analysis import StockAnalysisResult


@dataclass(frozen=True)
class AnalysisResultResponse:
    symbol: str
    technical_score: int
    fundamental_score: int
    stock_quality: int
    entry_quality: int
    opportunity: str

    @classmethod
    def from_result(cls, symbol: str, result: StockAnalysisResult) -> "AnalysisResultResponse":
        return cls(
            symbol=symbol,
            technical_score=result.technical_score.total_score,
            fundamental_score=result.fundamental_score.total,
            stock_quality=result.stock_quality.total_score,
            entry_quality=result.entry_quality.total_score,
            opportunity=result.opportunity.classification.value,
        )
