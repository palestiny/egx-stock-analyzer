from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.orchestrator import TechnicalAnalysisOrchestrator
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus


def create_price_bar(stock_id, day, price, volume):
    timestamp = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(days=day)
    value = Price(Decimal(str(price)))
    return PriceBar(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Volume(volume),
    )


# Tests that the orchestrator composes evidence from all current technical analyzers.
# This exists because the orchestrator is the composition boundary for Technical Analysis.
# Its function is to prove the individual analyzers remain the producers of evidence.
def test_orchestrator_composes_all_evidence():
    stock_id = uuid4()
    price_bars = [create_price_bar(stock_id, day, 100 + day, 100) for day in range(6)]

    trend = TrendEvidence(TrendStatus.UPTREND)
    support_resistance = SupportResistanceEvidence((), ())
    momentum = MomentumEvidence(MomentumStatus.POSITIVE, Decimal("5"))
    volume = VolumeEvidence(VolumeStatus.EQUAL_TO_AVERAGE, Decimal("1"))

    with patch("app.domain.technical_analysis.orchestrator.TrendAnalyzer") as trend_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.SupportResistanceAnalyzer") as sr_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.MomentumAnalyzer") as momentum_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.VolumeAnalyzer") as volume_analyzer:
        trend_analyzer.analyze.return_value = trend
        sr_analyzer.analyze.return_value = support_resistance
        momentum_analyzer.analyze.return_value = momentum
        volume_analyzer.analyze.return_value = volume

        result = TechnicalAnalysisOrchestrator.analyze(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            price_bars=price_bars,
            momentum_lookback=3,
            volume_lookback=2,
        )

    assert isinstance(result, TechnicalAnalysisResult)
    assert result.stock_id == stock_id
    assert result.timeframe is Timeframe.DAILY
    assert result.trend == trend
    assert result.support_resistance == support_resistance
    assert result.momentum == momentum
    assert result.volume == volume


# Tests that Momentum and Volume receive independent lookback configuration.
# This exists because the two analyzers have different analytical semantics.
# Its function is to prevent the orchestrator from silently coupling their lookback periods.
def test_orchestrator_passes_independent_lookbacks():
    stock_id = uuid4()
    price_bars = [create_price_bar(stock_id, day, 100, 100) for day in range(6)]

    with patch("app.domain.technical_analysis.orchestrator.TrendAnalyzer") as trend_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.SupportResistanceAnalyzer") as sr_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.MomentumAnalyzer") as momentum_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.VolumeAnalyzer") as volume_analyzer:
        trend_analyzer.analyze.return_value = TrendEvidence(TrendStatus.SIDEWAYS)
        sr_analyzer.analyze.return_value = SupportResistanceEvidence((), ())
        momentum_analyzer.analyze.return_value = MomentumEvidence(MomentumStatus.NEUTRAL)
        volume_analyzer.analyze.return_value = VolumeEvidence(VolumeStatus.EQUAL_TO_AVERAGE)

        TechnicalAnalysisOrchestrator.analyze(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            price_bars=price_bars,
            momentum_lookback=5,
            volume_lookback=2,
        )

    momentum_analyzer.analyze.assert_called_once_with(
        stock_id,
        Timeframe.DAILY,
        price_bars,
        5,
    )
    volume_analyzer.analyze.assert_called_once_with(
        stock_id,
        Timeframe.DAILY,
        price_bars,
        2,
    )


# Tests that insufficient evidence remains isolated to the analyzer that lacks enough data.
# This exists because DEC-030 requires independent data-sufficiency semantics.
# Its function is to prove the orchestrator does not reject the complete result.
def test_orchestrator_preserves_independent_insufficient_states():
    stock_id = uuid4()
    price_bars = [create_price_bar(stock_id, day, 100, 100) for day in range(2)]

    with patch("app.domain.technical_analysis.orchestrator.TrendAnalyzer") as trend_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.SupportResistanceAnalyzer") as sr_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.MomentumAnalyzer") as momentum_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.VolumeAnalyzer") as volume_analyzer:
        trend_analyzer.analyze.return_value = TrendEvidence(TrendStatus.INSUFFICIENT_DATA)
        sr_analyzer.analyze.return_value = SupportResistanceEvidence((), ())
        momentum_analyzer.analyze.return_value = MomentumEvidence(MomentumStatus.INSUFFICIENT_DATA)
        volume_analyzer.analyze.return_value = VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.2"))

        result = TechnicalAnalysisOrchestrator.analyze(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            price_bars=price_bars,
            momentum_lookback=5,
            volume_lookback=2,
        )

    assert result.trend.status is TrendStatus.INSUFFICIENT_DATA
    assert result.momentum.status is MomentumStatus.INSUFFICIENT_DATA
    assert result.volume.status is VolumeStatus.ABOVE_AVERAGE


# Tests that repeated orchestration with the same evidence is deterministic.
# This exists because Technical Analysis must be reproducible for the same inputs and configuration.
# Its function is to protect the composition boundary from hidden state.
def test_orchestrator_is_deterministic():
    stock_id = uuid4()
    price_bars = [create_price_bar(stock_id, day, 100, 100) for day in range(6)]

    with patch("app.domain.technical_analysis.orchestrator.TrendAnalyzer") as trend_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.SupportResistanceAnalyzer") as sr_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.MomentumAnalyzer") as momentum_analyzer, \
         patch("app.domain.technical_analysis.orchestrator.VolumeAnalyzer") as volume_analyzer:
        trend_analyzer.analyze.return_value = TrendEvidence(TrendStatus.SIDEWAYS)
        sr_analyzer.analyze.return_value = SupportResistanceEvidence((), ())
        momentum_analyzer.analyze.return_value = MomentumEvidence(MomentumStatus.NEUTRAL, Decimal("0"))
        volume_analyzer.analyze.return_value = VolumeEvidence(VolumeStatus.EQUAL_TO_AVERAGE, Decimal("1"))

        first = TechnicalAnalysisOrchestrator.analyze(
            stock_id, Timeframe.DAILY, price_bars, 3, 2
        )
        second = TechnicalAnalysisOrchestrator.analyze(
            stock_id, Timeframe.DAILY, price_bars, 3, 2
        )

    assert first == second
