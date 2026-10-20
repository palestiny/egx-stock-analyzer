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


def _result(
    score: int,
    *,
    trend,
    momentum,
    volume,
    classification,
    momentum_percent=Decimal("5"),
    volume_ratio=Decimal("1.5"),
    entry_context=None,
):
    return SimpleNamespace(
        technical_analysis=SimpleNamespace(
            trend=TrendEvidence(trend),
            momentum=MomentumEvidence(momentum, momentum_percent),
            volume=VolumeEvidence(volume, volume_ratio),
        ),
        stock_quality=SimpleNamespace(total_score=score),
        opportunity=SimpleNamespace(classification=classification),
        entry_context=entry_context,
    )


def _entry(current: str, resistance: str = "100"):
    return SimpleNamespace(
        current_price=SimpleNamespace(value=Decimal(current)),
        nearest_resistance=SimpleNamespace(price=SimpleNamespace(value=Decimal(resistance))),
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
    assert result.matches[0].momentum_percent == Decimal("5")
    assert result.matches[0].volume_ratio == Decimal("1.5")


def test_pre_breakout_watchlist_requires_momentum_volume_and_near_resistance():
    store = InMemoryAnalysisResultStore()
    store.save(
        "COMI",
        _result(
            92,
            trend=TrendStatus.UPTREND,
            momentum=MomentumStatus.POSITIVE,
            volume=VolumeStatus.ABOVE_AVERAGE,
            classification=OpportunityClassification.WATCH,
            momentum_percent=Decimal("4.2"),
            volume_ratio=Decimal("1.8"),
            entry_context=_entry("96"),
        ),
    )
    store.save(
        "EGAL",
        _result(
            80,
            trend=TrendStatus.UPTREND,
            momentum=MomentumStatus.POSITIVE,
            volume=VolumeStatus.ABOVE_AVERAGE,
            classification=OpportunityClassification.WATCH,
            volume_ratio=Decimal("1.4"),
            entry_context=_entry("98"),
        ),
    )
    store.save(
        "ABUK",
        _result(
            85,
            trend=TrendStatus.UPTREND,
            momentum=MomentumStatus.NEGATIVE,
            volume=VolumeStatus.ABOVE_AVERAGE,
            classification=OpportunityClassification.WATCH,
            volume_ratio=Decimal("2.0"),
            entry_context=_entry("98"),
        ),
    )
    store.save(
        "TMGH",
        _result(
            88,
            trend=TrendStatus.UPTREND,
            momentum=MomentumStatus.POSITIVE,
            volume=VolumeStatus.ABOVE_AVERAGE,
            classification=OpportunityClassification.WATCH,
            volume_ratio=Decimal("2.2"),
            entry_context=_entry("94"),
        ),
    )

    result = RunTechnicalScanner(store).execute(
        ["COMI", "EGAL", "ABUK", "TMGH"],
        scanner_id="pre-breakout-momentum-volume",
    )

    assert [item.symbol for item in result.matches] == ["COMI"]
    match = result.matches[0]
    assert match.criteria == (
        ScannerCriterion.UPTREND,
        ScannerCriterion.POSITIVE_MOMENTUM,
        ScannerCriterion.ABOVE_AVERAGE_VOLUME,
        ScannerCriterion.VOLUME_EXPANSION,
        ScannerCriterion.NEAR_RESISTANCE,
    )
    assert match.momentum_percent == Decimal("4.2")
    assert match.volume_ratio == Decimal("1.8")
    assert match.resistance_price == Decimal("100")
    assert match.distance_to_resistance_percent == Decimal("-4")


def test_scanner_rejects_duplicate_symbols():
    store = InMemoryAnalysisResultStore()
    with pytest.raises(ValueError, match="Duplicate"):
        RunTechnicalScanner(store).execute(["COMI", "COMI"])
