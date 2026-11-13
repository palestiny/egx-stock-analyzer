from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from zoneinfo import ZoneInfo

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.market_data.completed_daily_bar_source import ProviderDailyBarEvidence
from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.signals.evaluate_opportunity_lifecycle_sessions import (
    EvaluateOpportunityLifecycleSessions,
)
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
from app.application.signals.lifecycle_unit_of_work import (
    LifecycleBootstrapBatchRecord,
    LifecycleBootstrapRecord,
    InMemorySignalLifecycleUnitOfWork,
)
from app.application.signals.store import InMemorySignalHistoryStore
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.domain.signals.lifecycle import CompletedDailyBarObservation
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.application.signals.track_record import InMemoryTrackRecordStore
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.persistence.sqlite_lifecycle_occurrence_claim_store import (
    SQLiteLifecycleOccurrenceClaimStore,
    StaleLifecycleOccurrenceClaimError,
)
from app.infrastructure.persistence.sqlite_signal_history_store import SQLiteSignalHistoryStore
from app.infrastructure.persistence.sqlite_signal_lifecycle_unit_of_work import (
    SQLiteSignalLifecycleUnitOfWork,
)
from app.infrastructure.persistence.sqlite_track_record_store import SQLiteTrackRecordStore


CAIRO = ZoneInfo("Africa/Cairo")
START = date(2026, 10, 1)
END = date(2026, 11, 5)


class FakeCalendarStore:
    def __init__(self, active):
        self.active = active

    def get_active(self):
        return self.active


class FakeFinalityVerifier:
    def __init__(self, rejected_dates=()):
        self.rejected_dates = set(rejected_dates)

    def verify_finality(self, evidence):
        return evidence.bar.candle_at.astimezone(CAIRO).date() not in self.rejected_dates


def make_calendar(version="calendar-v1"):
    days = []
    current = START
    while current <= END:
        if current.weekday() not in (4, 5):
            days.append(
                EGXCalendarDay(
                    session_date=current,
                    status=CalendarDayStatus.CLOSED,
                    session_open=time(10, 0),
                    session_close=time(14, 30),
                    closed_at=datetime.combine(
                        current, time(14, 35), tzinfo=CAIRO
                    ),
                )
            )
        else:
            days.append(
                EGXCalendarDay(
                    session_date=current,
                    status=CalendarDayStatus.NON_TRADING,
                    session_open=None,
                    session_close=None,
                    closed_at=None,
                )
            )
        current += timedelta(days=1)

    calendar = EGXSessionCalendar(
        version=version,
        timezone="Africa/Cairo",
        coverage_start=START,
        coverage_end=END,
        days=tuple(days),
    )
    return StoredCalendarVersion(
        version=version,
        calendar=calendar,
        sha256="b" * 64,
        published_at=datetime(2026, 9, 30, 12, tzinfo=CAIRO),
        published_by="operator-1",
        source_reference="operator-maintained-calendar",
        publication_reason="lifecycle test",
    )


def make_signal():
    generated = datetime(2026, 10, 1, 9, tzinfo=CAIRO)
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=SignalStatus.ACTIVE,
        generated_at=generated,
        timeframe="DAILY",
        entry_zone=PriceZone(Decimal("99"), Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(Decimal("120"), "T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("trend", "trend evidence"),),
        strategy_id="breakout",
        strategy_version="1",
        data_timestamp=generated,
    )


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


def make_evidence(bar):
    return ProviderDailyBarEvidence(
        provider_id=bar.provider,
        provider_contract_version="test-contract-v1",
        instrument_symbol=bar.symbol,
        session_date=bar.candle_at.astimezone(CAIRO).date(),
        source_timestamp=bar.observed_at,
        retrieved_at=bar.observed_at,
        bar=bar,
    )


def build_service(
    *,
    rejected_dates=(),
    bootstrap=True,
    active_calendar_version="calendar-v1",
    database=None,
):
    calendar_store = FakeCalendarStore(make_calendar(active_calendar_version))
    verifier = FakeFinalityVerifier(rejected_dates)
    if database is None:
        history = InMemorySignalHistoryStore()
        alerts = InMemoryAlertPublisher()
        track_record = InMemoryTrackRecordStore()
        unit_of_work = InMemorySignalLifecycleUnitOfWork(history, alerts, track_record)
    else:
        history = SQLiteSignalHistoryStore(database)
        alerts = SQLiteAlertOutbox(database)
        track_record = SQLiteTrackRecordStore(database)
        claim_store = SQLiteLifecycleOccurrenceClaimStore(database)
        unit_of_work = SQLiteSignalLifecycleUnitOfWork(
            history, track_record, alerts, occurrence_claim_store=claim_store
        )
    lifecycle = SignalLifecycleOrchestrator(
        history, alerts, track_record, unit_of_work=unit_of_work
    )
    service = EvaluateOpportunityLifecycleSessions(
        calendar_store=calendar_store,
        finality_verifier=verifier,
        history=history,
        lifecycle=lifecycle,
    )
    signal = make_signal()
    publication = history.record(signal, "PUBLISHED", signal.generated_at)
    if bootstrap:
        batch_id = uuid4()
        batch = LifecycleBootstrapBatchRecord(
            batch_id=batch_id,
            calendar_version="calendar-v1",
            operator_id="test-operator",
            reason="test bootstrap",
            recorded_at=datetime(2026, 10, 1, 9, tzinfo=CAIRO),
            opportunity_count=1,
            batch_digest="c" * 64,
        )
        record = LifecycleBootstrapRecord(
            batch_id=batch_id,
            signal_id=publication.signal_id,
            baseline_date=publication.recorded_at.astimezone(CAIRO).date(),
            publication_event=publication.event,
            publication_recorded_at=publication.recorded_at,
            operator_id="test-operator",
            reason="test bootstrap",
            calendar_version="calendar-v1",
            recorded_at=batch.recorded_at,
            idempotency_key=f"{publication.signal_id}:calendar-v1",
        )
        unit_of_work.execute(lambda transaction: transaction.record_bootstrap_batch(batch, (record,)))
    return service, history, lifecycle, publication, alerts, track_record


def expected_sessions():
    return make_calendar().calendar.completed_sessions_between(
        START,
        END,
        as_of=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )


def test_lifecycle_session_recovery_processes_twenty_closed_sessions_then_expires():
    service, history, lifecycle, publication, alerts, track_record = build_service()
    sessions = expected_sessions()[:20]
    bars = {session: make_evidence(make_bar(session)) for session in sessions}

    result = service.execute(
        publication.signal_id,
        through_date=sessions[-1],
        bars_by_session=bars,
        evaluated_at=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )

    assert result.status == "EXPIRED"
    assert result.processed_sessions == sessions
    assert publication.recorded_at.astimezone(CAIRO).date() not in result.processed_sessions
    assert len(result.processed_sessions) == 20
    assert result.lifecycle_result.signal.status is SignalStatus.EXPIRED
    assert history.get(publication.signal_id).signal.status is SignalStatus.EXPIRED
    assert alerts.events[-1].event_type.value == "SIGNAL_EXPIRED"
    assert track_record.all() == ()


def test_lifecycle_session_recovery_stops_at_first_missing_session_and_resumes():
    service, history, lifecycle, publication, alerts, track_record = build_service()
    sessions = expected_sessions()[:20]
    bars = {
        session: make_evidence(make_bar(session))
        for index, session in enumerate(sessions)
        if index != 1
    }

    first_run = service.execute(
        publication.signal_id,
        through_date=sessions[-1],
        bars_by_session=bars,
        evaluated_at=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )
    assert first_run.status == "STALE_SESSION_DATA_GAP"
    assert first_run.processed_sessions == (sessions[0],)
    assert first_run.gap_session_date == sessions[1]
    assert history.get(publication.signal_id).signal.status is SignalStatus.ACTIVE
    stale_events = lifecycle.session_gap_events(publication.signal_id)
    assert [(event.session_date, event.status) for event in stale_events] == [
        (sessions[1], "STALE")
    ]

    bars[sessions[1]] = make_evidence(make_bar(sessions[1]))
    recovered = service.execute(
        publication.signal_id,
        through_date=sessions[-1],
        bars_by_session=bars,
        evaluated_at=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )

    assert recovered.status == "EXPIRED"
    assert recovered.processed_sessions == sessions[1:]
    assert history.get(publication.signal_id).signal.status is SignalStatus.EXPIRED
    recovered_gap_events = lifecycle.session_gap_events(publication.signal_id)
    assert [(event.session_date, event.status) for event in recovered_gap_events] == [
        (sessions[1], "STALE"),
        (sessions[1], "RESOLVED"),
    ]
    assert track_record.all() == ()


def test_lifecycle_session_recovery_does_not_advance_on_unverified_bar():
    sessions = expected_sessions()[:3]
    service, history, lifecycle, publication, alerts, track_record = build_service(
        rejected_dates=(sessions[1],)
    )
    bars = {session: make_evidence(make_bar(session)) for session in sessions}

    result = service.execute(
        publication.signal_id,
        through_date=sessions[-1],
        bars_by_session=bars,
        evaluated_at=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )

    assert result.status == "PROVIDER_FINALITY_NOT_VERIFIED"
    assert result.processed_sessions == (sessions[0],)
    assert result.gap_session_date == sessions[1]
    cursor = lifecycle.latest_completed_observation(publication.signal_id)
    assert cursor.bar.candle_at.astimezone(CAIRO).date() == sessions[0]
    gap_events = lifecycle.session_gap_events(publication.signal_id)
    assert gap_events[-1].status == "STALE"
    assert gap_events[-1].reason == "PROVIDER_FINALITY_NOT_VERIFIED"


def test_lifecycle_session_recovery_stops_after_target_transition():
    service, history, lifecycle, publication, alerts, track_record = build_service()
    sessions = expected_sessions()[:5]
    bars = {session: make_evidence(make_bar(session)) for session in sessions}
    bars[sessions[0]] = make_evidence(replace(
        bars[sessions[0]].bar,
        high=Decimal("121"),
        close=Decimal("110"),
        source_reference="https://provider.example/COMI/target-hit",
    ))

    result = service.execute(
        publication.signal_id,
        through_date=sessions[-1],
        bars_by_session=bars,
        evaluated_at=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )

    assert result.status == "TERMINAL_TRANSITION"
    assert result.processed_sessions == (sessions[0],)
    assert history.get(publication.signal_id).signal.status is SignalStatus.TRIGGERED
    assert alerts.events[-1].event_type.value == "SIGNAL_TRIGGERED"
    assert track_record.all() == ()

 
 
def test_lifecycle_evaluation_requires_a_publication_bootstrap_record():
    service, _, lifecycle, publication, _, _ = build_service(bootstrap=False)

    result = service.execute(
        publication.signal_id,
        through_date=date(2026, 10, 5),
        bars_by_session={},
        evaluated_at=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )

    assert result.status == "LIFECYCLE_BOOTSTRAP_REQUIRED"
    assert lifecycle.latest_completed_observation(publication.signal_id) is None


def test_lifecycle_evaluation_rejects_parent_revision_after_newer_revision_exists():
    service, history, lifecycle, publication, _, _ = build_service()
    revised = replace(make_signal(), confidence=Decimal("85"))
    history.record_revision(
        revised,
        "PUBLISHED_VERSION",
        datetime(2026, 10, 2, 11, tzinfo=CAIRO),
        parent_signal_id=publication.signal_id,
        reason="material opportunity revision",
    )

    result = service.execute(
        publication.signal_id,
        through_date=date(2026, 10, 5),
        bars_by_session={},
        evaluated_at=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )

    assert result.status == "NOT_LATEST_OPPORTUNITY_REVISION"
    assert lifecycle.latest_completed_observation(publication.signal_id) is None



def test_lifecycle_evaluation_requires_bootstrap_for_the_active_calendar_version():
    service, _, lifecycle, publication, _, _ = build_service(
        active_calendar_version="calendar-v2"
    )

    result = service.execute(
        publication.signal_id,
        through_date=date(2026, 10, 5),
        bars_by_session={},
        evaluated_at=datetime(2026, 10, 5, 16, tzinfo=CAIRO),
    )

    assert result.status == "LIFECYCLE_BOOTSTRAP_REQUIRED"
    assert lifecycle.latest_completed_observation(publication.signal_id) is None



def test_session_evaluator_uses_caller_owned_transaction_for_gap_and_recovery():
    service, history, lifecycle, publication, alerts, track_record = build_service()
    unit_of_work = lifecycle._unit_of_work
    transaction = unit_of_work.execute(lambda current: current)

    def reject_nested_unit_of_work(_operation):
        raise AssertionError("worker evaluation must not open a nested unit of work")

    unit_of_work.execute = reject_nested_unit_of_work
    session = expected_sessions()[0]
    cutoff = datetime(2026, 10, 2, 16, tzinfo=CAIRO)

    gap = service.execute(
        publication.signal_id,
        through_date=session,
        bars_by_session={},
        evaluated_at=cutoff,
        transaction=transaction,
    )
    assert gap.status == "STALE_SESSION_DATA_GAP"
    assert [
        (event.session_date, event.status)
        for event in transaction.session_gap_events(publication.signal_id)
    ] == [(session, "STALE")]

    recovered = service.execute(
        publication.signal_id,
        through_date=session,
        bars_by_session={session: make_evidence(make_bar(session))},
        evaluated_at=cutoff,
        transaction=transaction,
    )

    assert recovered.status == "EVALUATED"
    assert recovered.processed_sessions == (session,)
    assert transaction.latest_observation(publication.signal_id).bar == make_bar(session)
    assert [
        (event.session_date, event.status)
        for event in transaction.session_gap_events(publication.signal_id)
    ] == [(session, "STALE"), (session, "RESOLVED")]
    assert history.get(publication.signal_id).signal.status is SignalStatus.ACTIVE
    assert len(alerts.events) == 0
    assert track_record.all() == ()



def test_sqlite_claim_fence_rolls_back_real_session_evaluator_effects(tmp_path):
    database = tmp_path / "lifecycle-claim-atomicity.db"
    service, history, lifecycle, publication, alerts, track_record = build_service(
        database=database
    )
    unit_of_work = lifecycle._unit_of_work
    claim_store = SQLiteLifecycleOccurrenceClaimStore(database)
    claim_time = datetime(2026, 10, 2, 16, tzinfo=CAIRO)
    claim = claim_store.claim(
        "sqlite-session-evaluator-atomicity",
        "worker-a",
        now=claim_time,
        lease_seconds=10,
    )
    assert claim is not None

    session = expected_sessions()[0]
    target_bar = replace(
        make_bar(session),
        high=Decimal("121"),
        close=Decimal("110"),
        source_reference="https://provider.example/COMI/atomicity-target-hit",
    )
    clock_values = iter((
        claim_time + timedelta(seconds=1),
        claim_time + timedelta(seconds=11),
    ))

    with pytest.raises(StaleLifecycleOccurrenceClaimError):
        unit_of_work.execute_claimed(
            claim,
            lambda transaction: service.execute(
                publication.signal_id,
                through_date=session,
                bars_by_session={session: make_evidence(target_bar)},
                evaluated_at=claim_time,
                transaction=transaction,
            ),
            clock=lambda: next(clock_values),
        )

    # The evaluator really attempted an observation, status transition and
    # outbox write, but expiry at the commit fence must roll all of them back.
    assert len(history.history(publication.signal_id)) == 1
    assert history.get(publication.signal_id).signal.status is SignalStatus.ACTIVE
    assert lifecycle.latest_completed_observation(publication.signal_id) is None
    assert lifecycle.session_gap_events(publication.signal_id) == ()
    assert alerts.pending() == ()
    assert track_record.all() == ()
    persisted_claim = claim_store.get("sqlite-session-evaluator-atomicity")
    assert persisted_claim is not None
    assert persisted_claim["status"] == "CLAIMED"
