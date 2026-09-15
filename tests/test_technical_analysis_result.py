from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import (
    PriceLevelEvidence,
    SupportResistanceEvidence,
)
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from datetime import datetime, timezone


# Tests that TechnicalAnalysisResult composes independent technical evidence.
# This exists because the result is a composition boundary, not a replacement for individual analyzers.
# Its function is to prove all current evidence types can coexist in one immutable result.
def test_technical_analysis_result_composes_evidence():
    stock_id = uuid4()
    timestamp = datetime(2026, 9, 1, tzinfo=timezone.utc)

    trend = TrendEvidence(TrendStatus.UPTREND)
    support_resistance = SupportResistanceEvidence(
        support_levels=(PriceLevelEvidence(Price(Decimal("100")), timestamp),),
        resistance_levels=(PriceLevelEvidence(Price(Decimal("120")), timestamp),),
    )
    momentum = MomentumEvidence(MomentumStatus.POSITIVE, Decimal("5"))
    volume = VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.5"))

    result = TechnicalAnalysisResult(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        trend=trend,
        support_resistance=support_resistance,
        momentum=momentum,
        volume=volume,
    )

    assert result.stock_id == stock_id
    assert result.timeframe is Timeframe.DAILY
    assert result.trend == trend
    assert result.support_resistance == support_resistance
    assert result.momentum == momentum
    assert result.volume == volume


# Tests that TechnicalAnalysisResult is immutable.
# This exists because analytical results must remain stable after calculation.
# Its function is to protect deterministic evidence composition.
def test_technical_analysis_result_is_immutable():
    result = TechnicalAnalysisResult(
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        trend=TrendEvidence(TrendStatus.SIDEWAYS),
        support_resistance=SupportResistanceEvidence((), ()),
        momentum=MomentumEvidence(MomentumStatus.NEUTRAL, Decimal("0")),
        volume=VolumeEvidence(VolumeStatus.EQUAL_TO_AVERAGE, Decimal("1")),
    )

    try:
        result.timeframe = Timeframe.DAILY
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("TechnicalAnalysisResult should be immutable")


# Tests that TechnicalAnalysisResult preserves evidence-specific insufficient states.
# This exists because one evidence type being insufficient must not invalidate unrelated evidence.
# Its function is to prove independent evidence semantics survive composition.
def test_technical_analysis_result_preserves_independent_evidence_states():
    result = TechnicalAnalysisResult(
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        trend=TrendEvidence(TrendStatus.INSUFFICIENT_DATA),
        support_resistance=SupportResistanceEvidence((), ()),
        momentum=MomentumEvidence(MomentumStatus.INSUFFICIENT_DATA),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.2")),
    )

    assert result.trend.status is TrendStatus.INSUFFICIENT_DATA
    assert result.momentum.status is MomentumStatus.INSUFFICIENT_DATA
    assert result.volume.status is VolumeStatus.ABOVE_AVERAGE


# Tests that repeated construction with the same evidence is deterministic.
# This exists because the technical-analysis result must be reproducible from the same inputs.
# Its function is to protect the composition boundary from hidden state.
def test_technical_analysis_result_is_deterministic():
    stock_id = uuid4()
    trend = TrendEvidence(TrendStatus.UPTREND)
    support_resistance = SupportResistanceEvidence((), ())
    momentum = MomentumEvidence(MomentumStatus.POSITIVE, Decimal("2"))
    volume = VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.1"))

    first = TechnicalAnalysisResult(stock_id, Timeframe.DAILY, trend, support_resistance, momentum, volume)
    second = TechnicalAnalysisResult(stock_id, Timeframe.DAILY, trend, support_resistance, momentum, volume)

    assert first == second
