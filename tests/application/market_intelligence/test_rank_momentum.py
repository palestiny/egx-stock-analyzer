from decimal import Decimal
from uuid import uuid4

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.market_intelligence.rank_momentum import RankMomentumLeaders
from app.application.analysis.stock_analysis import StockAnalysisResult


def _result(momentum: str, score: int) -> StockAnalysisResult:
    from dataclasses import replace
    from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus

    base = object.__new__(StockAnalysisResult)
    base.__dict__ = {}
    return replace(
        StockAnalysisResult(
            technical_analysis=type("T", (), {
                "momentum": MomentumEvidence(
                    MomentumStatus.POSITIVE if Decimal(momentum) > 0 else MomentumStatus.NEGATIVE,
                    Decimal(momentum),
                )
            })(),
            fundamental_analysis=object(),
            technical_score=object(),
            fundamental_score=object(),
            stock_quality=type("S", (), {"total_score": score})(),
            entry_context=object(),
            entry_quality=object(),
            opportunity=object(),
        ),
    )
