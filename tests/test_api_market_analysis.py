from datetime import date
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.domain.execution import Execution


def test_post_market_analysis_returns_execution_metadata():
    execution = Execution.create()
    execution.start()
    execution.record_stock_success("EGAL")
    execution.record_stock_failure("IEEC", "provider unavailable")
    execution.finish()

    capability = Mock(spec=RunConfiguredMarketAnalysis)
    capability.execute.return_value = execution

    app = create_app(
        InMemoryAnalysisResultStore(),
        run_configured_market_analysis=capability,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["execution_id"] == str(execution.id)
    assert body["state"] == "completed_with_errors"
    assert body["successful_stock_ids"] == ["EGAL"]
    assert body["failed_stock_ids"] == ["IEEC"]
    assert body["failure_reasons"] == {"IEEC": "provider unavailable"}
    capability.execute.assert_called_once()
    assert capability.execute.call_args.args[0] == date.today()


def test_post_market_analysis_returns_503_when_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 503
    assert response.json()["detail"] == "Market analysis execution is not configured"


def test_post_market_analysis_does_not_accept_symbol_list():
    execution = Execution.create()
    execution.start()
    execution.complete()

    capability = Mock(spec=RunConfiguredMarketAnalysis)
    capability.execute.return_value = execution

    app = create_app(
        InMemoryAnalysisResultStore(),
        run_configured_market_analysis=capability,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/market-analysis",
            params={"symbols": "EGAL,IEEC"},
        )

    assert response.status_code == 200
    capability.execute.assert_called_once()


def test_post_market_analysis_exposes_automatic_delivery_outcome():
    from app.application.analysis.run_configured_market_analysis_with_automatic_alerts import (
        ConfiguredMarketAnalysisResult,
    )
    from app.application.notifications.automatic_alert_delivery import (
        AutomaticAlertDeliveryResult,
        AutomaticAlertDeliveryState,
    )

    execution = Execution.create()
    execution.start()
    execution.record_stock_success("EGAL")
    execution.complete()
    delivery = AutomaticAlertDeliveryResult(
        state=AutomaticAlertDeliveryState.COMPLETED,
        attempted_count=1,
        delivered_count=1,
        skipped_count=0,
        failed_count=0,
        failure_reasons={},
    )

    capability = Mock()
    capability.execute.return_value = ConfiguredMarketAnalysisResult(
        execution=execution,
        automatic_alert_delivery=delivery,
    )

    app = create_app(
        InMemoryAnalysisResultStore(),
        run_configured_market_analysis_with_automatic_alerts=capability,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 200
    assert response.json()["automatic_alert_delivery"] == {
        "state": "completed",
        "attempted_count": 1,
        "delivered_count": 1,
        "skipped_count": 0,
        "failed_count": 0,
        "failure_reasons": {},
    }
    capability.execute.assert_called_once()
