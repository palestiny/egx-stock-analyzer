from dataclasses import dataclass

from app.application.analysis.result_store import AnalysisResultStore
from app.domain.market_intelligence.movers import (
    MarketMover,
    MarketMoverRanking,
    MoverDirection,
)


@dataclass(frozen=True)
class RankMomentumLeaders:
    result_store: AnalysisResultStore

    def execute(self, symbols: list[str], limit: int = 10) -> MarketMoverRanking:
        normalized = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate stock symbol in momentum ranking")
        if limit <= 0:
            raise ValueError("limit must be positive")

        leaders: list[MarketMover] = []
        laggards: list[MarketMover] = []

        for symbol in normalized:
            record = self.result_store.get_record(symbol)
            if record is None:
                continue
            momentum = record.result.technical_analysis.momentum.rate_of_change
            if momentum is None:
                continue
            score = record.result.stock_quality.total_score
            mover = MarketMover(
                symbol=symbol,
                direction=MoverDirection.LEADER if momentum > 0 else MoverDirection.LAGGARD,
                momentum_percent=momentum,
                score=score,
            )
            (leaders if momentum > 0 else laggards).append(mover)

        leaders.sort(key=lambda item: (-item.momentum_percent, -item.score, item.symbol))
        laggards.sort(key=lambda item: (item.momentum_percent, -item.score, item.symbol))

        return MarketMoverRanking(
            movers=tuple((leaders + laggards)[:limit]),
            metric="momentum_rate_of_change",
            data_status="HISTORICAL_ANALYSIS_RESULT",
        )
