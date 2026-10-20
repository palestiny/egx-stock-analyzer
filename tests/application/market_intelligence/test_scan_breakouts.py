from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.market_intelligence.scan_breakouts import ScanBreakouts
from app.domain.entry_analysis.context import EntryContext
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import PriceLevelEvidence, SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus


def record(
    symbol,
    price,
    resistance,
    support,
    trend=TrendStatus.UPTREND,
    volume=VolumeStatus.ABOVE_AVERAGE,
    stock_quality=70,
):
    sid = uuid4()
    now = datetime.now(timezone.utc)
    result = SimpleNamespace(
        technical_analysis=TechnicalAnalysisResult(
            stock_id=sid,
            timeframe=Timeframe.DAILY,
            trend=TrendEvidence(trend),
            support_resistance=SupportResistanceEvidence(
                support_levels=(PriceLevelEvidence(Price(Decimal(str(support))), now),),
                resistance_levels=(PriceLevelEvidence(Price(Decimal(str(resistance))), now),),
            ),
            momentum=MomentumEvidence(MomentumStatus.POSITIVE, Decimal("2")),
            volume=VolumeEvidence(volume, Decimal("1.5")),
        ),
        entry_context=EntryContext(
            current_price=Price(Decimal(str(price))),
            nearest_support=PriceLevelEvidence(Price(Decimal(str(support))), now),
            nearest_resistance=PriceLevelEvidence(Price(Decimal(str(resistance))), now),
        ),
        stock_quality=SimpleNamespace(total_score=stock_quality),
    )
    store = InMemoryAnalysisResultStore()
    store.save(symbol, result)
    return store


def test_detects_upside_breakout_and_explains_quality_score():
    result = ScanBreakouts(record("COMI", 102, 100, 95)).execute(["COMI"])
    match = result.matches[0]

    assert match.status.value == "confirmed"
    assert match.direction.value == "upside"
    assert match.distance_percent == Decimal("2")
    assert match.score == 94
    assert "trigger_confirmed" in match.evidence
    assert "trend_aligned" in match.evidence
    assert "above_average_volume" in match.evidence


def test_detects_downside_breakout_and_aligns_downtrend():
    result = ScanBreakouts(
        record("COMI", 98, 100, 100, trend=TrendStatus.DOWNTREND)
    ).execute(["COMI"])
    match = next(item for item in result.matches if item.direction.value == "downside")

    assert match.status.value == "confirmed"
    assert "trend_aligned" in match.evidence
    assert match.score == 94


def test_candidate_near_resistance_has_lower_trigger_component():
    result = ScanBreakouts(
        record("COMI", "99.5", "100", "95")
    ).execute(["COMI"], tolerance_percent=Decimal("1"))
    match = next(item for item in result.matches if item.direction.value == "upside")

    assert match.status.value == "candidate"
    assert match.score == 84
    assert "near_trigger" in match.evidence


def test_quality_score_is_capped_and_clamps_stock_quality_input():
    score = ScanBreakouts._quality_score(
        confirmed=True,
        trend_aligned=True,
        volume_confirmed=True,
        stock_quality=150,
    )

    assert score == 100


def test_quality_score_penalizes_missing_confirmation_evidence():
    strong = ScanBreakouts._quality_score(
        confirmed=True,
        trend_aligned=True,
        volume_confirmed=True,
        stock_quality=70,
    )
    weak = ScanBreakouts._quality_score(
        confirmed=True,
        trend_aligned=False,
        volume_confirmed=False,
        stock_quality=70,
    )

    assert strong > weak
