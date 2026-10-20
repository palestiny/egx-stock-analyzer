from dataclasses import asdict, dataclass
from decimal import Decimal

from app.domain.market_intelligence.scanner import TechnicalScannerResult


@dataclass(frozen=True)
class TechnicalScannerMatchResponse:
    symbol: str
    score: int
    criteria: tuple[str, ...]
    momentum_percent: Decimal | None
    volume_ratio: Decimal | None
    resistance_price: Decimal | None
    distance_to_resistance_percent: Decimal | None


@dataclass(frozen=True)
class TechnicalScannerResponse:
    scanner_id: str
    evaluated_symbols: int
    data_status: str
    matches: tuple[TechnicalScannerMatchResponse, ...]

    @staticmethod
    def from_result(result: TechnicalScannerResult) -> "TechnicalScannerResponse":
        return TechnicalScannerResponse(
            scanner_id=result.scanner_id,
            evaluated_symbols=result.evaluated_symbols,
            data_status=result.data_status,
            matches=tuple(
                TechnicalScannerMatchResponse(
                    symbol=item.symbol,
                    score=item.score,
                    criteria=tuple(criterion.value for criterion in item.criteria),
                    momentum_percent=item.momentum_percent,
                    volume_ratio=item.volume_ratio,
                    resistance_price=item.resistance_price,
                    distance_to_resistance_percent=item.distance_to_resistance_percent,
                )
                for item in result.matches
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
