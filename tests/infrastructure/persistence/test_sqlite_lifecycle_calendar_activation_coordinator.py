import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time
from decimal import Decimal
from threading import Event
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.application.signals.bootstrap_opportunity_lifecycle import BootstrapOpportunityLifecycle
from app.application.signals.calendar_backed_lifecycle_evaluation_schedule import (
    CalendarBackedLifecycleEvaluationSchedule,
)
from app.application.signals.validate_lifecycle_calendar_activation import (
    LifecycleCalendarActivationValidation,
    ValidateLifecycleCalendarActivation,
)
from app.domain.identity.user import User, UserStatus
from app.domain.market_data.calendar_evidence import (
    CalendarArtifactRetention,
    CalendarEvidence,
    CalendarEvidenceKind,
    CalendarEvidenceSourceClass,
)
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.persistence.sqlite_calendar_evidence_repository import (
    SQLiteCalendarEvidenceRepository,
)
from app.infrastructure.persistence.sqlite_calendar_publication_unit_of_work import (
    SQLiteCalendarPublicationUnitOfWork,
)
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
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


CAIRO = ZoneInfo("Africa/Cairo")


class AlwaysVerifiedAuthenticity:
    def revalidate_for_activation(self, evidence, *, at):
        return True

    def assert_preflight_verification(self, evidence, *, at):
        return True

    def assert_preflight_verification(self, evidence, *, at):
        return True


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
    session_date = date(2026, 11, day)
    calendar = EGXSessionCalendar(
        version=version,
        timezone="Africa/Cairo",
        coverage_start=session_date,
        coverage_end=session_date,
        days=(
            EGXCalendarDay(
                session_date=session_date,
                status=CalendarDayStatus.SCHEDULED,
                session_open=time(10),
                session_close=time(14, 30),
            ),
        ),
    )
    actor = UUID("10000000-0000-0000-0000-000000000001")
    database = repository._database_path
    SQLiteUserStore(database).save(User(actor, UserStatus.ACTIVE))
    evidence_repository = SQLiteCalendarEvidenceRepository(database)
    evidence = CalendarEvidence.create(
        calendar_version=version,
        session_date=session_date,
        evidence_kind=CalendarEvidenceKind.SCHEDULE,
        source_type="OFFICIAL_EXCHANGE_NOTICE",
        source_reference=f"https://example.invalid/calendar/{version}/{session_date.isoformat()}",
        claim=f"EGX session scheduled on {session_date.isoformat()}",
        recorded_by=actor,
        observed_at=datetime(2026, 11, 1, 9, tzinfo=CAIRO),
        recorded_at=datetime(2026, 11, 1, 10, tzinfo=CAIRO),
        source_class=CalendarEvidenceSourceClass.A,
        source_publisher="EGX",
        market_scope="EGX_MARKET_WIDE",
        effective_from=session_date,
        effective_through=session_date,
        retrieved_at=datetime(2026, 11, 1, 9, 30, tzinfo=CAIRO),
        artifact_sha256="a" * 64,
        artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
        artifact_not_retained_reason="Fixture retains the official reference only",
    )
    SQLiteCalendarPublicationUnitOfWork(
        repository, evidence_repository
    ).publish(
        calendar,
        (evidence,),
        published_by=str(actor),
        source_reference=f"official-calendar-{version}",
        reason="atomic activation coordinator test",
        published_at=datetime(2026, 11, 1, 12, tzinfo=CAIRO),
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



def test_real_sqlite_validator_and_coordinator_activate_after_bootstrap(tmp_path):
    database = tmp_path / "real-validation.db"
    calendar_repository = SQLiteSessionCalendarRepository(database)
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    unit_of_work = SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox)

    calendar_days = tuple(
        EGXCalendarDay(
            session_date=session_date,
            status=CalendarDayStatus.SCHEDULED,
            session_open=time(10),
            session_close=time(14, 30),
        )
        for session_date in (
            date(2026, 11, 2),
            date(2026, 11, 3),
            date(2026, 11, 4),
        )
    )
    calendar = EGXSessionCalendar(
        version="verified-v1",
        timezone="Africa/Cairo",
        coverage_start=date(2026, 11, 2),
        coverage_end=date(2026, 11, 4),
        days=calendar_days,
    )
    actor = UUID("10000000-0000-0000-0000-000000000001")
    SQLiteUserStore(database).save(User(actor, UserStatus.ACTIVE))
    evidence_repository = SQLiteCalendarEvidenceRepository(database)
    evidence = tuple(
        CalendarEvidence.create(
            calendar_version="verified-v1",
            session_date=session_date,
            evidence_kind=CalendarEvidenceKind.SCHEDULE,
            source_type="OFFICIAL_EXCHANGE_NOTICE",
            source_reference=f"https://example.invalid/calendar/verified-v1/{session_date.isoformat()}",
            claim=f"EGX session scheduled on {session_date.isoformat()}",
            recorded_by=actor,
            observed_at=datetime(2026, 11, 1, 9, tzinfo=CAIRO),
            recorded_at=datetime(2026, 11, 1, 10, tzinfo=CAIRO),
            source_class=CalendarEvidenceSourceClass.A,
            source_publisher="EGX",
            market_scope="EGX_MARKET_WIDE",
            effective_from=session_date,
            effective_through=session_date,
            retrieved_at=datetime(2026, 11, 1, 9, 30, tzinfo=CAIRO),
            artifact_sha256="a" * 64,
            artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
            artifact_not_retained_reason="Fixture retains the official reference only",
        )
        for session_date in (
            date(2026, 11, 2),
            date(2026, 11, 3),
            date(2026, 11, 4),
        )
    )
    SQLiteCalendarPublicationUnitOfWork(
        calendar_repository, evidence_repository
    ).publish(
        calendar,
        evidence,
        published_by=str(actor),
        source_reference="calendar-evidence-2026-11",
        reason="verified schedule fixture",
        published_at=datetime(2026, 11, 1, 12, tzinfo=CAIRO),
    )

    published_at = datetime(2026, 11, 2, 9, tzinfo=CAIRO)
    signal = Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=published_at,
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("120"), "T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "trend evidence"),),
        strategy_id="breakout",
        strategy_version="1",
        data_timestamp=published_at,
    )
    history.record(signal, "PUBLISHED", published_at)
    BootstrapOpportunityLifecycle(
        history=history,
        calendar_store=calendar_repository,
        unit_of_work=unit_of_work,
    ).execute(
        calendar_version="verified-v1",
        operator_id="operator-1",
        reason="bootstrap before first activation",
        next_evaluation_date=date(2026, 11, 3),
        recorded_at=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
    )

    schedule = CalendarBackedLifecycleEvaluationSchedule(
        calendar_store=calendar_repository,
        candidate_calendar_version="verified-v1",
    )
    validator = ValidateLifecycleCalendarActivation(
        history=history,
        calendar_store=calendar_repository,
        unit_of_work=unit_of_work,
        schedule=schedule,
        evidence_store=evidence_repository,
        authenticity_verifier=AlwaysVerifiedAuthenticity(),
    )
    coordinator = SQLiteLifecycleCalendarActivationCoordinator(
        calendar_repository=calendar_repository,
        lifecycle_unit_of_work=unit_of_work,
        validator=validator,
    )

    attempt = coordinator.activate(
        "verified-v1",
        performed_by="admin-1",
        reason="activate after real lifecycle validation",
        as_of=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
    )

    assert attempt.validation.eligible is True
    assert attempt.validation.checked_opportunity_count == 1
    assert attempt.validation.next_evaluation_date == date(2026, 11, 3)
    assert attempt.validation.blockers == ()
    assert attempt.event is not None
    assert calendar_repository.get_active().version == "verified-v1"
    assert len(calendar_repository.list_activation_events()) == 1



def test_concurrent_calendar_writer_waits_until_lifecycle_validation_and_audit_commit(tmp_path):
    database = tmp_path / "concurrent-activation.db"
    calendar_repository = SQLiteSessionCalendarRepository(database)
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    unit_of_work = SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox)
    publish_calendar(calendar_repository, "v1", 3)

    validation_started = Event()
    release_validation = Event()
    second_writer_started = Event()
    second_writer_finished = Event()

    class BlockingValidator:
        def execute(self, *, calendar_version, as_of, transaction):
            assert transaction.bootstrap_batches() == ()
            validation_started.set()
            if not release_validation.wait(timeout=3):
                raise TimeoutError("test did not release activation validation")
            return LifecycleCalendarActivationValidation(
                eligible=True,
                calendar_version=calendar_version,
                next_evaluation_date=date(2026, 11, 3),
                checked_opportunity_count=0,
                blockers=(),
            )

    coordinator = SQLiteLifecycleCalendarActivationCoordinator(
        calendar_repository=calendar_repository,
        lifecycle_unit_of_work=unit_of_work,
        validator=BlockingValidator(),
    )
    second_repository = SQLiteSessionCalendarRepository(database)

    def second_writer():
        second_writer_started.set()
        try:
            return second_repository.activate(
                "v1",
                performed_by="other-admin",
                reason="concurrent activation attempt",
            )
        except ValueError as error:
            return error
        finally:
            second_writer_finished.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        activation_future = executor.submit(
            coordinator.activate,
            "v1",
            performed_by="admin",
            reason="serialized activation",
            as_of=datetime(2026, 11, 2, 16, tzinfo=CAIRO),
        )
        assert validation_started.wait(timeout=3)
        second_future = executor.submit(second_writer)
        assert second_writer_started.wait(timeout=3)
        assert second_writer_finished.wait(timeout=0.15) is False
        release_validation.set()

        activation = activation_future.result(timeout=3)
        second_result = second_future.result(timeout=3)

    assert activation.event is not None
    assert isinstance(second_result, ValueError)
    assert "already active" in str(second_result)
    assert calendar_repository.get_active().version == "v1"
    assert len(calendar_repository.list_activation_events()) == 1



def test_real_validator_rejects_evidence_store_outside_coordinator_database(tmp_path):
    database = tmp_path / "shared.db"
    wrong_database = tmp_path / "evidence.db"
    calendar_repository = SQLiteSessionCalendarRepository(database)
    history = SQLiteSignalHistoryStore(database)
    track_record = SQLiteTrackRecordStore(database)
    outbox = SQLiteAlertOutbox(database)
    unit_of_work = SQLiteSignalLifecycleUnitOfWork(history, track_record, outbox)
    wrong_evidence_repository = SQLiteCalendarEvidenceRepository(wrong_database)
    schedule = CalendarBackedLifecycleEvaluationSchedule(
        calendar_store=calendar_repository,
        candidate_calendar_version="calendar-v1",
    )
    validator = ValidateLifecycleCalendarActivation(
        history=history,
        calendar_store=calendar_repository,
        unit_of_work=unit_of_work,
        schedule=schedule,
        evidence_store=wrong_evidence_repository,
    )

    with pytest.raises(ValueError, match="all activation validation stores"):
        SQLiteLifecycleCalendarActivationCoordinator(
            calendar_repository=calendar_repository,
            lifecycle_unit_of_work=unit_of_work,
            validator=validator,
        )
