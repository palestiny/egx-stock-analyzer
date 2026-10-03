from dataclasses import asdict, dataclass

from app.domain.market_intelligence.scanner import TechnicalScannerResult


@dataclass(frozen=True)
class TechnicalScannerMatchResponse:
    symbol: str
    score: int
    criteria: tuple[str, ...]


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
                )
                for item in result.matches
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
