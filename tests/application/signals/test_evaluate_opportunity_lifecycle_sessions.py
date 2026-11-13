from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.application.alerts.in_memory import InMemoryAlertPublisher
from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.signals.evaluate_opportunity_lifecycle_sessions import (
    EvaluateOpportunityLifecycleSessions,
)
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
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

    def verify_finality(self, bar):
        return bar.candle_at.astimezone(CAIRO).date() not in self.rejected_dates


def make_calendar():
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
        version="calendar-v1",
        timezone="Africa/Cairo",
        coverage_start=START,
        coverage_end=END,
        days=tuple(days),
    )
    return StoredCalendarVersion(
        version="calendar-v1",
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


def build_service(*, rejected_dates=()):
    calendar_store = FakeCalendarStore(make_calendar())
    verifier = FakeFinalityVerifier(rejected_dates)
    history = InMemorySignalHistoryStore()
    alerts = InMemoryAlertPublisher()
    track_record = InMemoryTrackRecordStore()
    lifecycle = SignalLifecycleOrchestrator(history, alerts, track_record)
    service = EvaluateOpportunityLifecycleSessions(
        calendar_store=calendar_store,
        finality_verifier=verifier,
        history=history,
        lifecycle=lifecycle,
    )
    signal = make_signal()
    publication = history.record(signal, "PUBLISHED", signal.generated_at)
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
    bars = {session: make_bar(session) for session in sessions}

    result = service.execute(
        publication.signal_id,
        through_date=sessions[-1],
        bars_by_session=bars,
        evaluated_at=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )

    assert result.status == "EXPIRED"
    assert result.processed_sessions == sessions
    assert result.lifecycle_result.signal.status is SignalStatus.EXPIRED
    assert history.get(publication.signal_id).signal.status is SignalStatus.EXPIRED
    assert alerts.events[-1].event_type.value == "SIGNAL_EXPIRED"
    assert track_record.all() == ()


def test_lifecycle_session_recovery_stops_at_first_missing_session_and_resumes():
    service, history, lifecycle, publication, alerts, track_record = build_service()
    sessions = expected_sessions()[:20]
    bars = {
        session: make_bar(session)
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

    bars[sessions[1]] = make_bar(sessions[1])
    recovered = service.execute(
        publication.signal_id,
        through_date=sessions[-1],
        bars_by_session=bars,
        evaluated_at=datetime(2026, 11, 5, 16, tzinfo=CAIRO),
    )

    assert recovered.status == "EXPIRED"
    assert recovered.processed_sessions == sessions[1:]
    assert history.get(publication.signal_id).signal.status is SignalStatus.EXPIRED
    assert track_record.all() == ()


def test_lifecycle_session_recovery_does_not_advance_on_unverified_bar():
    sessions = expected_sessions()[:3]
    service, history, lifecycle, publication, alerts, track_record = build_service(
        rejected_dates=(sessions[1],)
    )
    bars = {session: make_bar(session) for session in sessions}

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
