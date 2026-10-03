from dataclasses import asdict, dataclass
from decimal import Decimal

from app.domain.market_intelligence.sectors import SectorRanking


@dataclass(frozen=True)
class SectorItemResponse:
    sector: str
    symbol_count: int
    average_momentum_percent: Decimal
    average_score: Decimal


@dataclass(frozen=True)
class SectorRankingResponse:
    direction: str
    metric: str
    data_status: str
    sectors: tuple[SectorItemResponse, ...]

    @staticmethod
    def from_ranking(ranking: SectorRanking) -> "SectorRankingResponse":
        return SectorRankingResponse(
            direction=ranking.direction.value,
            metric=ranking.metric,
            data_status=ranking.data_status,
            sectors=tuple(
                SectorItemResponse(
                    sector=item.sector,
                    symbol_count=item.symbol_count,
                    average_momentum_percent=item.average_momentum_percent,
                    average_score=item.average_score,
                )
                for item in ranking.sectors
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
