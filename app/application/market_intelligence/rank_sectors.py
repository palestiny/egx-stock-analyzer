from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal

from app.application.analysis.result_store import AnalysisResultStore
from app.domain.market_intelligence.sectors import (
    SectorDirection,
    SectorRanking,
    SectorSnapshot,
)


@dataclass(frozen=True)
class SectorInput:
    symbol: str
    sector: str


@dataclass(frozen=True)
class RankSectors:
    result_store: AnalysisResultStore

    def execute(
        self,
        inputs: list[SectorInput],
        direction: SectorDirection = SectorDirection.LEADING,
        limit: int = 10,
    ) -> SectorRanking:
        if limit <= 0:
            raise ValueError("limit must be positive")

        normalized: list[SectorInput] = []
        seen: set[str] = set()
        for item in inputs:
            symbol = item.symbol.strip().upper()
            sector = item.sector.strip()
            if not symbol or not sector:
                raise ValueError("symbol and sector are required")
            if symbol in seen:
                raise ValueError(f"Duplicate stock symbol in sector ranking: {symbol}")
            seen.add(symbol)
            normalized.append(SectorInput(symbol, sector))

        buckets: dict[str, list[tuple[Decimal, int]]] = defaultdict(list)
        for item in normalized:
            record = self.result_store.get_record(item.symbol)
            if record is None:
                continue
            momentum = record.result.technical_analysis.momentum.rate_of_change
            if momentum is None:
                continue
            buckets[item.sector].append(
                (Decimal(str(momentum)), record.result.stock_quality.total_score)
            )

        snapshots = [
            SectorSnapshot(
                sector=sector,
                symbol_count=len(values),
                average_momentum_percent=sum((v[0] for v in values), Decimal("0")) / Decimal(len(values)),
                average_score=Decimal(sum(v[1] for v in values)) / len(values),
            )
            for sector, values in buckets.items()
            if values
        ]

        reverse = direction is SectorDirection.LEADING
        snapshots.sort(
            key=lambda item: (
                -item.average_momentum_percent if reverse else item.average_momentum_percent,
                -item.average_score,
                item.sector,
            )
        )

        return SectorRanking(
            sectors=tuple(snapshots[:limit]),
            direction=direction,
            metric="average_momentum_percent",
            data_status="HISTORICAL_ANALYSIS_RESULT",
        )
