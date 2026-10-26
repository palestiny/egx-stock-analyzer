from datetime import datetime, timezone
import sqlite3

import pytest

from app.infrastructure.persistence.sqlite_owner_dashboard_read_store import (
    SQLiteOwnerDashboardReadStore,
)


def test_owner_dashboard_reports_missing_features_as_unavailable(tmp_path) -> None:
    store = SQLiteOwnerDashboardReadStore(tmp_path / "empty.db")
    result = store.snapshot(as_of=datetime(2026, 10, 26, tzinfo=timezone.utc))

    assert result["availability"]["telegram_outbox"] is False
    assert result["availability"]["subscriptions"] is False
    assert result["counts"]["telegram_outbox_by_status"] is None
    assert result["counts"]["news_events"] is None
    assert result["availability"]["session_reports"] is False
    assert result["availability"]["payment_reconciliation"] is False


def test_owner_dashboard_returns_aggregate_counts_without_personal_fields(tmp_path) -> None:
    path = tmp_path / "owner.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE signal_alert_outbox (
                event_id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at TEXT NOT NULL
            );
            INSERT INTO signal_alert_outbox VALUES ('event-1', 'PENDING', '2026-10-26T10:00:00+00:00');
            INSERT INTO signal_alert_outbox VALUES ('event-2', 'DELIVERED', '2026-10-26T11:00:00+00:00');
            CREATE TABLE signal_alert_deliveries (
                event_id TEXT, user_id TEXT, channel TEXT, status TEXT
            );
            INSERT INTO signal_alert_deliveries VALUES ('event-1', 'user-private', 'telegram', 'FAILED');
            INSERT INTO signal_alert_deliveries VALUES ('event-2', 'user-private', 'telegram', 'DELIVERED');
            CREATE TABLE subscriptions (subscription_id TEXT, user_id TEXT, status TEXT);
            INSERT INTO subscriptions VALUES ('sub-1', 'user-private', 'ACTIVE');
            CREATE TABLE telegram_account_links (user_id TEXT, chat_id TEXT, linked_at TEXT);
            INSERT INTO telegram_account_links VALUES ('user-private', 'private-chat-id', '2026-10-26T09:00:00+00:00');
            CREATE TABLE news_events (event_id TEXT PRIMARY KEY);
            INSERT INTO news_events VALUES ('news-1');
            """
        )

    result = SQLiteOwnerDashboardReadStore(path).snapshot(
        as_of=datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    )

    assert result["counts"]["telegram_outbox_by_status"] == {"DELIVERED": 1, "PENDING": 1}
    assert result["counts"]["telegram_deliveries_by_status"] == {"DELIVERED": 1, "FAILED": 1}
    assert result["counts"]["subscriptions_by_status"] == {"ACTIVE": 1}
    assert result["counts"]["linked_telegram_accounts"] == 1
    assert result["counts"]["news_events"] == 1
    assert result["counts"]["oldest_pending_outbox_created_at"] == "2026-10-26T10:00:00+00:00"
    serialized = repr(result)
    assert "private-chat-id" not in serialized
    assert "user-private" not in serialized


def test_owner_dashboard_rejects_naive_cutoff(tmp_path) -> None:
    store = SQLiteOwnerDashboardReadStore(tmp_path / "empty.db")
    with pytest.raises(ValueError, match="timezone-aware"):
        store.snapshot(as_of=datetime(2026, 10, 26))
