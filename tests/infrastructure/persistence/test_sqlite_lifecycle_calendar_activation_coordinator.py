import sqlite3
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.application.signals.validate_lifecycle_calendar_activation import (
    LifecycleCalendarActivationValidation,
)
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.persistence.sqlite_lifecycle_calendar_activation_coordinator import (
    SQLiteLifecycleCalendarActivationCoordinator,
)
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)
from app.infrastructure.persistence.sqlite_signal_history_store import (
    SQLiteSignalHistoryStore,
)
from app.infrastructure.persistence.sqlite_signal_lifecycle_unit_of_work import (
    SQLiteSignalLifecycleUnitOfWork,
)
from app.infrastructure.persistence.sqlite_track_record_store import (
    SQLiteTrackRecordStore,
)


CAIRO = ZoneInfo("Africa/Cairo")


class StubValidator:
    def __init__(self, *, eligible=True):
        self.eligible = eligible
        self.received_transaction = False

    def execute(self, *, calendar_version, as_of, transaction):
        assert transaction.bootstrap_batches() == ()
        self.received_transaction = True
        blockers = ()
        return LifecycleCalendarActivationValidation(
            eligible=self.eligible,
            calendar_version=calendar_version,
            next_evaluation_date=date(2026, 11, 3),
            checked_opportunity_count=0,
            blockers=blockers,
        )


def publish_calendar(repository, version, day):
    calendar = EGXSessionCalendar(
        version=version,
        timezone="Africa/Cairo",
        coverage_start=date(2026, 11, day),
        coverage_end=date(2026, 11, day),
        days=(
            EGXCalendarDay(
                session_date=date(2026, 11, day),
                status=CalendarDayStatus.SCHEDULED,
                session_open=time(10),
                session_close=time(14, 30),
            ),
        ),
    )
    repository.publish(
        calendar,
        published_by="operator",
        source_reference=f"official-calendar-{version}",
        reason="atomic activation coordinator test",
        published_at=datetime(2026, 11, 1, tzinfo=CAIRO),
    )


def make_coordinator(database, *, eligible=True):
    calendar_repository = SQLiteSessionCalendarRepository(database)
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    unit_of_work = SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox)
    validator = StubValidator(eligible=eligible)
    coordinator = SQLiteLifecycleCalendarActivationCoordinator(
        calendar_repository=calendar_repository,
        lifecycle_unit_of_work=unit_of_work,
        validator=validator,
    )
    return coordinator, calendar_repository, unit_of_work, validator


def test_activation_runs_validation_and_pointer_audit_in_one_owned_transaction(tmp_path, monkeypatch):
    database = tmp_path / "activation.db"
    coordinator, repository, unit_of_work, validator = make_coordinator(database)
    publish_calendar(repository, "v1", 3)

    def separate_uow_execution_is_forbidden(*args, **kwargs):
        raise AssertionError("activation must not open a nested lifecycle transaction")

    monkeypatch.setattr(unit_of_work, "execute", separate_uow_execution_is_forbidden)

    attempt = coordinator.activate(
        "v1",
        performed_by="admin",
        reason="activate after validation",
        as_of=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
    )

    assert validator.received_transaction is True
    assert attempt.validation.eligible is True
    assert attempt.event is not None
    assert attempt.event.action == "ACTIVATE"
    assert repository.get_active().version == "v1"
    assert len(repository.list_activation_events()) == 1


def test_rejected_validation_leaves_pointer_and_audit_unchanged(tmp_path):
    database = tmp_path / "rejected.db"
    coordinator, repository, _, _ = make_coordinator(database, eligible=False)
    publish_calendar(repository, "v1", 3)

    attempt = coordinator.activate(
        "v1",
        performed_by="admin",
        reason="must be rejected",
        as_of=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
    )

    assert attempt.validation.eligible is False
    assert attempt.event is None
    assert repository.get_active() is None
    assert repository.list_activation_events() == ()


def test_audit_insert_failure_rolls_back_active_pointer_change(tmp_path):
    database = tmp_path / "audit-failure.db"
    coordinator, repository, _, _ = make_coordinator(database)
    publish_calendar(repository, "v1", 3)
    publish_calendar(repository, "v2", 4)

    first = coordinator.activate(
        "v1",
        performed_by="admin",
        reason="first",
        as_of=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
    )
    second = coordinator.activate(
        "v2",
        performed_by="admin",
        reason="second",
        as_of=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
    )
    assert first.event is not None and second.event is not None
    events_before = repository.list_activation_events()

    with repository._connect() as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_rollback_audit
            BEFORE INSERT ON egx_calendar_activation_events
            WHEN NEW.action = 'ROLLBACK'
            BEGIN
                SELECT RAISE(ABORT, 'injected audit failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="injected audit failure"):
        coordinator.rollback(
            "v1",
            performed_by="admin",
            reason="restore first",
            as_of=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
        )

    assert repository.get_active().version == "v2"
    assert repository.list_activation_events() == events_before


def test_coordinator_rejects_stores_on_different_database_files(tmp_path):
    calendar_repository = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    history = SQLiteSignalHistoryStore(tmp_path / "history.db")
    track_record = SQLiteTrackRecordStore(tmp_path / "history.db")
    outbox = SQLiteAlertOutbox(tmp_path / "history.db")
    unit_of_work = SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox)

    with pytest.raises(ValueError, match="share one SQLite database"):
        SQLiteLifecycleCalendarActivationCoordinator(
            calendar_repository=calendar_repository,
            lifecycle_unit_of_work=unit_of_work,
            validator=StubValidator(),
        )
