from datetime import date
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.domain.execution import Execution, ExecutionState


AS_OF = date(2026, 9, 18)


def execution(state: ExecutionState) -> Execution:
    result = Execution.create()
    result.start()
    if state is ExecutionState.COMPLETED:
        result.record_stock_success("EGAL")
        result.complete()
    elif state is ExecutionState.COMPLETED_WITH_ERRORS:
        result.record_stock_success("EGAL")
        result.record_stock_failure("IEEC", "provider unavailable")
        result.complete_with_errors()
    else:
        result.record_stock_failure("EGAL", "analysis failed")
        result.fail()
    return result


def test_post_market_analysis_executes_configured_universe():
    capability = Mock()
    capability.execute.return_value = execution(ExecutionState.COMPLETED)
    app = create_app(
        InMemoryAnalysisResultStore(),
        run_configured_market_analysis=capability,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "completed"
    assert body["successful_stock_ids"] == ["EGAL"]
    assert body["failed_stock_ids"] == []
    capability.execute.assert_called_once()
    assert capability.execute.call_args.args[0] == date.today()


def test_post_market_analysis_returns_partial_failures():
    capability = Mock()
    capability.execute.return_value = execution(ExecutionState.COMPLETED_WITH_ERRORS)
    app = create_app(
        InMemoryAnalysisResultStore(),
        run_configured_market_analysis=capability,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 200
    assert response.json()["state"] == "completed_with_errors"
    assert response.json()["failed_stock_ids"] == ["IEEC"]
    assert response.json()["failure_reasons"] == {"IEEC": "provider unavailable"}


def test_post_market_analysis_returns_503_when_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.post("/api/v1/market-analysis")

    assert response.status_code == 503
