from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient

from app.application.signals.calendar_backed_lifecycle_evaluation_schedule import (
    CalendarBackedLifecycleEvaluationSchedule,
)
from app.application.signals.validate_lifecycle_calendar_activation import (
    ValidateLifecycleCalendarActivation,
)
from app.domain.identity.user import User, UserStatus
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.persistence.sqlite_lifecycle_calendar_activation_coordinator import (
    SQLiteLifecycleCalendarActivationCoordinator,
)
from app.infrastructure.persistence.sqlite_signal_lifecycle_unit_of_work import (
    SQLiteSignalLifecycleUnitOfWork,
)
from app.infrastructure.runtime import create_infrastructure_runtime

from tests.test_infrastructure_runtime import FakeYFinanceModule
from tests.test_infrastructure_runtime import InMemoryAnalysisResultStore
from tests.test_infrastructure_runtime import RetryPolicy
from tests.test_infrastructure_runtime import Stock
from tests.test_infrastructure_runtime import InMemoryStockCatalog


def test_real_sqlite_authenticity_gate_blocks_and_then_allows_atomic_calendar_activation(
    tmp_path,
) -> None:
    content_by_url = {
        "https://calendar.example.test/notices/closure": b"fixture closure notice",
        "https://calendar.example.test/notices/session": b"fixture session notice",
    }

    class FakeRetriever:
        def retrieve(self, url: str):
            from app.application.market_data.calendar_source_authenticity import (
                RetrievedCalendarSourceArtifact,
            )

            return RetrievedCalendarSourceArtifact(
                requested_url=url,
                final_url=url,
                redirect_urls=(),
                tls_verified=True,
                status_code=200,
                content=content_by_url[url],
                content_type="application/pdf",
            )

    owner_id, uploader_id, reviewer_id = uuid4(), uuid4(), uuid4()
    database = tmp_path / "calendar-activation-authenticity.db"
    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([Stock.create("EGAL", "Egypt Aluminum")]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(
            operator_token="legacy-test-token",
            analysis_database_path=str(database),
            calendar_source_trust_owner_user_id=owner_id,
        ),
        result_store=InMemoryAnalysisResultStore(),
        retry_policy=RetryPolicy(1),
    )

    assert runtime.user_store is not None
    assert runtime.credential_service is not None
    assert runtime.operator_access_store is not None
    assert runtime.session_calendar_store is not None
    assert runtime.calendar_evidence_repository is not None
    assert runtime.calendar_source_origin_registry is not None
    assert runtime.calendar_source_authenticity_verifier is not None
    assert runtime.signal_history_store is not None
    assert runtime.signal_track_record_store is not None
    assert runtime.signal_alert_outbox is not None

    for user_id in (owner_id, uploader_id, reviewer_id):
        runtime.user_store.save(User(user_id, UserStatus.ACTIVE))
    owner_credential = runtime.credential_service.provision(owner_id)
    uploader_credential = runtime.credential_service.provision(uploader_id)
    reviewer_credential = runtime.credential_service.provision(reviewer_id)
    runtime.operator_access_store.bootstrap_first_operator(
        owner_id, reason="Activation authenticity integration fixture"
    )
    for user_id in (uploader_id, reviewer_id):
        runtime.operator_access_store.grant(
            user_id,
            actor_user_id=owner_id,
            actor_credential_id=owner_credential.id,
            reason="Independent operator fixture",
        )

    runtime.calendar_source_authenticity_verifier._retriever = FakeRetriever()
    app = __import__("app.main", fromlist=["create_application"]).create_application(
        runtime, operator_token="legacy-test-token"
    )

    with TestClient(app) as client:
        owner_headers = {"Authorization": "Bearer " + owner_credential.secret}
        uploader_headers = {"Authorization": "Bearer " + uploader_credential.secret}
        reviewer_headers = {"Authorization": "Bearer " + reviewer_credential.secret}

        approval = client.post(
            "/api/v1/owner/session-calendar-source-origins",
            headers=owner_headers,
            json={
                "origin": "https://calendar.example.test",
                "publisher": "EGX",
                "source_class": "A",
                "market_scope": "EGX_MARKET_WIDE",
                "trust_basis": "Isolated test fixture; not a production trust anchor",
                "registry_version": "activation-test-trust-v1",
            },
        )
        assert approval.status_code == 201

        evidence_specs = (
            {
                "session_date": "2026-11-13",
                "evidence_kind": "CLOSURE",
                "source_reference": "https://calendar.example.test/notices/closure",
                "claim": "EGX is closed on 2026-11-13",
                "content": content_by_url["https://calendar.example.test/notices/closure"],
            },
            {
                "session_date": "2026-11-16",
                "evidence_kind": "SCHEDULE",
                "source_reference": "https://calendar.example.test/notices/session",
                "claim": "EGX session is scheduled on 2026-11-16",
                "content": content_by_url["https://calendar.example.test/notices/session"],
            },
        )
        publication = client.post(
            "/api/v1/owner/session-calendars/versions",
            headers=uploader_headers,
            json={
                "version": "authenticity-activation-v1",
                "timezone": "Africa/Cairo",
                "coverage_start": "2026-11-13",
                "coverage_end": "2026-11-16",
                "days": [
                    {"date": "2026-11-13", "status": "NON_TRADING"},
                    {
                        "date": "2026-11-16",
                        "status": "SCHEDULED",
                        "session_open": "10:00",
                        "session_close": "14:30",
                    },
                ],
                "evidence": [
                    {
                        "session_date": item["session_date"],
                        "evidence_kind": item["evidence_kind"],
                        "source_type": "OFFICIAL_EXCHANGE_NOTICE",
                        "source_class": "A",
                        "source_publisher": "EGX",
                        "market_scope": "EGX_MARKET_WIDE",
                        "effective_from": item["session_date"],
                        "effective_through": item["session_date"],
                        "retrieved_at": "2026-11-12T09:00:00+02:00",
                        "artifact_sha256": sha256(item["content"]).hexdigest(),
                        "artifact_retention": "EXTERNAL_ONLY",
                        "artifact_not_retained_reason": "Test fixture does not retain external bytes",
                        "source_reference": item["source_reference"],
                        "claim": item["claim"],
                        "observed_at": "2026-11-12T09:00:00+02:00",
                    }
                    for item in evidence_specs
                ],
                "source_reference": "isolated activation authenticity fixture",
                "reason": "Test real authenticity gate with atomic activation",
            },
        )
        assert publication.status_code == 201
        evidence_ids = [item["evidence_id"] for item in publication.json()["evidence"]]
        assert len(evidence_ids) == 2

        for evidence_id, item in zip(evidence_ids, evidence_specs, strict=True):
            review = client.post(
                f"/api/v1/operator/session-calendars/evidence/{evidence_id}/authenticity-review",
                headers=reviewer_headers,
                json={"reviewed_claim": item["claim"], "claim_supported": True},
            )
            assert review.status_code == 201
            assert review.json()["decision"] == "VERIFIED"

        schedule = CalendarBackedLifecycleEvaluationSchedule(
            calendar_store=runtime.session_calendar_store,
            candidate_calendar_version="authenticity-activation-v1",
        )
        validator = ValidateLifecycleCalendarActivation(
            history=runtime.signal_history_store,
            calendar_store=runtime.session_calendar_store,
            unit_of_work=SQLiteSignalLifecycleUnitOfWork(
                runtime.signal_history_store,
                runtime.signal_track_record_store,
                runtime.signal_alert_outbox,
            ),
            schedule=schedule,
            evidence_store=runtime.calendar_evidence_repository,
            authenticity_verifier=runtime.calendar_source_authenticity_verifier,
        )
        unit_of_work = validator._unit_of_work
        coordinator = SQLiteLifecycleCalendarActivationCoordinator(
            calendar_repository=runtime.session_calendar_store,
            lifecycle_unit_of_work=unit_of_work,
            validator=validator,
        )

        failed_url = "https://calendar.example.test/notices/session"
        original_session_bytes = content_by_url[failed_url]
        content_by_url[failed_url] = b"changed bytes after independent review"
        failed_at = datetime(2026, 11, 13, 16, tzinfo=timezone(timedelta(hours=2)))
        rejected = coordinator.activate(
            "authenticity-activation-v1",
            performed_by="integration-test-owner",
            reason="Must reject changed source bytes",
            as_of=failed_at,
        )
        assert rejected.validation.eligible is False
        assert rejected.event is None
        assert runtime.session_calendar_store.get_active() is None
        assert runtime.session_calendar_store.list_activation_events() == ()

        content_by_url[failed_url] = original_session_bytes
        accepted_at = failed_at + timedelta(minutes=1)
        accepted = coordinator.activate(
            "authenticity-activation-v1",
            performed_by="integration-test-owner",
            reason="Activate after fresh independent source verification",
            as_of=accepted_at,
        )
        assert accepted.validation.eligible is True
        assert accepted.validation.blockers == ()
        assert accepted.event is not None
        assert accepted.event.action == "ACTIVATE"
        assert runtime.session_calendar_store.get_active() is not None
        assert runtime.session_calendar_store.get_active().version == "authenticity-activation-v1"
        assert len(runtime.session_calendar_store.list_activation_events()) == 1

    assert runtime.closed is True
