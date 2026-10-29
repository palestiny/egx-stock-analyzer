from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.signals.generate_signal import GenerateSignal
from app.domain.entry_analysis.context import EntryContext
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import (
    PriceLevelEvidence,
    SupportResistanceEvidence,
)
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus


SOURCE_TIMESTAMP = datetime(2026, 10, 3, 12, 30, tzinfo=timezone.utc)


def make_store(data_timestamp=SOURCE_TIMESTAMP):
    sid = uuid4()
    now = SOURCE_TIMESTAMP
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
        data_timestamp=data_timestamp,
    )
    store = InMemoryAnalysisResultStore()
    store.save("COMI", result, analysis_date=date(2026, 10, 3))
    return store


def test_generates_buy_signal_preserving_source_bar_timestamp():
    signal = GenerateSignal(make_store()).execute("COMI")
    assert signal is not None
    assert signal.direction.value == "BUY"
    assert signal.status.value == "ACTIVE"
    assert signal.invalidation == Decimal("95")
    assert signal.targets[0].price == Decimal("109")
    assert signal.data_timestamp == SOURCE_TIMESTAMP
    assert signal.generated_at != signal.data_timestamp


def test_no_signal_when_trend_is_not_breakout_aligned():
    store = make_store()
    record = store.get_record("COMI")
    record.result.technical_analysis = SimpleNamespace(
        trend=TrendEvidence(TrendStatus.SIDEWAYS),
        timeframe=Timeframe.DAILY,
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.5")),
    )
    assert GenerateSignal(store).execute("COMI") is None


def test_does_not_generate_signal_from_undated_analysis_snapshot():
    dated_store = make_store()
    record = dated_store.get_record("COMI")
    assert record is not None
    undated_store = InMemoryAnalysisResultStore()
    undated_store.save(
        "COMI",
        record.result,
        analysis_date=None,
    )

    assert GenerateSignal(undated_store).execute("COMI") is None


def test_does_not_generate_signal_without_source_timestamp():
    assert GenerateSignal(make_store(data_timestamp=None)).execute("COMI") is None


def test_does_not_generate_signal_with_naive_source_timestamp():
    naive_timestamp = datetime(2026, 10, 3, 12, 30)
    assert GenerateSignal(make_store(data_timestamp=naive_timestamp)).execute("COMI") is None
