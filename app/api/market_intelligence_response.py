from dataclasses import asdict, dataclass
from decimal import Decimal

from app.domain.market_intelligence.movers import MarketMoverRanking


@dataclass(frozen=True)
class MarketMoverItemResponse:
    symbol: str
    direction: str
    momentum_percent: Decimal
    score: int


@dataclass(frozen=True)
class MarketMoverRankingResponse:
    metric: str
    data_status: str
    movers: tuple[MarketMoverItemResponse, ...]

    @staticmethod
    def from_ranking(ranking: MarketMoverRanking) -> "MarketMoverRankingResponse":
        return MarketMoverRankingResponse(
            metric=ranking.metric,
            data_status=ranking.data_status,
            movers=tuple(
                MarketMoverItemResponse(
                    symbol=item.symbol,
                    direction=item.direction.value,
                    momentum_percent=item.momentum_percent,
                    score=item.score,
                )
                for item in ranking.movers
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
