import sqlite3
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.domain.market_data.calendar_evidence import (
    CalendarEvidence,
    CalendarEvidenceKind,
    CalendarEvidenceSourceClass,
    CalendarArtifactRetention,
)
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.infrastructure.persistence.sqlite_calendar_evidence_repository import (
    CalendarEvidenceIntegrityError,
    SQLiteCalendarEvidenceRepository,
)
from app.domain.identity.user import User, UserStatus
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)


def _calendar():
    return EGXSessionCalendar(
        version="egx-evidence-v1",
        timezone="Africa/Cairo",
        coverage_start=date(2026, 11, 2),
        coverage_end=date(2026, 11, 2),
        days=(EGXCalendarDay(date(2026, 11, 2), CalendarDayStatus.NON_TRADING),),
    )


def _evidence(claim="Exchange notice confirms closure", **overrides):
    values = {
        "calendar_version": "egx-evidence-v1",
        "session_date": date(2026, 11, 2),
        "evidence_kind": CalendarEvidenceKind.CLOSURE,
        "source_type": "OFFICIAL_EXCHANGE_NOTICE",
        "source_reference": "https://example.invalid/notice/123",
        "claim": claim,
        "recorded_by": UUID("10000000-0000-0000-0000-000000000001"),
        "observed_at": datetime(2026, 11, 2, 12, tzinfo=timezone.utc),
        "source_class": CalendarEvidenceSourceClass.A,
        "source_publisher": "EGX",
        "market_scope": "EGX_MARKET_WIDE",
        "effective_from": date(2026, 11, 2),
        "effective_through": date(2026, 11, 2),
        "retrieved_at": datetime(2026, 11, 2, 12, tzinfo=timezone.utc),
        "artifact_sha256": "b" * 64,
        "artifact_retention": CalendarArtifactRetention.EXTERNAL_ONLY,
        "artifact_not_retained_reason": "Test fixture stores the official reference only",
    }
    values.update(overrides)
    return CalendarEvidence.create(**values)


def _repository(tmp_path):
    database = tmp_path / "evidence.db"
    SQLiteSessionCalendarRepository(database).publish(
        _calendar(),
        published_by="bootstrap-user",
        source_reference="schema-fixture",
        reason="test fixture only",
    )
    SQLiteUserStore(database).save(
        User(
            id=UUID("10000000-0000-0000-0000-000000000001"),
            status=UserStatus.ACTIVE,
        )
    )
    return SQLiteCalendarEvidenceRepository(database), database


def test_evidence_is_append_only_and_survives_recreation(tmp_path):
    repository, database = _repository(tmp_path)
    stored = repository.append(_evidence())
    recreated = SQLiteCalendarEvidenceRepository(database)
    assert recreated.get(stored.evidence_id) == stored
    assert len(stored.content_sha256) == 64
    with recreated._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE egx_calendar_evidence SET claim = 'rewritten' WHERE evidence_id = ?",
                (str(stored.evidence_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM egx_calendar_evidence WHERE evidence_id = ?",
                (str(stored.evidence_id),),
            )


def test_conflicting_claims_are_visible_not_overwritten(tmp_path):
    repository, _ = _repository(tmp_path)
    first = repository.append(_evidence("Closure notice A"))
    second = repository.append(_evidence("Trading session notice B"))
    conflicts = repository.list_conflicts("egx-evidence-v1", date(2026, 11, 2))
    assert len(conflicts) == 1
    assert {item.evidence_id for item in conflicts[0].evidence} == {
        first.evidence_id, second.evidence_id
    }


def test_correction_appends_and_preserves_original_evidence(tmp_path):
    repository, _ = _repository(tmp_path)
    original = repository.append(_evidence("Initial notice"))
    correction = repository.append(
        _evidence(
            "Corrected notice",
            supersedes_evidence_id=original.evidence_id,
            supersession_reason="Exchange issued a correction",
        )
    )
    assert repository.get(original.evidence_id) == original
    assert correction.supersedes_evidence_id == original.evidence_id
    assert len(repository.list_for_day("egx-evidence-v1", date(2026, 11, 2))) == 2
    assert repository.list_conflicts("egx-evidence-v1", date(2026, 11, 2)) == ()


def test_supersession_must_reference_same_day_and_kind(tmp_path):
    repository, _ = _repository(tmp_path)
    original = repository.append(_evidence())
    with pytest.raises(ValueError, match="same calendar day and kind"):
        repository.append(
            _evidence(
                evidence_kind=CalendarEvidenceKind.SCHEDULE,
                supersedes_evidence_id=original.evidence_id,
                supersession_reason="wrong evidence kind",
            )
        )


def test_read_detects_evidence_hash_tampering(tmp_path):
    repository, _ = _repository(tmp_path)
    stored = repository.append(_evidence())
    with repository._connect() as connection:
        connection.execute("DROP TRIGGER egx_calendar_evidence_no_update")
        connection.execute(
            "UPDATE egx_calendar_evidence SET claim = 'tampered' WHERE evidence_id = ?",
            (str(stored.evidence_id),),
        )
    with pytest.raises(CalendarEvidenceIntegrityError, match="SHA-256"):
        repository.get(stored.evidence_id)


def test_evidence_requires_timezone_aware_timestamps():
    with pytest.raises(ValueError, match="observed_at"):
        _evidence(observed_at=datetime(2026, 11, 2, 12))


def test_supersession_reason_is_mandatory():
    with pytest.raises(ValueError, match="supersession_reason"):
        _evidence(supersedes_evidence_id=uuid4())

def test_evidence_must_reference_an_explicit_calendar_coverage_date(tmp_path):
    repository, _ = _repository(tmp_path)
    with pytest.raises(ValueError, match="explicit date"):
        repository.append(
            _evidence(session_date=date(2026, 11, 3))
        )


def test_evidence_must_reference_an_existing_calendar_version(tmp_path):
    repository, _ = _repository(tmp_path)
    with pytest.raises(KeyError, match="Unknown calendar version"):
        repository.append(_evidence(calendar_version="missing-version"))

def test_evidence_actor_must_reference_an_existing_user(tmp_path):
    repository, _ = _repository(tmp_path)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        repository.append(_evidence(recorded_by=uuid4()))
