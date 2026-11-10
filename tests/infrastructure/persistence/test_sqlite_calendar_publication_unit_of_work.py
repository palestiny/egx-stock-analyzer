from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timezone
from uuid import UUID

import pytest

from app.domain.identity.user import User, UserStatus
from app.domain.market_data.calendar_evidence import CalendarEvidence, CalendarEvidenceKind, CalendarEvidenceSourceClass, CalendarArtifactRetention
from app.domain.market_data.session_calendar import CalendarDayStatus, EGXCalendarDay, EGXSessionCalendar
from app.infrastructure.persistence.sqlite_calendar_evidence_repository import SQLiteCalendarEvidenceRepository
from app.infrastructure.persistence.sqlite_calendar_publication_unit_of_work import SQLiteCalendarPublicationUnitOfWork
from app.infrastructure.persistence.sqlite_session_calendar_repository import SQLiteSessionCalendarRepository
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


ACTOR = UUID("10000000-0000-0000-0000-000000000001")


def _calendar(version: str = "atomic-calendar-v1") -> EGXSessionCalendar:
    return EGXSessionCalendar(
        version=version,
        timezone="Africa/Cairo",
        coverage_start=date(2026, 11, 1),
        coverage_end=date(2026, 11, 2),
        days=(
            EGXCalendarDay(date(2026, 11, 1), CalendarDayStatus.NON_TRADING),
            EGXCalendarDay(date(2026, 11, 2), CalendarDayStatus.NON_TRADING),
        ),
    )


def _evidence(
    day: date,
    claim: str,
    *,
    kind: CalendarEvidenceKind = CalendarEvidenceKind.SCHEDULE,
    evidence_id: UUID | None = None,
    supersedes_evidence_id: UUID | None = None,
    supersession_reason: str | None = None,
    source_class: CalendarEvidenceSourceClass = CalendarEvidenceSourceClass.A,
    market_scope: str = "EGX_MARKET_WIDE",
    effective_from: date | None = None,
    calendar_version: str = "atomic-calendar-v1",
) -> CalendarEvidence:
    return CalendarEvidence.create(
        calendar_version=calendar_version,
        session_date=day,
        evidence_kind=kind,
        source_type="OFFICIAL_EXCHANGE_NOTICE",
        source_reference=f"https://example.invalid/notices/{day.isoformat()}",
        claim=claim,
        recorded_by=ACTOR,
        observed_at=datetime(2026, 11, day.day, 9, tzinfo=timezone.utc),
        evidence_id=evidence_id,
        supersedes_evidence_id=supersedes_evidence_id,
        supersession_reason=supersession_reason,
        source_class=source_class,
        source_publisher={CalendarEvidenceSourceClass.A: "EGX", CalendarEvidenceSourceClass.A_R: "FRA", CalendarEvidenceSourceClass.B: "Public authority", CalendarEvidenceSourceClass.C: "Broker"}[source_class],
        market_scope=market_scope,
        effective_from=effective_from or day,
        effective_through=day,
        retrieved_at=datetime(2026, 11, day.day, 9, tzinfo=timezone.utc),
        artifact_sha256="a" * 64,
        artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
        artifact_not_retained_reason="Test fixture stores the official reference only",
    )


def _setup(tmp_path):
    database = tmp_path / "calendar.db"
    calendar_repository = SQLiteSessionCalendarRepository(database)
    evidence_repository = SQLiteCalendarEvidenceRepository(database)
    SQLiteUserStore(database).save(User(ACTOR, UserStatus.ACTIVE))
    uow = SQLiteCalendarPublicationUnitOfWork(calendar_repository, evidence_repository)
    return database, calendar_repository, evidence_repository, uow


def _evidence_set():
    return (
        _evidence(date(2026, 11, 1), "Official notice confirms closure", kind=CalendarEvidenceKind.CLOSURE),
        _evidence(date(2026, 11, 2), "Official notice confirms closure", kind=CalendarEvidenceKind.CLOSURE),
    )


def test_publication_commits_calendar_evidence_and_explicit_links_together(tmp_path):
    database, calendars, evidence_repository, uow = _setup(tmp_path)

    stored, evidence = uow.publish(
        _calendar(),
        _evidence_set(),
        published_by=str(ACTOR),
        source_reference="EGX source bundle",
        reason="Atomic publication test",
    )

    assert calendars.get_version(stored.version) == stored
    assert len(evidence) == 2
    assert all(evidence_repository.get(item.evidence_id) == item for item in evidence)
    with sqlite3.connect(database) as connection:
        links = connection.execute(
            "SELECT calendar_version, session_date, evidence_id "
            "FROM egx_calendar_day_evidence_links ORDER BY session_date"
        ).fetchall()
    assert len(links) == 2
    assert {row[1] for row in links} == {"2026-11-01", "2026-11-02"}


def test_failure_after_first_evidence_insert_rolls_back_every_publication_row(tmp_path, monkeypatch):
    database, calendars, evidence_repository, uow = _setup(tmp_path)
    original = evidence_repository.append_in_transaction
    calls = 0

    def fail_after_one(connection, evidence):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected evidence persistence failure")
        return original(connection, evidence)

    monkeypatch.setattr(evidence_repository, "append_in_transaction", fail_after_one)

    with pytest.raises(RuntimeError, match="injected"):
        uow.publish(
            _calendar(),
            _evidence_set(),
            published_by=str(ACTOR),
            source_reference="EGX source bundle",
            reason="Rollback test",
        )

    assert calendars.get_version("atomic-calendar-v1") is None
    assert evidence_repository.list_for_day("atomic-calendar-v1", date(2026, 11, 1)) == ()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_versions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_day_evidence_links").fetchone()[0] == 0


def test_conflicting_unsuperseded_claims_roll_back_calendar_and_evidence(tmp_path):
    database, calendars, evidence_repository, uow = _setup(tmp_path)
    evidence = (
        _evidence(date(2026, 11, 1), "Official notice says trading", kind=CalendarEvidenceKind.CLOSURE),
        _evidence(date(2026, 11, 1), "Different official notice says closure", kind=CalendarEvidenceKind.CLOSURE),
        _evidence(date(2026, 11, 2), "Official notice confirms closure", kind=CalendarEvidenceKind.CLOSURE),
    )

    with pytest.raises(ValueError, match="Unresolved calendar evidence conflict"):
        uow.publish(
            _calendar(),
            evidence,
            published_by=str(ACTOR),
            source_reference="EGX source bundle",
            reason="Conflict rejection test",
        )

    assert calendars.get_version("atomic-calendar-v1") is None
    assert evidence_repository.list_for_day("atomic-calendar-v1", date(2026, 11, 1)) == ()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_day_evidence_links").fetchone()[0] == 0


def test_publication_requires_evidence_for_exact_calendar_date_set(tmp_path):
    _database, _calendars, _evidence_repository, uow = _setup(tmp_path)
    with pytest.raises(ValueError, match="cover exactly"):
        uow.publish(
            _calendar(),
            (_evidence(date(2026, 11, 1), "Only first date is evidenced"),),
            published_by=str(ACTOR),
            source_reference="EGX source bundle",
            reason="Missing evidence test",
        )


def test_publication_rejects_evidence_actor_mismatch_before_writes(tmp_path):
    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    mismatched = tuple(
        CalendarEvidence.create(
            calendar_version=item.calendar_version,
            session_date=item.session_date,
            evidence_kind=item.evidence_kind,
            source_type=item.source_type,
            source_reference=item.source_reference,
            claim=item.claim,
            recorded_by=UUID("20000000-0000-0000-0000-000000000002"),
            observed_at=item.observed_at,
            source_class=item.source_class,
            source_publisher=item.source_publisher,
            market_scope=item.market_scope,
            effective_from=item.effective_from,
            effective_through=item.effective_through,
            retrieved_at=item.retrieved_at,
            artifact_sha256=item.artifact_sha256,
            artifact_retention=item.artifact_retention,
            artifact_not_retained_reason=item.artifact_not_retained_reason,
        )
        for item in _evidence_set()
    )
    with pytest.raises(ValueError, match="actor must match"):
        uow.publish(
            _calendar(),
            mismatched,
            published_by=str(ACTOR),
            source_reference="EGX source bundle",
            reason="Actor mismatch test",
        )
    assert calendars.list_versions() == ()


def test_calendar_evidence_repositories_must_share_database(tmp_path):
    calendars = SQLiteSessionCalendarRepository(tmp_path / "calendar.db")
    evidence = SQLiteCalendarEvidenceRepository(tmp_path / "evidence.db")
    with pytest.raises(ValueError, match="share one SQLite database"):
        SQLiteCalendarPublicationUnitOfWork(calendars, evidence)



def test_failure_after_all_links_are_written_rolls_back_every_table(tmp_path, monkeypatch):
    database, calendars, evidence_repository, uow = _setup(tmp_path)

    def fail_validation(_connection, _version, _dates):
        raise RuntimeError("injected final validation failure")

    monkeypatch.setattr(uow, "_validate_no_unresolved_conflicts", fail_validation)

    with pytest.raises(RuntimeError, match="final validation"):
        uow.publish(
            _calendar(),
            _evidence_set(),
            published_by=str(ACTOR),
            source_reference="EGX source bundle",
            reason="Final gate rollback test",
        )

    assert calendars.get_version("atomic-calendar-v1") is None
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_versions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM egx_calendar_day_evidence_links").fetchone()[0] == 0


def test_second_connection_cannot_observe_uncommitted_calendar_or_evidence(tmp_path, monkeypatch):
    database, calendars, evidence_repository, uow = _setup(tmp_path)
    original = evidence_repository.append_in_transaction
    observations = []

    def inspect_from_other_connection(connection, item):
        stored = original(connection, item)
        with sqlite3.connect(database) as observer:
            observations.append(
                (
                    observer.execute(
                        "SELECT COUNT(*) FROM egx_calendar_versions"
                    ).fetchone()[0],
                    observer.execute(
                        "SELECT COUNT(*) FROM egx_calendar_evidence"
                    ).fetchone()[0],
                )
            )
        return stored

    monkeypatch.setattr(evidence_repository, "append_in_transaction", inspect_from_other_connection)
    uow.publish(
        _calendar(),
        _evidence_set(),
        published_by=str(ACTOR),
        source_reference="EGX source bundle",
        reason="Isolation test",
    )

    assert observations == [(0, 0), (0, 0)]
    assert calendars.get_version("atomic-calendar-v1") is not None


def test_calendar_status_requires_its_corresponding_evidence_kind(tmp_path):
    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    invalid = (
        _evidence(date(2026, 11, 1), "A schedule claim", kind=CalendarEvidenceKind.SCHEDULE),
        _evidence(date(2026, 11, 2), "A closure claim", kind=CalendarEvidenceKind.CLOSURE),
    )

    with pytest.raises(ValueError, match="requires evidence kinds: CLOSURE"):
        uow.publish(
            _calendar(),
            invalid,
            published_by=str(ACTOR),
            source_reference="EGX source bundle",
            reason="Evidence-kind validation test",
        )

    assert calendars.list_versions() == ()



def test_in_batch_supersession_preserves_original_and_resolves_claim(tmp_path):
    _database, _calendars, evidence_repository, uow = _setup(tmp_path)
    original_id = UUID("30000000-0000-0000-0000-000000000001")
    correction_id = UUID("30000000-0000-0000-0000-000000000002")
    original = _evidence(
        date(2026, 11, 1),
        "Initial notice says non-trading",
        kind=CalendarEvidenceKind.CLOSURE,
        evidence_id=original_id,
    )
    correction = _evidence(
        date(2026, 11, 1),
        "Corrected notice confirms non-trading",
        kind=CalendarEvidenceKind.CLOSURE,
        evidence_id=correction_id,
        supersedes_evidence_id=original_id,
        supersession_reason="A later official exchange notice corrected the earlier claim",
    )
    second_day = _evidence(
        date(2026, 11, 2),
        "Official notice confirms closure",
        kind=CalendarEvidenceKind.CLOSURE,
    )

    _stored, evidence = uow.publish(
        _calendar(),
        (original, correction, second_day),
        published_by=str(ACTOR),
        source_reference="EGX source bundle",
        reason="In-batch correction test",
    )

    assert len(evidence) == 3
    assert evidence_repository.get(original_id) == evidence[0]
    assert evidence_repository.get(correction_id) == evidence[1]
    assert evidence[1].supersedes_evidence_id == original_id
    assert evidence_repository.list_conflicts(
        "atomic-calendar-v1", date(2026, 11, 1)
    ) == ()


def test_secondary_source_cannot_authorize_calendar_publication(tmp_path):
    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    evidence = (
        _evidence(date(2026, 11, 1), "Broker says closure", kind=CalendarEvidenceKind.CLOSURE, source_class=CalendarEvidenceSourceClass.C),
        _evidence(date(2026, 11, 2), "EGX says closure", kind=CalendarEvidenceKind.CLOSURE),
    )
    with pytest.raises(ValueError, match="Class A EGX primary evidence"):
        uow.publish(
            _calendar(), evidence, published_by=str(ACTOR),
            source_reference="EGX source bundle", reason="Reject secondary-only evidence",
        )
    assert calendars.list_versions() == ()


def test_regulatory_evidence_is_limited_to_fra_scope_and_cannot_authorize_egx_session(tmp_path):
    with pytest.raises(ValueError, match="FRA_REGULATORY"):
        _evidence(
            date(2026, 11, 1), "FRA regulatory notice",
            kind=CalendarEvidenceKind.CLOSURE,
            source_class=CalendarEvidenceSourceClass.A_R,
            market_scope="EGX_MARKET_WIDE",
        )

    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    evidence = (
        _evidence(
            date(2026, 11, 1), "FRA regulatory context",
            kind=CalendarEvidenceKind.CLOSURE,
            source_class=CalendarEvidenceSourceClass.A_R,
            market_scope="FRA_REGULATORY",
        ),
        _evidence(date(2026, 11, 2), "EGX operational closure", kind=CalendarEvidenceKind.CLOSURE),
    )
    with pytest.raises(ValueError, match="Class A EGX primary evidence kinds"):
        uow.publish(
            _calendar(), evidence, published_by=str(ACTOR),
            source_reference="EGX source bundle", reason="Regulatory evidence is not operational evidence",
        )
    assert calendars.list_versions() == ()


def test_primary_evidence_must_cover_egx_market_wide_scope(tmp_path):
    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    evidence = (
        _evidence(
            date(2026, 11, 1), "Index-only notice", kind=CalendarEvidenceKind.CLOSURE,
            market_scope="EGX_INDEX_ONLY",
        ),
        _evidence(date(2026, 11, 2), "EGX says closure", kind=CalendarEvidenceKind.CLOSURE),
    )
    with pytest.raises(ValueError, match="Class A EGX primary evidence kinds"):
        uow.publish(
            _calendar(), evidence, published_by=str(ACTOR),
            source_reference="EGX source bundle", reason="Reject non-market-wide evidence",
        )
    assert calendars.list_versions() == ()


def test_open_status_requires_schedule_and_open_confirmation(tmp_path):
    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    open_day = EGXSessionCalendar(
        version="open-calendar-v1", timezone="Africa/Cairo",
        coverage_start=date(2026, 11, 3), coverage_end=date(2026, 11, 3),
        days=(EGXCalendarDay(date(2026, 11, 3), CalendarDayStatus.OPEN,
                             session_open=time(10, 0),
                             session_close=time(14, 30)),),
    )
    schedule_only = (_evidence(date(2026, 11, 3), "Scheduled", kind=CalendarEvidenceKind.SCHEDULE, calendar_version="open-calendar-v1"),)
    with pytest.raises(ValueError, match="OPEN_CONFIRMATION"):
        uow.publish(
            open_day, schedule_only, published_by=str(ACTOR),
            source_reference="EGX source bundle", reason="Require opening confirmation",
        )
    with_open = schedule_only + (
        _evidence(date(2026, 11, 3), "Trading opened", kind=CalendarEvidenceKind.OPEN_CONFIRMATION, calendar_version="open-calendar-v1"),
    )
    stored, _ = uow.publish(
        open_day, with_open, published_by=str(ACTOR),
        source_reference="EGX source bundle", reason="Opening confirmation supplied",
    )
    assert calendars.get_version(stored.version) == stored


def test_exceptional_hours_requires_its_own_primary_evidence_kind(tmp_path):
    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    exceptional_day = EGXSessionCalendar(
        version="exceptional-calendar-v1", timezone="Africa/Cairo",
        coverage_start=date(2026, 11, 3), coverage_end=date(2026, 11, 3),
        days=(EGXCalendarDay(
            date(2026, 11, 3), CalendarDayStatus.SCHEDULED,
            session_open=time(10, 0), session_close=time(13, 0),
            exceptional_hours=True,
        ),),
    )
    schedule = (_evidence(
        date(2026, 11, 3), "Scheduled", kind=CalendarEvidenceKind.SCHEDULE,
        calendar_version="exceptional-calendar-v1",
    ),)
    with pytest.raises(ValueError, match="EXCEPTIONAL_HOURS"):
        uow.publish(
            exceptional_day, schedule, published_by=str(ACTOR),
            source_reference="EGX source bundle", reason="Require exceptional-hours evidence",
        )
    evidence = schedule + (_evidence(
        date(2026, 11, 3), "EGX confirms shortened session hours",
        kind=CalendarEvidenceKind.EXCEPTIONAL_HOURS,
        calendar_version="exceptional-calendar-v1",
    ),)
    stored, _ = uow.publish(
        exceptional_day, evidence, published_by=str(ACTOR),
        source_reference="EGX source bundle", reason="Publish evidenced exceptional hours",
    )
    assert calendars.get_version(stored.version) == stored


def test_exceptional_hours_evidence_requires_explicit_calendar_day_marker(tmp_path):
    _database, calendars, _evidence_repository, uow = _setup(tmp_path)
    evidence = (
        _evidence(date(2026, 11, 1), "EGX confirms exceptional hours", kind=CalendarEvidenceKind.EXCEPTIONAL_HOURS),
        _evidence(date(2026, 11, 2), "EGX says closure", kind=CalendarEvidenceKind.CLOSURE),
    )
    with pytest.raises(ValueError, match="without an explicit day marker"):
        uow.publish(
            _calendar(), evidence, published_by=str(ACTOR),
            source_reference="EGX source bundle", reason="Reject orphan exceptional-hours evidence",
        )
    assert calendars.list_versions() == ()
