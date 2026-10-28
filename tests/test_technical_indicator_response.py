from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.api.technical_indicator_response import TechnicalIndicatorHistoryResponse
from app.domain.technical_analysis.elliott import (
    ElliottDirection,
    ElliottImpulseCandidate,
    ElliottCorrectionCandidate,
    ElliottCorrectionCount,
    ElliottWaveCount,
)
from app.domain.technical_analysis.indicator_evidence import (
    TechnicalIndicatorEvidence,
    TechnicalIndicatorPoint,
)
from app.domain.market_data.timeframe import Timeframe


def point(day: int) -> TechnicalIndicatorPoint:
    return TechnicalIndicatorPoint(
        timestamp=datetime(2026, 10, day, tzinfo=timezone.utc),
        close=Decimal("10"),
        sma_20=None, sma_50=None, sma_200=None,
        ema_9=None, ema_20=None, ema_50=None, ema_200=None,
        rsi_14=None, macd_line=None, macd_signal=None, macd_histogram=None,
        bollinger_upper=None, bollinger_middle=None, bollinger_lower=None,
        atr_14=None, stochastic_k_14=None, stochastic_d_3=None,
        cci_20=None, obv=0, mfi_14=None, plus_di_14=None, minus_di_14=None,
        adx_14=None, ichimoku_conversion_9=None, ichimoku_base_26=None,
        ichimoku_span_a_unshifted=None, ichimoku_span_b_unshifted=None,
        candlestick_patterns=("doji",),
    )


def report():
    evidence = TechnicalIndicatorEvidence((point(1), point(2), point(3)))
    technical = SimpleNamespace(timeframe=Timeframe.DAILY, indicators=evidence)
    return SimpleNamespace(stock_symbol="EGAL", technical_analysis=technical)


def test_response_limits_points_and_preserves_decimal_precision_as_strings() -> None:
    response = TechnicalIndicatorHistoryResponse.from_report(report(), limit=2)
    assert response["symbol"] == "EGAL"
    assert response["returned_points"] == 2
    assert response["total_points"] == 3
    assert response["points"][0]["close"] == "10"
    assert response["points"][0]["timestamp"] == "2026-10-02T00:00:00+00:00"


def test_response_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="between 1 and 1000"):
        TechnicalIndicatorHistoryResponse.from_report(report(), limit=1001)

def test_response_exposes_elliott_rule_diagnostics_and_invalidation_level() -> None:
    candidate = ElliottWaveCount(
        start_index=2,
        end_index=17,
        candidate=ElliottImpulseCandidate(
            ElliottDirection.UP,
            (
                Decimal("10"),
                Decimal("20"),
                Decimal("13"),
                Decimal("25"),
                Decimal("22"),
                Decimal("30"),
            ),
        ),
    )
    analysis = report()
    analysis.technical_analysis.indicators = TechnicalIndicatorEvidence(
        (replace(point(1), elliott_candidates=(candidate,)),)
    )

    response = TechnicalIndicatorHistoryResponse.from_report(analysis)
    item = response["points"][0]["elliott_candidates"][0]
    assert item["is_rule_consistent"] is True
    assert item["rule_violations"] == []
    assert item["wave_two_invalidation_price"] == "10"



def test_response_exposes_elliott_abc_correction_diagnostics() -> None:
    correction = ElliottCorrectionCount(
        start_index=3,
        end_index=12,
        candidate=ElliottCorrectionCandidate(
            ElliottDirection.DOWN,
            (
                Decimal("30"),
                Decimal("20"),
                Decimal("25"),
                Decimal("15"),
            ),
        ),
    )
    analysis = report()
    analysis.technical_analysis.indicators = TechnicalIndicatorEvidence(
        (replace(point(1), elliott_corrections=(correction,)),)
    )

    response = TechnicalIndicatorHistoryResponse.from_report(analysis)
    item = response["points"][0]["elliott_corrections"][0]
    assert item["is_rule_consistent"] is True
    assert item["rule_violations"] == []
    assert item["wave_b_origin_boundary_price"] == "30"
    assert item["candidate"]["points"] == ["30", "20", "25", "15"]
