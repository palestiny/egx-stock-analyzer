from dataclasses import asdict, dataclass

from app.domain.market_intelligence.fibonacci import FibonacciScanResult


@dataclass(frozen=True)
class FibonacciResponse:
    metric: str
    data_status: str
    opportunities: tuple[dict[str, object], ...]

    @staticmethod
    def from_result(result: FibonacciScanResult) -> "FibonacciResponse":
        return FibonacciResponse(
            metric=result.metric,
            data_status=result.data_status,
            opportunities=tuple(asdict(item) for item in result.opportunities),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
