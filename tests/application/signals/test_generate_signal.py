from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.signals.generate_signal import GenerateSignal
from app.domain.entry_analysis.context import EntryContext
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import PriceLevelEvidence
from app.domain.technical_analysis.support_resistance import SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
from datetime import datetime, timezone


def make_store():
    sid = uuid4()
    now = datetime.now(timezone.utc)
    support = PriceLevelEvidence(Price(Decimal("95")), now)
    resistance = PriceLevelEvidence(Price(Decimal("100")), now)
    result = SimpleNamespace(
        technical_analysis=TechnicalAnalysisResult(
            stock_id=sid,
            timeframe=Timeframe.DAILY,
            trend=TrendEvidence(TrendStatus.UPTREND),
            support_resistance=SupportResistanceEvidence((support,), (resistance,)),
            momentum=MomentumEvidence(MomentumStatus.POSITIVE, Decimal("2")),
            volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.5")),
        ),
        entry_context=EntryContext(Price(Decimal("102")), support, resistance),
        stock_quality=SimpleNamespace(total_score=80),
    )
    store = InMemoryAnalysisResultStore()
    store.save("COMI", result, analysis_date=date(2026, 10, 3))
    return store


def test_generates_buy_signal_from_upside_breakout():
    signal = GenerateSignal(make_store()).execute("COMI")
    assert signal is not None
    assert signal.direction.value == "BUY"
    assert signal.status.value == "ACTIVE"
    assert signal.invalidation == Decimal("95")
    assert signal.targets[0].price == Decimal("109")


def test_no_signal_when_trend_is_not_breakout_aligned():
    store = make_store()
    record = store.get_record("COMI")
    record.result.technical_analysis = SimpleNamespace(
        trend=TrendEvidence(TrendStatus.SIDEWAYS),
        timeframe=Timeframe.DAILY,
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.5")),
    )
    assert GenerateSignal(store).execute("COMI") is None
