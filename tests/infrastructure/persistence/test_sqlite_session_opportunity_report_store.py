from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.reporting.session_opportunity_ledger import (
    SessionOpportunityEntry,
    SessionOpportunityLedgerReport,
)
from app.domain.signals.model import SignalStatus
from app.domain.signals.outcome import SignalOutcome
from app.infrastructure.persistence.sqlite_session_opportunity_report_store import (
    SQLiteSessionOpportunityReportStore,
)


def report(
    generated_at: datetime,
    *,
    unresolved_count: int = 0,
    opportunities: tuple[SessionOpportunityEntry, ...] = (),
) -> SessionOpportunityLedgerReport:
    items = tuple(opportunities)
    return SessionOpportunityLedgerReport(
        session_date=date(2026, 10, 26),
        generated_at=generated_at,
        exchange_timezone="Africa/Cairo",
        methodology_version="session-opportunity-ledger-v1",
        opportunities=items,
        unresolved_count=unresolved_count,
        resolved_proxy_count=sum(
            item.market_proxy_outcome is not None for item in items
        ),
    )


def test_session_report_store_persists_immutable_idempotent_snapshots(tmp_path) -> None:
    store = SQLiteSessionOpportunityReportStore(tmp_path / "reports.db")
    generated = datetime(2026, 10, 26, 15, tzinfo=timezone.utc)
    item = report(generated)

    assert store.save(item) is True
    assert store.save(item) is False
    saved = store.get_latest(date(2026, 10, 26), as_of=generated)
    assert saved is not None
    assert saved["session_date"] == "2026-10-26"
    assert saved["generated_at"] == generated.isoformat()
    assert saved["methodology_version"] == "session-opportunity-ledger-v1"
    assert saved["total_count"] == 0
    assert saved["unresolved_count"] == 0
    assert saved["resolved_proxy_count"] == 0
    assert saved["opportunities"] == []
    assert all(value == 0 for value in saved["status_counts"].values())


def test_session_report_store_is_idempotent_for_equivalent_timezone_offsets(tmp_path) -> None:
    store = SQLiteSessionOpportunityReportStore(tmp_path / "reports.db")
    utc_generated = datetime(2026, 10, 26, 15, tzinfo=timezone.utc)
    equivalent_offset = datetime.fromisoformat("2026-10-26T17:00:00+02:00")

    assert utc_generated == equivalent_offset
    assert store.save(report(utc_generated)) is True
    assert store.save(report(equivalent_offset)) is False

    saved = store.get_latest(date(2026, 10, 26), as_of=utc_generated)
    assert saved is not None
    assert saved["generated_at"] == utc_generated.isoformat()


def test_session_report_store_concurrent_duplicate_saves_are_idempotent(tmp_path) -> None:
    database = tmp_path / "reports.db"
    generated = datetime(2026, 10, 26, 15, tzinfo=timezone.utc)
    item = report(generated)
    stores = [SQLiteSessionOpportunityReportStore(database) for _ in range(8)]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda store: store.save(item), stores))

    assert results.count(True) == 1
    assert results.count(False) == 7
    saved = stores[0].get_latest(date(2026, 10, 26), as_of=generated)
    assert saved is not None
    assert saved["generated_at"] == generated.isoformat()


def test_session_report_store_supports_point_in_time_reads(tmp_path) -> None:
    store = SQLiteSessionOpportunityReportStore(tmp_path / "reports.db")
    generated = datetime(2026, 10, 26, 15, tzinfo=timezone.utc)
    store.save(report(generated))

    assert store.get_latest(date(2026, 10, 26), as_of=datetime(2026, 10, 26, 14, tzinfo=timezone.utc)) is None
    assert store.get_latest(date(2026, 10, 26), as_of=generated) is not None


def test_session_report_store_rejects_conflicting_immutable_snapshot(tmp_path) -> None:
    store = SQLiteSessionOpportunityReportStore(tmp_path / "reports.db")
    generated = datetime(2026, 10, 26, 15, tzinfo=timezone.utc)
    store.save(report(generated))

    with pytest.raises(ValueError, match="immutable"):
        store.save(report(generated, unresolved_count=1))


def test_session_report_store_rejects_naive_timestamps(tmp_path) -> None:
    store = SQLiteSessionOpportunityReportStore(tmp_path / "reports.db")
    with pytest.raises(ValueError, match="timezone-aware"):
        store.get_latest(date(2026, 10, 26), as_of=datetime(2026, 10, 26))



def test_session_report_store_persists_source_and_outcome_data_timestamps(tmp_path) -> None:
    store = SQLiteSessionOpportunityReportStore(tmp_path / "reports.db")
    generated = datetime(2026, 10, 26, 15, tzinfo=timezone.utc)
    source_timestamp = datetime(2026, 10, 26, 7, tzinfo=timezone.utc)
    outcome_timestamp = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    opportunity = SessionOpportunityEntry(
        signal_id=uuid4(),
        symbol="EGAL",
        publication_time=datetime(2026, 10, 26, 8, tzinfo=timezone.utc),
        original_entry_lower=Decimal("100"),
        original_entry_upper=Decimal("102"),
        original_invalidation=Decimal("95"),
        original_targets=(("T1", Decimal("110")),),
        current_status=SignalStatus.TRIGGERED,
        current_evidence=("breakout",),
        market_proxy_outcome=SignalOutcome.TARGET_HIT,
        market_proxy_return=Decimal("0.09"),
        market_proxy_r=Decimal("1.8"),
        outcome_observed_at=outcome_timestamp,
        source_data_timestamp=source_timestamp,
        outcome_data_timestamp=outcome_timestamp,
    )

    assert store.save(report(generated, opportunities=(opportunity,))) is True
    saved = store.get_latest(date(2026, 10, 26), as_of=generated)

    assert saved is not None
    saved_opportunity = saved["opportunities"][0]
    assert saved_opportunity["source_data_timestamp"] == source_timestamp.isoformat()
    assert saved_opportunity["outcome_data_timestamp"] == outcome_timestamp.isoformat()
