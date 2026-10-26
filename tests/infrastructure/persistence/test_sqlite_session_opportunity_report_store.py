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
    assert store.get_latest(date(2026, 10, 26), as_of=generated) == {
        "session_date": "2026-10-26",
        "generated_at": generated.isoformat(),
        "exchange_timezone": "Africa/Cairo",
        "methodology_version": "session-opportunity-ledger-v1",
        "total_count": 0,
        "unresolved_count": 0,
        "resolved_proxy_count": 0,
        "status_counts": {},
        "opportunities": [],
    }


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
