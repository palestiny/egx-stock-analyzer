from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.signals.bootstrap_opportunity_lifecycle import BootstrapOpportunityLifecycle
from app.application.signals.lifecycle_unit_of_work import (
    InMemorySignalLifecycleUnitOfWork,
    LifecycleObservationRecord,
)
from app.application.signals.store import InMemorySignalHistoryStore
from app.application.signals.track_record import InMemoryTrackRecordStore
from app.application.signals.validate_lifecycle_calendar_activation import (
    ValidateLifecycleCalendarActivation,
)
from app.domain.market_data.calendar_evidence import (
    CalendarArtifactRetention,
    CalendarEvidence,
    CalendarEvidenceKind,
    CalendarEvidenceSourceClass,
)
from app.domain.market_data.session_calendar import (
    CalendarDayStatus, EGXCalendarDay, EGXSessionCalendar,
)
from app.domain.signals.lifecycle import CompletedDailyBarObservation
from app.domain.signals.model import (
    PriceZone, Signal, SignalDirection, SignalEvidence, SignalStatus, Target,
)


CAIRO = ZoneInfo("Africa/Cairo")
START = date(2026, 10, 1)
END = date(2026, 10, 15)


class FakeCalendarStore:
    def __init__(self, stored):
        self.stored = stored

    def get_version(self, version):
        return self.stored if self.stored.version == version else None


class FakeCalendarEvidenceStore:
    def __init__(self, stored):
        self.stored = stored
        self.missing = set()
        self.source_class = CalendarEvidenceSourceClass.A
        self.conflicting = set()

    def list_for_calendar_day(self, calendar_version, session_date):
        if calendar_version != self.stored.version:
            return ()
        day = self.stored.calendar.day_for(session_date)
        required = {
            CalendarDayStatus.NON_TRADING: {CalendarEvidenceKind.CLOSURE},
            CalendarDayStatus.CANCELLED: {CalendarEvidenceKind.CANCELLATION},
            CalendarDayStatus.SCHEDULED: {CalendarEvidenceKind.SCHEDULE},
            CalendarDayStatus.OPEN: {CalendarEvidenceKind.SCHEDULE, CalendarEvidenceKind.OPEN_CONFIRMATION},
            CalendarDayStatus.CLOSED: {CalendarEvidenceKind.SCHEDULE, CalendarEvidenceKind.CLOSE_CONFIRMATION},
        }[day.status]
        if day.exceptional_hours:
            required.add(CalendarEvidenceKind.EXCEPTIONAL_HOURS)
        records = []
        for kind in required:
            if (session_date, kind) in self.missing:
                continue
            source_class = self.source_class
            publisher = "EGX" if source_class is CalendarEvidenceSourceClass.A else (
                "FRA" if source_class is CalendarEvidenceSourceClass.A_R else "Broker"
            )
            market_scope = (
                "FRA_REGULATORY"
                if source_class is CalendarEvidenceSourceClass.A_R
                else "EGX_MARKET_WIDE"
            )
            records.append(CalendarEvidence.create(
                calendar_version=calendar_version,
                session_date=session_date,
                evidence_kind=kind,
                source_type="OFFICIAL_EXCHANGE_NOTICE",
                source_reference=f"https://example.invalid/{session_date.isoformat()}/{kind.value}",
                claim=f"Verified {kind.value} for {session_date.isoformat()}",
                recorded_by=UUID("10000000-0000-0000-0000-000000000001"),
                observed_at=datetime.combine(session_date, time(9), tzinfo=CAIRO),
                source_class=source_class,
                source_publisher=publisher,
                market_scope=market_scope,
                effective_from=session_date,
                effective_through=session_date,
                retrieved_at=datetime.combine(session_date, time(9), tzinfo=CAIRO),
                artifact_sha256="a" * 64,
                artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
                artifact_not_retained_reason="Fixture retains the official reference only",
            ))
            if (session_date, kind) in self.conflicting:
                records.append(CalendarEvidence.create(
                    calendar_version=calendar_version,
                    session_date=session_date,
                    evidence_kind=kind,
                    source_type="OFFICIAL_EXCHANGE_NOTICE",
                    source_reference=f"https://example.invalid/conflict/{session_date.isoformat()}/{kind.value}",
                    claim=f"Conflicting {kind.value} for {session_date.isoformat()}",
                    recorded_by=UUID("10000000-0000-0000-0000-000000000001"),
                    observed_at=datetime.combine(session_date, time(9), tzinfo=CAIRO),
                    source_class=source_class,
                    source_publisher=publisher,
                    market_scope="EGX_MARKET_WIDE",
                    effective_from=session_date,
                    effective_through=session_date,
                    retrieved_at=datetime.combine(session_date, time(9), tzinfo=CAIRO),
                    artifact_sha256="b" * 64,
                    artifact_retention=CalendarArtifactRetention.EXTERNAL_ONLY,
                    artifact_not_retained_reason="Conflicting fixture evidence",
                ))
        return tuple(records)


class FakeAuthenticityVerifier:
    def revalidate_for_activation(self, evidence, *, at):
        return True

    def assert_preflight_verification(self, evidence, *, at):
        return True


class FakeSchedule:
    def __init__(self, next_date):
        self.next_date = next_date
        self.received_after = None

    def next_evaluation_date(self, *, after):
        self.received_after = after
        return self.next_date


def make_calendar(*, version="calendar-v1", end=END, next_status=CalendarDayStatus.SCHEDULED, closed_dates=()):
    days = []
    current = START
    while current <= end:
        trading = current.weekday() not in (4, 5)
        status = CalendarDayStatus.SCHEDULED if trading else CalendarDayStatus.NON_TRADING
        if current in closed_dates:
            status = CalendarDayStatus.CLOSED
        elif current == date(2026, 10, 6):
            status = next_status
        days.append(EGXCalendarDay(
            current, status,
            session_open=time(10, 0) if status in {CalendarDayStatus.SCHEDULED, CalendarDayStatus.CLOSED} else None,
            session_close=time(14, 30) if status in {CalendarDayStatus.SCHEDULED, CalendarDayStatus.CLOSED} else None,
            closed_at=(
                datetime.combine(current, time(14, 35), tzinfo=CAIRO)
                if status is CalendarDayStatus.CLOSED else None
            ),
        ))
        current += timedelta(days=1)
    calendar = EGXSessionCalendar(
        version, "Africa/Cairo", START, end, tuple(days)
    )
    return StoredCalendarVersion(
        version, calendar, "a" * 64,
        datetime(2026, 9, 30, 12, tzinfo=CAIRO),
        "calendar-operator", "official-calendar-evidence", "approved fixture",
    )


def make_signal():
    generated = datetime(2026, 10, 1, 9, tzinfo=CAIRO)
    return Signal(
        symbol="COMI", direction=SignalDirection.BUY, status=SignalStatus.ACTIVE,
        generated_at=generated, timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"), targets=(Target(Decimal("120"), "T1"),),
        confidence=Decimal("80"), risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "trend evidence"),),
        strategy_id="breakout", strategy_version="1", data_timestamp=generated,
    )


def setup(*, bootstrap=True, next_date=date(2026, 10, 6), bootstrap_next_date=None, end=END, next_status=CalendarDayStatus.SCHEDULED, version="calendar-v1", closed_dates=()):
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track = InMemoryTrackRecordStore()
    uow = InMemorySignalLifecycleUnitOfWork(history, alerts, track)
    stored = make_calendar(version=version, end=end, next_status=next_status, closed_dates=closed_dates)
    calendar_store = FakeCalendarStore(stored)
    publication = history.record(
        make_signal(), "PUBLISHED", datetime(2026, 10, 2, 10, tzinfo=CAIRO)
    )
    if bootstrap:
        BootstrapOpportunityLifecycle(
            history=history, calendar_store=calendar_store, unit_of_work=uow
        ).execute(
            calendar_version=stored.version,
            operator_id="operator-1",
            reason="bootstrap before activation",
            next_evaluation_date=bootstrap_next_date or next_date,
            recorded_at=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
        )
    schedule = FakeSchedule(next_date)
    evidence_store = FakeCalendarEvidenceStore(stored)
    validator = ValidateLifecycleCalendarActivation(
        history=history, calendar_store=calendar_store,
        unit_of_work=uow, schedule=schedule, evidence_store=evidence_store,
        authenticity_verifier=FakeAuthenticityVerifier(),
    )
    return validator, schedule, publication, uow, history, evidence_store


def test_calendar_activation_validation_accepts_complete_bootstrap_and_explicit_coverage():
    validator, schedule, _, _, _, _ = setup()
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is True
    assert result.checked_opportunity_count == 1
    assert result.blockers == ()
    assert schedule.received_after == date(2026, 10, 5)


def test_calendar_activation_validation_rejects_missing_bootstrap():
    validator, _, _, _, _, _ = setup(bootstrap=False)
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert result.blockers[0].code == "BOOTSTRAP_MISSING_OR_AMBIGUOUS"


def test_calendar_activation_validation_rejects_incomplete_candidate_coverage():
    validator, _, _, _, _, _ = setup(end=date(2026, 10, 5), bootstrap_next_date=date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "CALENDAR_COVERAGE_INCOMPLETE" for item in result.blockers)


def test_calendar_activation_validation_rejects_non_trading_next_evaluation_date():
    validator, _, _, _, _, _ = setup(next_status=CalendarDayStatus.NON_TRADING, bootstrap_next_date=date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "NEXT_EVALUATION_NOT_SCHEDULED" for item in result.blockers)


def test_calendar_activation_validation_fails_closed_without_trusted_schedule_date():
    validator, schedule, _, _, _, _ = setup()
    schedule.next_date = None
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert result.blockers[0].code == "NEXT_EVALUATION_DATE_UNAVAILABLE"



def test_calendar_activation_validation_rejects_schedule_date_not_after_today():
    validator, schedule, _, _, _, _ = setup(next_date=date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "NEXT_EVALUATION_DATE_NOT_FUTURE" for item in result.blockers)
    assert schedule.received_after == date(2026, 10, 5)



def make_bar(session_date):
    return CompletedDailyBarObservation(
        symbol="COMI",
        provider="attested-provider",
        timeframe="DAILY",
        candle_at=datetime.combine(session_date, time(14, 30), tzinfo=CAIRO),
        observed_at=datetime.combine(session_date, time(15, 40), tzinfo=CAIRO),
        revision="r1",
        source_reference=f"https://provider.example/COMI/{session_date.isoformat()}",
        finality_attestation="provider-finality-v1",
        is_final=True,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("98"),
        close=Decimal("102"),
    )


def record_cursor(uow, publication, session_date):
    uow.execute(lambda transaction: transaction.record_observation(
        LifecycleObservationRecord(
            signal_id=publication.signal_id,
            bar=make_bar(session_date),
            policy_version="lifecycle-policy-v1",
            calendar_version="calendar-v1",
            resulting_status=SignalStatus.ACTIVE,
        )
    ))


def test_calendar_activation_validation_requires_reconciled_cursor_to_be_closed():
    validator, _, publication, uow, _, _ = setup()
    record_cursor(uow, publication, date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "RECONCILED_CURSOR_NOT_CLOSED_IN_CANDIDATE" for item in result.blockers)


def test_calendar_activation_validation_accepts_closed_reconciled_cursor():
    validator, _, publication, uow, _, _ = setup(closed_dates={date(2026, 10, 5)})
    record_cursor(uow, publication, date(2026, 10, 5))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is True
    assert result.blockers == ()


def test_rollback_candidate_is_revalidated_against_latest_reconciled_cursor():
    validator, _, publication, uow, _, _ = setup(
        version="calendar-v2",
        closed_dates={date(2026, 10, 5)},
    )
    record_cursor(uow, publication, date(2026, 10, 5))
    # Revalidation happens at rollback time, using the cursor currently persisted,
    # not a previously cached validation result.
    result = validator.execute(
        calendar_version="calendar-v2",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is True
    assert result.checked_opportunity_count == 1



def test_calendar_activation_validation_allows_no_active_opportunities():
    validator, _, publication, _, history, _ = setup()
    history.record_for_signal(
        publication.signal_id,
        replace(publication.signal, status=SignalStatus.CLOSED),
        "CLOSED",
        datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is True
    assert result.checked_opportunity_count == 0
    assert result.blockers == ()



def test_calendar_activation_validation_rejects_cursor_on_publication_baseline():
    validator, _, publication, uow, _, _ = setup()
    record_cursor(uow, publication, date(2026, 10, 2))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "RECONCILED_CURSOR_NOT_AFTER_BASELINE" for item in result.blockers)


def test_calendar_activation_validation_requires_next_evaluation_after_cursor():
    validator, _, publication, uow, _, _ = setup()
    record_cursor(uow, publication, date(2026, 10, 6))
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(item.code == "NEXT_EVALUATION_NOT_AFTER_CURSOR" for item in result.blockers)



def test_calendar_activation_validator_uses_caller_owned_lifecycle_transaction(monkeypatch):
    validator, _, _, uow, _, _ = setup()
    transaction = uow.execute(lambda tx: tx)

    def nested_transaction_is_forbidden(*args, **kwargs):
        raise AssertionError("validator opened a nested lifecycle transaction")

    monkeypatch.setattr(uow, "execute", nested_transaction_is_forbidden)
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
        transaction=transaction,
    )

    assert result.eligible is True
    assert result.blockers == ()



def test_calendar_activation_rejects_day_without_linked_evidence():
    validator, _, _, _, _, evidence_store = setup()
    evidence_store.missing.add((date(2026, 10, 1), CalendarEvidenceKind.SCHEDULE))

    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )

    assert result.eligible is False
    assert any(item.code == "CALENDAR_DAY_EVIDENCE_MISSING" for item in result.blockers)


def test_calendar_activation_rejects_conflicting_unsuperseded_day_evidence():
    validator, _, _, _, _, evidence_store = setup()
    evidence_store.conflicting.add((date(2026, 10, 1), CalendarEvidenceKind.SCHEDULE))

    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )

    assert result.eligible is False
    assert any(item.code == "CALENDAR_DAY_EVIDENCE_CONFLICT" for item in result.blockers)


def test_calendar_activation_rejects_non_primary_or_non_egx_day_evidence():
    validator, _, _, _, _, evidence_store = setup()
    evidence_store.source_class = CalendarEvidenceSourceClass.A_R

    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )

    assert result.eligible is False
    assert any(item.code == "CALENDAR_DAY_PRIMARY_EVIDENCE_MISSING" for item in result.blockers)

def test_calendar_activation_fails_closed_when_authenticity_verifier_is_missing():
    validator, _, _, _, _, _ = setup()
    validator._authenticity_verifier = None
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(
        item.code == "CALENDAR_SOURCE_AUTHENTICITY_VERIFIER_NOT_CONFIGURED"
        for item in result.blockers
    )


class RejectingAuthenticityVerifier:
    def revalidate_for_activation(self, evidence, *, at):
        raise ValueError("origin is not owner-approved")

    def assert_preflight_verification(self, evidence, *, at):
        raise ValueError("no fresh source verification record")


def test_calendar_activation_fails_closed_when_source_authenticity_preflight_fails():
    validator, _, _, _, _, _ = setup()
    validator._authenticity_verifier = RejectingAuthenticityVerifier()
    result = validator.execute(
        calendar_version="calendar-v1",
        as_of=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )
    assert result.eligible is False
    assert any(
        item.code == "CALENDAR_SOURCE_AUTHENTICITY_UNVERIFIED"
        for item in result.blockers
    )

