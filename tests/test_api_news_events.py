from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.domain.news.event import NewsEvent, NewsEventCategory, NewsSourceType


class FakeNewsEventStore:
    def __init__(self, events: tuple[NewsEvent, ...]) -> None:
        self.events = events
        self.last_query = None

    def query_as_of(self, as_of, *, symbol=None, minimum_entity_confidence=Decimal("0.8"), limit=100):
        self.last_query = (as_of, symbol, minimum_entity_confidence, limit)
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if not minimum_entity_confidence.is_finite() or not Decimal("0") <= minimum_entity_confidence <= Decimal("1"):
            raise ValueError("minimum_entity_confidence must be between zero and one")
        return self.events[:limit]


def sample_event() -> NewsEvent:
    published = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    return NewsEvent(
        event_id=uuid4(),
        source_name="EGX",
        source_type=NewsSourceType.EXCHANGE_DISCLOSURE,
        source_url="https://beta.egx.com.eg/en/media-center",
        title="Company disclosure",
        category=NewsEventCategory.CORPORATE_ACTION,
        published_at=published,
        retrieved_at=published,
        first_seen_at=published,
        matched_symbols=("EGAL",),
        entity_match_confidence=Decimal("0.99"),
        content_fingerprint="sha256:test",
    )


def test_news_events_route_is_authenticated_and_returns_point_in_time_metadata() -> None:
    store = FakeNewsEventStore((sample_event(),))
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        news_event_store=store,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/news/events?symbol=egal&as_of=2026-10-26T15:00:00%2B00:00",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "EGAL"
    assert payload["count"] == 1
    assert payload["events"][0]["source_type"] == "exchange_disclosure"
    assert payload["events"][0]["entity_match_confidence"] == "0.99"
    assert store.last_query[1:] == ("EGAL", Decimal("0.8"), 100)


def test_news_events_route_rejects_naive_as_of_timestamp() -> None:
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        news_event_store=FakeNewsEventStore(()),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/news/events?as_of=2026-10-26T15:00:00",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 422
    assert "timezone" in response.json()["detail"]


def test_news_events_route_rejects_out_of_range_limit() -> None:
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        news_event_store=FakeNewsEventStore(()),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/news/events?limit=1001",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 422
    assert "limit" in response.json()["detail"]


def test_news_events_route_is_unavailable_when_store_is_not_configured() -> None:
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-operator-token")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/news/events",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 503



class FakeNewsIngestionService:
    def __init__(self):
        self.received_since = None

    def ingest(self, since=None):
        self.received_since = since
        from app.application.news.ingestion import NewsIngestionSummary

        return NewsIngestionSummary(
            source_name="Configured EGX Feed",
            fetched=3,
            inserted=2,
            duplicates=1,
        )


def test_operator_can_trigger_configured_news_ingestion() -> None:
    service = FakeNewsIngestionService()
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        news_ingestion_service=service,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/news/ingest?since=2026-10-25T00:00:00%2B00:00",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "source_name": "Configured EGX Feed",
        "fetched": 3,
        "inserted": 2,
        "duplicates": 1,
    }
    assert service.received_since == datetime(2026, 10, 25, tzinfo=timezone.utc)


def test_news_ingestion_route_is_unavailable_when_no_feed_is_configured() -> None:
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/news/ingest",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 503
    assert "EGX_NEWS_RSS_URL" in response.json()["detail"]


def test_news_ingestion_route_rejects_naive_since_timestamp() -> None:
    service = FakeNewsIngestionService()
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        news_ingestion_service=service,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/news/ingest?since=2026-10-25T00:00:00",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 422
    assert "timezone" in response.json()["detail"]


def test_news_ingestion_route_requires_operator_permission() -> None:
    from uuid import uuid4

    from app.application.security.identity import AuthenticatedIdentity
    from app.domain.identity.user import UserStatus

    class UserOnlyAuthenticator:
        def authenticate(self, authorization):
            return AuthenticatedIdentity.user(uuid4(), UserStatus.ACTIVE)

    app = create_app(
        InMemoryAnalysisResultStore(),
        authenticator=UserOnlyAuthenticator(),
        news_ingestion_service=FakeNewsIngestionService(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/news/ingest",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
