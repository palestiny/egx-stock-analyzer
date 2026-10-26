from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.domain.reporting.session_opportunity_ledger import SessionOpportunityLedgerReport


TOKEN = "test-operator-token"
NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


class FakeOverview:
    def execute(self, *, as_of=None):
        return {
            "as_of": (as_of or NOW).isoformat(),
            "availability": {"session_reports": False, "payment_reconciliation": False},
            "counts": {"subscriptions_by_status": {"ACTIVE": 2}},
            "integrations": {"telegram_transport_configured": True, "news_source_configured": False},
            "limitations": ["Session reports are not configured."],
        }


class FakeSignalGenerator:
    def __init__(self, signal):
        self.signal = signal
        self.symbols = []

    def execute(self, symbol):
        self.symbols.append(symbol)
        return self.signal


class FakePublisher:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, signal, *, recorded_at):
        self.calls.append((signal, recorded_at))
        return self.result


class FakeDispatcher:
    def __init__(self):
        self.calls = []

    def execute(self, *, now, limit=100):
        self.calls.append((now, limit))
        return SimpleNamespace(
            events_processed=3,
            recipients_delivered=4,
            recipients_suppressed=2,
            recipients_failed=1,
        )


def make_client(*, signal=None, publication=None, dispatcher=None, overview=None, ledger_builder=None, report_store=None):
    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        operator_token=TOKEN,
        generate_signal=FakeSignalGenerator(signal),
        publish_signal_opportunity=FakePublisher(publication),
        dispatch_signal_alert_outbox=dispatcher,
        get_owner_dashboard_overview=overview,
        build_session_opportunity_ledger=ledger_builder,
        session_opportunity_report_store=report_store,
    )
    return TestClient(app)


def test_owner_overview_is_operator_only_and_reports_unavailable_features() -> None:
    client = make_client(overview=FakeOverview())

    denied = client.get("/api/v1/owner/overview")
    assert denied.status_code == 401

    response = client.get(
        "/api/v1/owner/overview?as_of=2026-10-26T12:00:00Z",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    assert response.json()["availability"]["session_reports"] is False
    assert response.json()["integrations"]["news_source_configured"] is False


def test_publish_endpoint_queues_active_signal_without_claiming_delivery() -> None:
    signal = SimpleNamespace(symbol="EGAL", status="ACTIVE")
    publication = SimpleNamespace(
        signal_id=uuid4(),
        event_id=uuid4(),
        queued_new_event=True,
    )
    client = make_client(signal=signal, publication=publication)

    response = client.post(
        "/api/v1/opportunities/EGAL/publish",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json()["queued_new_event"] is True
    assert response.json()["delivery"] == "queued_not_yet_delivered"
    assert response.json()["signal_id"] == str(publication.signal_id)


def test_publish_endpoint_returns_not_found_when_no_actionable_signal_exists() -> None:
    client = make_client(signal=None, publication=None)

    response = client.post(
        "/api/v1/opportunities/EGAL/publish",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 404


def test_dispatch_endpoint_returns_recipient_delivery_counts() -> None:
    dispatcher = FakeDispatcher()
    client = make_client(dispatcher=dispatcher)

    response = client.post(
        "/api/v1/telegram/opportunities/dispatch?limit=25",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "events_processed": 3,
        "recipients_delivered": 4,
        "recipients_suppressed": 2,
        "recipients_failed": 1,
    }
    assert dispatcher.calls[0][1] == 25



class FakeLedgerBuilder:
    def execute(self, session_date, *, generated_at):
        return SessionOpportunityLedgerReport(
            session_date=session_date,
            generated_at=generated_at,
            exchange_timezone="Africa/Cairo",
            methodology_version="session-opportunity-ledger-v1",
            opportunities=(),
            unresolved_count=0,
            resolved_proxy_count=0,
        )


class FakeSessionReportStore:
    def __init__(self):
        self.saved = None

    def save(self, report):
        self.saved = report
        return True

    def get_latest(self, session_date, *, as_of=None):
        if self.saved is None or self.saved.session_date != session_date:
            return None
        return {
            "session_date": session_date.isoformat(),
            "generated_at": self.saved.generated_at.isoformat(),
            "total_count": self.saved.total_count,
            "opportunities": [],
        }


def test_session_report_endpoints_persist_and_read_as_of_snapshots() -> None:
    store = FakeSessionReportStore()
    client = make_client(ledger_builder=FakeLedgerBuilder(), report_store=store)

    generated = client.post(
        "/api/v1/session-opportunity-reports?session_date=2026-10-26&generated_at=2026-10-26T15:00:00Z",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert generated.status_code == 200
    assert generated.json()["persisted"] is True
    assert generated.json()["created"] is True
    assert generated.json()["total_count"] == 0

    saved = client.get(
        "/api/v1/session-opportunity-reports?session_date=2026-10-26&as_of=2026-10-26T16:00:00Z",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert saved.status_code == 200
    assert saved.json()["session_date"] == "2026-10-26"


def test_session_report_read_returns_not_found_before_first_snapshot() -> None:
    client = make_client(report_store=FakeSessionReportStore())
    response = client.get(
        "/api/v1/session-opportunity-reports?session_date=2026-10-26",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 404
