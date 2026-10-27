from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest

from app.domain.reporting.session_opportunity_ledger import SessionOpportunityLedgerReport
from app.infrastructure.persistence.sqlite_session_opportunity_report_store import (
    SQLiteSessionOpportunityReportStore,
)


def report(generated_at: datetime, *, unresolved_count: int = 0) -> SessionOpportunityLedgerReport:
    return SessionOpportunityLedgerReport(
        session_date=date(2026, 10, 26),
        generated_at=generated_at,
        exchange_timezone="Africa/Cairo",
        methodology_version="session-opportunity-ledger-v1",
        opportunities=(),
        unresolved_count=unresolved_count,
        resolved_proxy_count=0,
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
