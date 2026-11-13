from dataclasses import replace
from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from uuid import uuid4

from app.application.market_data.completed_daily_bar_source import ProviderDailyBarEvidence
from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.signals.evaluate_completed_daily_bar import EvaluateCompletedDailyBar
from app.domain.market_data.session_calendar import (
    CalendarDayStatus,
    EGXCalendarDay,
    EGXSessionCalendar,
)
from app.domain.signals.lifecycle import CompletedDailyBarObservation


CAIRO = ZoneInfo("Africa/Cairo")
SESSION_DATE = date(2026, 10, 4)


class FakeCalendarStore:
    def __init__(self, active):
        self.active = active

    def get_active(self):
        return self.active


class FakeFinalityVerifier:
    def __init__(self, accepted=True):
        self.accepted = accepted
        self.calls = 0
        self.last_evidence = None

    def verify_finality(self, evidence):
        self.calls += 1
        self.last_evidence = evidence
        return self.accepted


class FakeLifecycle:
    def __init__(self):
        self.calls = []

    def process_completed_daily_bar(self, signal_id, bar, *, policy_version, calendar_version):
        self.calls.append((signal_id, bar, policy_version, calendar_version))
        return SimpleNamespace(changed=False)


def make_calendar(status=CalendarDayStatus.CLOSED):
    closed_at = (
        datetime(2026, 10, 4, 14, 35, tzinfo=CAIRO)
        if status is CalendarDayStatus.CLOSED
        else None
    )
    day = EGXCalendarDay(
        session_date=SESSION_DATE,
        status=status,
        session_open=time(10, 0) if status is not CalendarDayStatus.NON_TRADING else None,
        session_close=time(14, 30) if status is not CalendarDayStatus.NON_TRADING else None,
        closed_at=closed_at,
    )
    calendar = EGXSessionCalendar(
        version="calendar-v1",
        timezone="Africa/Cairo",
        coverage_start=SESSION_DATE,
        coverage_end=SESSION_DATE,
        days=(day,),
    )
    return StoredCalendarVersion(
        version="calendar-v1",
        calendar=calendar,
        sha256="a" * 64,
        published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        published_by="operator-1",
        source_reference="operator-maintained-calendar",
        publication_reason="test",
    )


def make_bar():
    return CompletedDailyBarObservation(
        symbol="COMI",
        provider="test-provider",
        timeframe="DAILY",
        candle_at=datetime(2026, 10, 4, 14, 30, tzinfo=CAIRO),
        observed_at=datetime(2026, 10, 4, 15, 40, tzinfo=CAIRO),
        revision="r1",
        source_reference="https://provider.example/COMI/2026-10-04",
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


def evaluator(*, active, verified=True):
    verifier = FakeFinalityVerifier(verified)
    lifecycle = FakeLifecycle()
    service = EvaluateCompletedDailyBar(
        calendar_store=FakeCalendarStore(active),
        finality_verifier=verifier,
        lifecycle=lifecycle,
    )
    return service, verifier, lifecycle


def test_daily_bar_is_suppressed_without_an_active_calendar():
    service, verifier, lifecycle = evaluator(active=None)
    result = service.execute(
        uuid4(),
        make_evidence(make_bar()),
        evaluated_at=datetime(2026, 10, 4, 16, 0, tzinfo=CAIRO),
    )
    assert result.accepted is False
    assert result.reason == "NO_ACTIVE_EGX_SESSION_CALENDAR"
    assert verifier.calls == 0
    assert lifecycle.calls == []


def test_daily_bar_requires_explicit_closed_session_and_calendar_coverage():
    service, verifier, lifecycle = evaluator(
        active=make_calendar(CalendarDayStatus.SCHEDULED)
    )
    result = service.execute(
        uuid4(),
        make_evidence(make_bar()),
        evaluated_at=datetime(2026, 10, 4, 16, 0, tzinfo=CAIRO),
    )
    assert result.reason == "SESSION_NOT_EXPLICITLY_CLOSED"
    assert verifier.calls == 0
    assert lifecycle.calls == []


def test_daily_bar_requires_post_close_plus_sixty_minutes():
    service, verifier, lifecycle = evaluator(active=make_calendar())
    result = service.execute(
        uuid4(),
        make_evidence(make_bar()),
        evaluated_at=datetime(2026, 10, 4, 15, 20, tzinfo=CAIRO),
    )
    assert result.reason == "POST_CLOSE_BUFFER_NOT_ELAPSED"
    assert verifier.calls == 0
    assert lifecycle.calls == []


def test_daily_bar_requires_provider_finality_verification():
    service, verifier, lifecycle = evaluator(active=make_calendar(), verified=False)
    result = service.execute(
        uuid4(),
        make_evidence(make_bar()),
        evaluated_at=datetime(2026, 10, 4, 16, 0, tzinfo=CAIRO),
    )
    assert result.reason == "PROVIDER_FINALITY_NOT_VERIFIED"
    assert verifier.calls == 1
    assert lifecycle.calls == []


def test_daily_bar_evaluates_only_after_calendar_and_finality_gates_pass():
    service, verifier, lifecycle = evaluator(active=make_calendar())
    signal_id = uuid4()
    bar = make_bar()
    evidence = make_evidence(bar)
    result = service.execute(
        signal_id,
        evidence,
        evaluated_at=datetime(2026, 10, 4, 16, 0, tzinfo=CAIRO),
    )
    assert result.accepted is True
    assert result.reason == "EVALUATED"
    assert result.calendar_version == "calendar-v1"
    assert verifier.calls == 1
    assert verifier.last_evidence is evidence
    assert verifier.last_evidence.provider_contract_version == "test-contract-v1"
    assert lifecycle.calls == [(signal_id, bar, "dec139-completed-daily-bar-v1", "calendar-v1")]


def test_daily_bar_rejects_future_observation_timestamp():
    service, verifier, lifecycle = evaluator(active=make_calendar())
    bar = make_bar()
    result = service.execute(
        uuid4(),
        make_evidence(bar),
        evaluated_at=datetime(2026, 10, 4, 15, 30, tzinfo=CAIRO),
    )
    assert result.reason == "PROVIDER_EVIDENCE_FROM_FUTURE"
    assert verifier.calls == 0
    assert lifecycle.calls == []


def test_daily_bar_must_be_retrieved_after_the_post_close_buffer():
    service, verifier, lifecycle = evaluator(active=make_calendar())
    bar = make_evidence(replace(
        make_bar(),
        observed_at=datetime(2026, 10, 4, 15, 20, tzinfo=CAIRO),
    ))
    result = service.execute(
        uuid4(),
        bar,
        evaluated_at=datetime(2026, 10, 4, 16, 0, tzinfo=CAIRO),
    )
    assert result.reason == "POST_CLOSE_BUFFER_NOT_ELAPSED"
    assert verifier.calls == 0
    assert lifecycle.calls == []


def test_daily_bar_outside_active_calendar_coverage_is_suppressed():
    service, verifier, lifecycle = evaluator(active=make_calendar())
    bar = make_evidence(replace(
        make_bar(),
        candle_at=datetime(2026, 10, 5, 14, 30, tzinfo=CAIRO),
        observed_at=datetime(2026, 10, 5, 16, 0, tzinfo=CAIRO),
    ))
    result = service.execute(
        uuid4(),
        bar,
        evaluated_at=datetime(2026, 10, 5, 16, 0, tzinfo=CAIRO),
    )
    assert result.reason == "SESSION_OUTSIDE_CALENDAR_COVERAGE"
    assert verifier.calls == 0
    assert lifecycle.calls == []
