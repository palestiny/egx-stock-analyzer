from types import SimpleNamespace
from decimal import Decimal

import pytest

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.market_intelligence.rank_momentum import RankMomentumLeaders
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


def test_ranks_positive_and_negative_momentum_deterministically():
    store = InMemoryAnalysisResultStore()
    store.save("COMI", _result("12.5", 80))
    store.save("EGAL", _result("-8.0", 90))
    store.save("AIDC", _result("7.0", 95))

    ranking = RankMomentumLeaders(store).execute(["COMI", "EGAL", "AIDC"])

    assert [item.symbol for item in ranking.movers] == ["COMI", "AIDC", "EGAL"]
    assert ranking.metric == "momentum_rate_of_change"
    assert ranking.data_status == "HISTORICAL_ANALYSIS_RESULT"


def test_limit_is_enforced():
    store = InMemoryAnalysisResultStore()
    store.save("COMI", _result("12.5", 80))
    store.save("AIDC", _result("7.0", 95))

    ranking = RankMomentumLeaders(store).execute(["COMI", "AIDC"], limit=1)

    assert len(ranking.movers) == 1
    assert ranking.movers[0].symbol == "COMI"


def test_rejects_duplicate_symbols():
    store = InMemoryAnalysisResultStore()
    with pytest.raises(ValueError, match="Duplicate"):
        RankMomentumLeaders(store).execute(["COMI", "COMI"])
