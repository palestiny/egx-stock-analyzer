from dataclasses import dataclass

from app.application.analysis.stock_analysis import StockAnalysisResult
from app.domain.opportunity.classification import OpportunityClassification


@dataclass(frozen=True)
class MarketOpportunityInput:
    symbol: str
    result: StockAnalysisResult


@dataclass(frozen=True)
class RankedOpportunity:
    symbol: str
    result: StockAnalysisResult


@dataclass(frozen=True)
class RankedOpportunitySet:
    opportunities: tuple[RankedOpportunity, ...]


class RankMarketOpportunities:
    def execute(self, inputs: list[MarketOpportunityInput]) -> RankedOpportunitySet:
        normalized: list[MarketOpportunityInput] = []
        seen: set[str] = set()

        for item in inputs:
            symbol = item.symbol.strip().upper()
            if symbol in seen:
                raise ValueError(f"Duplicate stock symbol in opportunity ranking: {symbol}")
            seen.add(symbol)
            normalized.append(MarketOpportunityInput(symbol=symbol, result=item.result))

        eligible = [
            item
            for item in normalized
            if item.result.opportunity.classification
            in {OpportunityClassification.BUY, OpportunityClassification.WATCH}
        ]

        ordered = sorted(
            eligible,
            key=lambda item: (
                -item.result.stock_quality.total_score,
                -item.result.entry_quality.total_score,
                -item.result.technical_score.total_score,
                -item.result.fundamental_score.total,
                item.symbol,
            ),
        )

        return RankedOpportunitySet(
            opportunities=tuple(
                RankedOpportunity(symbol=item.symbol, result=item.result)
                for item in ordered
            )
        )
