from dataclasses import asdict, dataclass
from decimal import Decimal

from app.domain.market_intelligence.breakout import BreakoutScanResult


@dataclass(frozen=True)
class BreakoutMatchResponse:
    symbol: str
    direction: str
    status: str
    trigger_price: Decimal
    current_price: Decimal
    distance_percent: Decimal
    score: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class BreakoutResponse:
    matches: tuple[BreakoutMatchResponse, ...]
    evaluated_symbols: int
    data_status: str

    @classmethod
    def from_result(cls, result: BreakoutScanResult) -> "BreakoutResponse":
        return cls(
            matches=tuple(
                BreakoutMatchResponse(
                    symbol=item.symbol,
                    direction=item.direction.value,
                    status=item.status.value,
                    trigger_price=item.trigger_price,
                    current_price=item.current_price,
                    distance_percent=item.distance_percent,
                    score=item.score,
                    evidence=item.evidence,
                )
                for item in result.matches
            ),
            evaluated_symbols=result.evaluated_symbols,
            data_status=result.data_status,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
