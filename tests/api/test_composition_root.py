from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore


EXPECTED_PATHS = {
    "/health",
    "/api/v1/auth/me",
    "/api/v1/analysis/{symbol}",
    "/api/v1/history/{symbol}",
    "/api/v1/reports/{symbol}",
    "/api/v1/analysis-runs",
    "/api/v1/analysis-runs/{run_id}",
    "/api/v1/analysis-snapshots/{snapshot_id}",
    "/api/v1/comparisons/{symbol}",
    "/api/v1/performance/{symbol}",
    "/api/v1/management/audit",
    "/api/v1/users/me/audit",
    "/api/v1/users",
    "/api/v1/users/{user_id}/status",
    "/api/v1/users/{user_id}/credentials/rotate",
    "/api/v1/users/me/credentials/rotate",
    "/api/v1/workflows/executions",
    "/api/v1/workflows/history",
    "/api/v1/workflows/executions/{execution_id}/history",
    "/api/v1/workflows/executions/{execution_id}/recover",
    "/api/v1/market-analysis",
    "/api/v1/opportunities",
    "/api/v1/alerts/{symbol}",
    "/api/v1/alerts/{symbol}/deliver",
}


def test_composition_root_registers_each_api_route_once() -> None:
    app = create_app(InMemoryAnalysisResultStore())

    routes = [
        route
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/")
        or getattr(route, "path", "") == "/health"
    ]
    route_keys = [(route.path, tuple(sorted(route.methods or ()))) for route in routes]

    assert {route.path for route in routes} == EXPECTED_PATHS
    assert len(route_keys) == len(set(route_keys))
