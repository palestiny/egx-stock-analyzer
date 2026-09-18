from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.application.analysis.stock_analysis import StockAnalysisResult
from app.domain.entry_analysis.context import EntryContext
from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.fundamental_analysis.growth import GrowthEvidence, GrowthStatus
from app.domain.fundamental_analysis.liquidity import LiquidityEvidence, LiquidityStatus
from app.domain.fundamental_analysis.profitability import (
    ProfitabilityEvidence,
    ProfitabilityStatus,
)
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.fundamental_analysis.scoring import (
    FundamentalScore,
    ScoreContribution,
)
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.opportunity.classification import (
    OpportunityClassification,
    OpportunityClassificationResult,
)
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.scoring import TechnicalScore
from app.domain.technical_analysis.support_resistance import (
    SupportResistanceEvidence,
)
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
from app.infrastructure.persistence.analysis_result_serializer import (
    AnalysisResultSerializationError,
    deserialize_analysis_result,
    serialize_analysis_result,
)
from app.infrastructure.persistence.sqlite_analysis_result_store import (
    SQLiteAnalysisResultStore,
)


def make_result():
    stock_id = uuid4()
    technical = TechnicalAnalysisResult(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        trend=TrendEvidence(TrendStatus.UPTREND),
        support_resistance=SupportResistanceEvidence((), ()),
        momentum=MomentumEvidence(MomentumStatus.POSITIVE, Decimal("2.5")),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.25")),
    )
    fundamental = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 9, 17),
        profitability=ProfitabilityEvidence(
            ProfitabilityStatus.PROFITABLE,
            Decimal("0.15"),
        ),
        liquidity=LiquidityEvidence(
            LiquidityStatus.ABOVE_ONE,
            Decimal("1.8"),
        ),
        growth=GrowthEvidence(GrowthStatus.POSITIVE, Decimal("0.2")),
    )
    technical_score = TechnicalScore(1, 1, 1, 3)
    fundamental_score = FundamentalScore(
        total=3,
        contributions=(
            ScoreContribution("profitability", 1),
            ScoreContribution("liquidity", 1),
            ScoreContribution("growth", 1),
        ),
    )
    stock_quality = StockQualityScore(
        fundamental_score=fundamental_score,
        technical_score=technical_score,
        total_score=6,
    )
    entry_quality = EntryQualityScore(1, 1, 2)

    return StockAnalysisResult(
        technical_analysis=technical,
        fundamental_analysis=fundamental,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        stock_quality=stock_quality,
        entry_context=EntryContext(
            current_price=Price(Decimal("350.5")),
            nearest_support=None,
            nearest_resistance=None,
        ),
        entry_quality=entry_quality,
        opportunity=OpportunityClassificationResult(
            OpportunityClassification.BUY
        ),
    )


def test_serializer_round_trips_complete_analysis_result():
    result = make_result()

    restored = deserialize_analysis_result(serialize_analysis_result(result))

    assert restored == result


def test_serializer_rejects_unsupported_version():
    result = serialize_analysis_result(make_result())

    import json

    document = json.loads(result)
    document["version"] = 999

    import pytest

    with pytest.raises(AnalysisResultSerializationError):
        deserialize_analysis_result(json.dumps(document))


def test_sqlite_store_round_trips_result_and_analysis_date(tmp_path):
    database_path = tmp_path / "analysis.db"
    result = make_result()
    analysis_date = date(2026, 9, 18)

    store = SQLiteAnalysisResultStore(database_path)
    store.save("EGAL", result, analysis_date)

    restored_store = SQLiteAnalysisResultStore(database_path)
    record = restored_store.get_record("EGAL")

    assert record is not None
    assert record.result == result
    assert record.analysis_date == analysis_date


def test_sqlite_store_replaces_latest_result_for_symbol(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    first = make_result()
    second = make_result()

    store.save("EGAL", first, date(2026, 9, 17))
    store.save("EGAL", second, date(2026, 9, 18))

    record = store.get_record("EGAL")

    assert record is not None
    assert record.result == second
    assert record.analysis_date == date(2026, 9, 18)


def test_sqlite_store_returns_none_for_missing_symbol(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")

    assert store.get_record("UNKNOWN") is None
