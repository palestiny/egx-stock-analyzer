import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import date, datetime, timezone

import pytest

from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)


def calendar(version: str, day: int = 2) -> EGXSessionCalendar:
    return EGXSessionCalendar(
        version=version,
        timezone="Africa/Cairo",
        coverage_start=date(2026, 11, day),
        coverage_end=date(2026, 11, day),
        days=(
            EGXCalendarDay(date(2026, 11, day), CalendarDayStatus.NON_TRADING),
        ),
    )


def test_published_calendar_version_survives_repository_recreation(tmp_path):
    database = tmp_path / "calendar.db"
    repository = SQLiteSessionCalendarRepository(database)
    source = calendar("egx-2026-v1")
    published_at = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)

    stored = repository.publish(
        source,
        published_by="operator-1",
        source_reference="EGX notice 123",
        reason="Initial verified calendar",
        published_at=published_at,
    )

    recreated = SQLiteSessionCalendarRepository(database)
    loaded = recreated.get_version("egx-2026-v1")

    assert loaded == stored
    assert loaded.calendar == source
    assert len(loaded.sha256) == 64


def test_calendar_versions_are_immutable(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="publish",
    )

    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE egx_calendar_versions SET publication_reason = 'changed' "
                "WHERE version = 'egx-v1'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM egx_calendar_versions WHERE version = 'egx-v1'"
            )


def test_activation_and_rollback_are_audited_and_durable(tmp_path):
    database = tmp_path / "calendar.db"
    repository = SQLiteSessionCalendarRepository(database)
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="first version",
    )
    repository.publish(
        calendar("egx-v2", day=3),
        published_by="operator",
        source_reference="notice-2",
        reason="second version",
    )

    first = repository.activate(
        "egx-v1", performed_by="admin-1", reason="activate first"
    )
    second = repository.activate(
        "egx-v2", performed_by="admin-1", reason="activate second"
    )
    rollback = repository.rollback(
        "egx-v1", performed_by="admin-1", reason="restore known-good calendar"
    )

    recreated = SQLiteSessionCalendarRepository(database)
    assert recreated.get_active().version == "egx-v1"
    assert [event.action for event in recreated.list_activation_events()] == [
        "ACTIVATE", "ACTIVATE", "ROLLBACK"
    ]
    assert rollback.previous_version == "egx-v2"
    assert rollback.target_version == "egx-v1"
    assert first.event_id < second.event_id < rollback.event_id


def test_activation_fails_for_unknown_version_without_changing_active(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    with pytest.raises(KeyError, match="Unknown calendar version"):
        repository.activate(
            "missing", performed_by="admin", reason="should fail"
        )
    assert repository.get_active() is None
    assert repository.list_activation_events() == ()


def test_rollback_requires_previously_active_version(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="first version",
    )
    with pytest.raises(ValueError, match="previously"):
        repository.rollback(
            "egx-v1", performed_by="admin", reason="not previously active"
        )


def test_deactivation_is_audited_and_leaves_no_active_version(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="first version",
    )
    repository.activate("egx-v1", performed_by="admin", reason="enable")
    event = repository.deactivate(
        performed_by="admin", reason="source evidence withdrawn"
    )

    assert event.action == "DEACTIVATE"
    assert event.previous_version == "egx-v1"
    assert event.target_version is None
    assert repository.get_active() is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"published_by": "", "source_reference": "notice", "reason": "valid"},
        {"published_by": "operator", "source_reference": "", "reason": "valid"},
        {"published_by": "operator", "source_reference": "notice", "reason": " "},
    ],
)
def test_publication_requires_operator_provenance_and_reason(tmp_path, kwargs):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    with pytest.raises(ValueError):
        repository.publish(calendar("egx-v1"), **kwargs)


def test_publication_rejects_naive_timestamp(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    with pytest.raises(ValueError, match="timezone-aware"):
        repository.publish(
            calendar("egx-v1"),
            published_by="operator",
            source_reference="notice",
            reason="publish",
            published_at=datetime(2026, 11, 1, 12),
        )


def test_activation_events_are_append_only(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice",
        reason="publish",
    )
    repository.activate("egx-v1", performed_by="admin", reason="activate")

    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE egx_calendar_activation_events SET reason = 'rewritten' "
                "WHERE event_id = 1"
            )



def test_calendar_payload_integrity_is_verified_when_loaded(tmp_path):
    from app.infrastructure.persistence.sqlite_session_calendar_repository import (
        CalendarVersionIntegrityError,
    )

    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="publish",
    )

    with repository._connect() as connection:
        connection.execute("DROP TRIGGER egx_calendar_versions_no_update")
        connection.execute(
            "UPDATE egx_calendar_versions SET calendar_json = "
            "REPLACE(calendar_json, 'egx-v1', 'egx-v2') WHERE version = 'egx-v1'"
        )

    with pytest.raises(CalendarVersionIntegrityError, match="SHA-256 integrity check"):
        repository.get_version("egx-v1")


def test_calendar_payload_version_must_match_immutable_row_key(tmp_path):
    from app.infrastructure.persistence.sqlite_session_calendar_repository import (
        CalendarVersionIntegrityError,
    )

    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="publish",
    )

    with repository._connect() as connection:
        connection.execute("DROP TRIGGER egx_calendar_versions_no_update")
        connection.execute(
            "UPDATE egx_calendar_versions SET calendar_json = "
            "REPLACE(calendar_json, 'egx-v1', 'egx-v2'), sha256 = ? "
            "WHERE version = 'egx-v1'",
            (
                hashlib.sha256(
                    json.dumps(
                        {
                            "version": "egx-v2",
                            "timezone": "Africa/Cairo",
                            "coverage_start": "2026-11-02",
                            "coverage_end": "2026-11-02",
                            "days": [
                                {
                                    "date": "2026-11-02",
                                    "status": "NON_TRADING",
                                    "session_open": None,
                                    "session_close": None,
                                    "closed_at": None,
                                    "reason": None,
                                    "exceptional_hours": False,
                                }
                            ],
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
            ),
        )

    with pytest.raises(CalendarVersionIntegrityError, match="payload version"):
        repository.get_version("egx-v1")



def test_in_memory_calendar_database_survives_repository_connections():
    repository = SQLiteSessionCalendarRepository(":memory:")
    stored = repository.publish(
        calendar("memory-v1"),
        published_by="operator",
        source_reference="memory-test",
        reason="Verify shared in-memory persistence",
    )

    assert repository.get_version("memory-v1") == stored
    repository.activate(
        "memory-v1",
        performed_by="operator",
        reason="Verify in-memory active pointer",
    )
    assert repository.get_active() == stored

    isolated_repository = SQLiteSessionCalendarRepository(":memory:")
    assert isolated_repository.get_version("memory-v1") is None

    repository.close()
    repository.close()
    with pytest.raises(RuntimeError, match="repository is closed"):
        repository.get_version("memory-v1")
    isolated_repository.close()



def test_invalid_persisted_calendar_json_fails_closed(tmp_path):
    from app.infrastructure.persistence.sqlite_session_calendar_repository import (
        CalendarVersionIntegrityError,
    )

    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="publish",
    )

    with repository._connect() as connection:
        connection.execute("DROP TRIGGER egx_calendar_versions_no_update")
        connection.execute(
            "UPDATE egx_calendar_versions SET calendar_json = ? WHERE version = ?",
            ("{invalid-json", "egx-v1"),
        )

    with pytest.raises(CalendarVersionIntegrityError, match="invalid JSON"):
        repository.get_version("egx-v1")


def test_concurrent_activation_attempts_serialize_and_audit_once(tmp_path):
    database = tmp_path / "calendar.db"
    first_repository = SQLiteSessionCalendarRepository(database)
    second_repository = SQLiteSessionCalendarRepository(database)
    first_repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="publish",
    )
    barrier = Barrier(2)

    def activate(repository):
        barrier.wait()
        try:
            return repository.activate(
                "egx-v1",
                performed_by="operator",
                reason="concurrent activation test",
            )
        except ValueError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(activate, (first_repository, second_repository))
        )

    assert sum(not isinstance(result, ValueError) for result in results) == 1
    assert sum(isinstance(result, ValueError) for result in results) == 1
    assert first_repository.get_active().version == "egx-v1"
    assert len(first_repository.list_activation_events()) == 1



def test_deactivation_without_active_calendar_is_rejected_without_audit(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")

    with pytest.raises(ValueError, match="no calendar version is active"):
        repository.deactivate(
            performed_by="operator",
            reason="There is nothing to deactivate",
        )

    assert repository.get_active() is None
    assert repository.list_activation_events() == ()


def test_failed_rollback_preserves_active_version_and_audit_history(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="first version",
    )
    repository.publish(
        calendar("egx-v2", day=3),
        published_by="operator",
        source_reference="notice-2",
        reason="second version",
    )
    repository.activate(
        "egx-v2",
        performed_by="operator",
        reason="activate second version",
    )
    before_events = repository.list_activation_events()

    with pytest.raises(ValueError, match="previously active"):
        repository.rollback(
            "egx-v1",
            performed_by="operator",
            reason="reject unactivated rollback target",
        )

    assert repository.get_active().version == "egx-v2"
    assert repository.list_activation_events() == before_events


def test_activation_event_deletion_is_rejected(tmp_path):
    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="publish",
    )
    repository.activate(
        "egx-v1",
        performed_by="operator",
        reason="activate",
    )

    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM egx_calendar_activation_events WHERE event_id = 1"
            )



def test_corrupt_calendar_cannot_be_activated_or_audited(tmp_path):
    from app.infrastructure.persistence.sqlite_session_calendar_repository import (
        CalendarVersionIntegrityError,
    )

    repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    repository.publish(
        calendar("egx-v1"),
        published_by="operator",
        source_reference="notice-1",
        reason="publish",
    )

    with repository._connect() as connection:
        connection.execute("DROP TRIGGER egx_calendar_versions_no_update")
        connection.execute(
            "UPDATE egx_calendar_versions SET calendar_json = ? WHERE version = ?",
            ("{}", "egx-v1"),
        )

    with pytest.raises(CalendarVersionIntegrityError, match="SHA-256 integrity check"):
        repository.activate(
            "egx-v1",
            performed_by="operator",
            reason="must reject corrupt calendar",
        )

    assert repository.get_active() is None
    assert repository.list_activation_events() == ()
