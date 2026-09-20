from dataclasses import dataclass

from app.application.analysis.rank_market_opportunities import RankedOpportunity
from app.application.analysis.get_market_opportunity_ranking import MarketOpportunityView


@dataclass(frozen=True)
class MarketOpportunityItemResponse:
    symbol: str
    classification: str
    stock_quality: int
    entry_quality: int
    technical_score: int
    fundamental_score: int

    @classmethod
    def from_ranked_opportunity(
        cls,
        opportunity: RankedOpportunity,
    ) -> "MarketOpportunityItemResponse":
        result = opportunity.result
        return cls(
            symbol=opportunity.symbol,
            classification=result.opportunity.classification.value,
            stock_quality=result.stock_quality.total_score,
            entry_quality=result.entry_quality.total_score,
            technical_score=result.technical_score.total_score,
            fundamental_score=result.fundamental_score.total,
        )


@dataclass(frozen=True)
class MarketOpportunityViewResponse:
    opportunities: list[MarketOpportunityItemResponse]
    missing_symbols: list[str]

    @classmethod
    def from_view(
        cls,
        view: MarketOpportunityView,
    ) -> "MarketOpportunityViewResponse":
        return cls(
            opportunities=[
                MarketOpportunityItemResponse.from_ranked_opportunity(item)
                for item in view.opportunities
            ],
            missing_symbols=list(view.missing_symbols),
        )
