import sqlite3
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

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


def test_sqlite_store_preserves_multiple_historical_snapshots(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    first = make_result()
    second = make_result()

    store.save("EGAL", first, date(2026, 9, 17))
    store.save("EGAL", second, date(2026, 9, 18))

    history = store.get_history("EGAL")

    assert len(history) == 2
    assert history[0].result == second
    assert history[0].analysis_date == date(2026, 9, 18)
    assert history[1].result == first
    assert history[1].analysis_date == date(2026, 9, 17)
    assert history[0].snapshot_id != history[1].snapshot_id


def test_sqlite_store_allows_multiple_snapshots_on_same_date(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    first = make_result()
    second = make_result()

    analysis_date = date(2026, 9, 18)
    store.save("EGAL", first, analysis_date)
    store.save("EGAL", second, analysis_date)

    history = store.get_history("EGAL")

    assert len(history) == 2
    assert {record.analysis_date for record in history} == {analysis_date}
    assert history[0].snapshot_id < history[1].snapshot_id


def test_sqlite_store_history_supports_inclusive_date_bounds(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    store.save("EGAL", make_result(), date(2026, 9, 16))
    store.save("EGAL", make_result(), date(2026, 9, 17))
    store.save("EGAL", make_result(), date(2026, 9, 18))

    history = store.get_history(
        "EGAL",
        start_date=date(2026, 9, 17),
        end_date=date(2026, 9, 18),
    )

    assert [record.analysis_date for record in history] == [
        date(2026, 9, 18),
        date(2026, 9, 17),
    ]


def test_sqlite_store_latest_result_is_derived_from_history(tmp_path):
    database_path = tmp_path / "analysis.db"
    store = SQLiteAnalysisResultStore(database_path)

    store.save("EGAL", make_result(), date(2026, 9, 17))
    store.save("EGAL", make_result(), date(2026, 9, 18))

    latest = store.get_record("EGAL")
    history = store.get_history("EGAL")

    assert latest == history[0]


def test_sqlite_store_migrates_existing_latest_only_row(tmp_path):
    import sqlite3

    database_path = tmp_path / "analysis.db"
    result = make_result()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE analysis_results (
                symbol TEXT PRIMARY KEY,
                analysis_date TEXT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO analysis_results (symbol, analysis_date, payload)
            VALUES (?, ?, ?)
            """,
            ("EGAL", date(2026, 9, 18).isoformat(), serialize_analysis_result(result)),
        )

    store = SQLiteAnalysisResultStore(database_path)

    history = store.get_history("EGAL")

    assert len(history) == 1
    assert history[0].result == result
    assert history[0].analysis_date == date(2026, 9, 18)
    assert history[0].snapshot_id is not None


def test_sqlite_store_history_survives_store_recreation(tmp_path):
    database_path = tmp_path / "analysis.db"
    store = SQLiteAnalysisResultStore(database_path)
    store.save("EGAL", make_result(), date(2026, 9, 17))
    store.save("EGAL", make_result(), date(2026, 9, 18))

    restored = SQLiteAnalysisResultStore(database_path)

    assert len(restored.get_history("EGAL")) == 2


def test_sqlite_store_gets_snapshot_by_id(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    result = make_result()
    store.save("EGAL", result, date(2026, 9, 18))

    saved = store.get_history("EGAL")[0]
    restored = store.get_snapshot(saved.snapshot_id)

    assert restored == saved
    assert restored.symbol == "EGAL"


def test_sqlite_store_returns_none_for_missing_snapshot(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")

    assert store.get_snapshot(uuid4()) is None


def test_sqlite_store_gets_snapshot_by_uuid_and_preserves_symbol(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    store.save("EGAL", make_result(), date(2026, 9, 18))

    snapshot = store.get_history("EGAL")[0]
    restored = store.get_snapshot(snapshot.snapshot_id)

    assert restored == snapshot
    assert restored is not None
    assert restored.symbol == "EGAL"



def test_snapshot_can_be_correlated_to_analysis_run(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    result = make_result()
    run_id = uuid4()

    store.save("EGAL", result, date(2026, 9, 20), run_id)

    record = store.get_record("EGAL")

    assert record is not None
    assert record.analysis_run_id == run_id


def test_legacy_snapshot_without_analysis_run_remains_readable(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    result = make_result()

    store.save("EGAL", result, date(2026, 9, 20))

    record = store.get_record("EGAL")

    assert record is not None
    assert record.analysis_run_id is None


def test_one_snapshot_per_symbol_per_analysis_run_is_enforced(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    result = make_result()
    run_id = uuid4()

    store.save("EGAL", result, date(2026, 9, 20), run_id)

    with pytest.raises(sqlite3.IntegrityError):
        store.save("EGAL", result, date(2026, 9, 20), run_id)


def test_sqlite_store_persists_snapshot_owner_and_supports_owner_scoped_latest(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    result = make_result()
    owner_id = uuid4()
    other_owner_id = uuid4()

    store.save("EGAL", result, date(2026, 9, 18), owner_user_id=owner_id)
    store.save("EGAL", make_result(), date(2026, 9, 19), owner_user_id=other_owner_id)

    owner_record = store.get_record("EGAL", owner_user_id=owner_id)
    other_record = store.get_record("EGAL", owner_user_id=other_owner_id)

    assert owner_record is not None
    assert owner_record.owner_user_id == owner_id
    assert other_record is not None
    assert other_record.owner_user_id == other_owner_id


def test_sqlite_store_operator_scope_can_read_all_snapshot_owners(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    first_owner = uuid4()
    second_owner = uuid4()

    store.save("EGAL", make_result(), date(2026, 9, 18), owner_user_id=first_owner)
    store.save("EGAL", make_result(), date(2026, 9, 19), owner_user_id=second_owner)

    history = store.get_history("EGAL")

    assert [record.owner_user_id for record in history] == [
        second_owner,
        first_owner,
    ]


def test_sqlite_store_owner_scoped_history_excludes_other_users(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    owner_id = uuid4()
    other_owner_id = uuid4()

    store.save("EGAL", make_result(), date(2026, 9, 18), owner_user_id=owner_id)
    store.save("EGAL", make_result(), date(2026, 9, 19), owner_user_id=other_owner_id)

    history = store.get_history("EGAL", owner_user_id=owner_id)

    assert len(history) == 1
    assert history[0].owner_user_id == owner_id


def test_sqlite_store_owner_scoped_snapshot_lookup_hides_other_users(tmp_path):
    store = SQLiteAnalysisResultStore(tmp_path / "analysis.db")
    owner_id = uuid4()
    other_owner_id = uuid4()

    store.save("EGAL", make_result(), date(2026, 9, 18), owner_user_id=owner_id)
    snapshot = store.get_history("EGAL")[0]

    assert store.get_snapshot(snapshot.snapshot_id, owner_user_id=other_owner_id) is None
    assert store.get_snapshot(snapshot.snapshot_id, owner_user_id=owner_id) == snapshot
