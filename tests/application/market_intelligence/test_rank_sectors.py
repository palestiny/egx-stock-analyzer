from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.market_intelligence.rank_sectors import RankSectors, SectorInput
from app.domain.market_intelligence.sectors import SectorDirection
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus


def _result(momentum: str, score: int) -> SimpleNamespace:
    value = Decimal(momentum)
    return SimpleNamespace(
        technical_analysis=SimpleNamespace(
            momentum=MomentumEvidence(
                MomentumStatus.POSITIVE if value > 0 else MomentumStatus.NEGATIVE,
                value,
            )
        ),
        stock_quality=SimpleNamespace(total_score=score),
    )


def test_ranks_sectors_by_average_momentum():
    store = InMemoryAnalysisResultStore()
    store.save("COMI", _result("10", 90))
    store.save("EGAL", _result("4", 80))
    store.save("AIDC", _result("6", 70))

    ranking = RankSectors(store).execute(
        [
            SectorInput("COMI", "Banks"),
            SectorInput("EGAL", "Metals"),
            SectorInput("AIDC", "Banks"),
        ]
    )

    assert [item.sector for item in ranking.sectors] == ["Banks", "Metals"]
    assert ranking.sectors[0].average_momentum_percent == Decimal("8")


def test_laggard_order_is_ascending():
    store = InMemoryAnalysisResultStore()
    store.save("COMI", _result("-2", 90))
    store.save("EGAL", _result("-8", 80))

    ranking = RankSectors(store).execute(
        [
            SectorInput("COMI", "Banks"),
            SectorInput("EGAL", "Metals"),
        ],
        direction=SectorDirection.LAGGING,
    )

    assert [item.sector for item in ranking.sectors] == ["Metals", "Banks"]


def test_rejects_duplicate_symbols():
    with pytest.raises(ValueError, match="Duplicate"):
        RankSectors(InMemoryAnalysisResultStore()).execute(
            [SectorInput("COMI", "Banks"), SectorInput("COMI", "Banks")]
        )
