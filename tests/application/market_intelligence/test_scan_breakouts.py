from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.application.market_intelligence.scan_breakouts import ScanBreakouts
from app.domain.entry_analysis.context import EntryContext
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import PriceLevelEvidence, SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
from app.application.analysis.result_store import InMemoryAnalysisResultStore


def record(symbol, price, resistance, support, trend=TrendStatus.UPTREND, volume=VolumeStatus.ABOVE_AVERAGE):
    sid = uuid4()
    result = SimpleNamespace(
        technical_analysis=TechnicalAnalysisResult(
            stock_id=sid,
            timeframe=Timeframe.DAILY,
            trend=TrendEvidence(trend),
            support_resistance=SupportResistanceEvidence(
                support_levels=(PriceLevelEvidence(Price(Decimal(str(support))), __import__("datetime").datetime.now(__import__("datetime").timezone.utc),),),
                resistance_levels=(PriceLevelEvidence(Price(Decimal(str(resistance))), __import__("datetime").datetime.now(__import__("datetime").timezone.utc),),),
            ),
            momentum=MomentumEvidence(MomentumStatus.POSITIVE, Decimal("2")),
            volume=VolumeEvidence(volume, Decimal("1.5")),
        ),
        entry_context=EntryContext(
            current_price=Price(Decimal(str(price))),
            nearest_support=PriceLevelEvidence(Price(Decimal(str(support))), __import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
            nearest_resistance=PriceLevelEvidence(Price(Decimal(str(resistance))), __import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
        ),
        stock_quality=SimpleNamespace(total_score=70),
    )
    store = InMemoryAnalysisResultStore()
    store.save(symbol, result)
    return store


def test_detects_upside_breakout():
    result = ScanBreakouts(record("COMI", 102, 100, 95)).execute(["COMI"])
    match = result.matches[0]
    assert match.status.value == "confirmed"
    assert match.direction.value == "upside"
    assert match.distance_percent == Decimal("2")


def test_detects_downside_breakout():
    result = ScanBreakouts(record("COMI", 98, 100, 100)).execute(["COMI"])
    match = result.matches[0]
    assert match.status.value == "confirmed"
    assert match.direction.value == "downside"


def test_candidate_near_resistance():
    result = ScanBreakouts(record("COMI", "99.5", "100", "95")).execute(["COMI"], tolerance_percent=Decimal("1"))
    match = result.matches[0]
    assert match.status.value == "candidate"
