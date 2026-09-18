from dataclasses import dataclass

from app.application.analysis.rank_market_opportunities import (
    MarketOpportunityInput,
    RankMarketOpportunities,
)
from app.application.analysis.result_store import AnalysisResultStore


@dataclass(frozen=True)
class MarketOpportunityView:
    opportunities: tuple
    missing_symbols: tuple[str, ...]


class GetMarketOpportunityRanking:
    def __init__(
        self,
        result_store: AnalysisResultStore,
        rank_market_opportunities: RankMarketOpportunities,
    ) -> None:
        self._result_store = result_store
        self._rank_market_opportunities = rank_market_opportunities

    def execute(self, symbols: list[str]) -> MarketOpportunityView:
        normalized_symbols = [symbol.strip().upper() for symbol in symbols]

        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("Duplicate stock symbol in market opportunity view")

        inputs: list[MarketOpportunityInput] = []
        missing: list[str] = []

        for symbol in normalized_symbols:
            record = self._result_store.get_record(symbol)
            if record is None:
                missing.append(symbol)
                continue

            inputs.append(
                MarketOpportunityInput(
                    symbol=symbol,
                    result=record.result,
                )
            )

        ranked = self._rank_market_opportunities.execute(inputs)

        return MarketOpportunityView(
            opportunities=ranked.opportunities,
            missing_symbols=tuple(missing),
        )
