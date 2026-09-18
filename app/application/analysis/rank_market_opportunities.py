from dataclasses import dataclass
from typing import Any

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
class RankedMarketOpportunities:
    items: tuple[RankedOpportunity, ...]


class RankMarketOpportunities:
    _RANKABLE_CLASSIFICATIONS = frozenset(
        {
            OpportunityClassification.BUY,
            OpportunityClassification.WATCH,
        }
    )

    def execute(
        self,
        opportunities: list[MarketOpportunityInput],
    ) -> RankedMarketOpportunities:
        normalized: list[MarketOpportunityInput] = [
            MarketOpportunityInput(
                symbol=item.symbol.strip().upper(),
                result=item.result,
            )
            for item in opportunities
        ]

        symbols = [item.symbol for item in normalized]
        if len(symbols) != len(set(symbols)):
            raise ValueError("Duplicate stock symbol in opportunity ranking input")

        eligible = [
            item
            for item in normalized
            if item.result.opportunity.classification in self._RANKABLE_CLASSIFICATIONS
        ]

        ranked = sorted(
            eligible,
            key=lambda item: (
                -item.result.stock_quality.total_score,
                -item.result.entry_quality.total_score,
                -item.result.technical_score.total_score,
                -item.result.fundamental_score.total,
                item.symbol,
            ),
        )

        return RankedMarketOpportunities(
            items=tuple(
                RankedOpportunity(symbol=item.symbol, result=item.result)
                for item in ranked
            )
        )
