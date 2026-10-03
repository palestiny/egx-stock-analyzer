from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.market_intelligence.run_technical_scanner import RunTechnicalScanner
from app.domain.market_intelligence.scanner import ScannerCriterion
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus


def _result(score: int, *, trend, momentum, volume, classification):
    return SimpleNamespace(
        technical_analysis=SimpleNamespace(
            trend=TrendEvidence(trend),
            momentum=MomentumEvidence(momentum, Decimal("5")),
            volume=VolumeEvidence(volume, Decimal("1.5")),
        ),
        stock_quality=SimpleNamespace(total_score=score),
        opportunity=SimpleNamespace(classification=classification),
    )


def test_scanner_returns_explainable_matches():
    store = InMemoryAnalysisResultStore()
    store.save(
        "COMI",
        _result(
            92,
            trend=TrendStatus.UPTREND,
            momentum=MomentumStatus.POSITIVE,
            volume=VolumeStatus.ABOVE_AVERAGE,
            classification=OpportunityClassification.BUY,
        ),
    )
    store.save(
        "EGAL",
        _result(
            80,
            trend=TrendStatus.UPTREND,
            momentum=MomentumStatus.NEGATIVE,
            volume=VolumeStatus.ABOVE_AVERAGE,
            classification=OpportunityClassification.WATCH,
        ),
    )

    result = RunTechnicalScanner(store).execute(["COMI", "EGAL"])

    assert [item.symbol for item in result.matches] == ["COMI"]
    assert result.matches[0].criteria == (
        ScannerCriterion.UPTREND,
        ScannerCriterion.POSITIVE_MOMENTUM,
        ScannerCriterion.ABOVE_AVERAGE_VOLUME,
        ScannerCriterion.ACTIONABLE_CLASSIFICATION,
    )


def test_scanner_rejects_duplicate_symbols():
    store = InMemoryAnalysisResultStore()
    with pytest.raises(ValueError, match="Duplicate"):
        RunTechnicalScanner(store).execute(["COMI", "COMI"])
