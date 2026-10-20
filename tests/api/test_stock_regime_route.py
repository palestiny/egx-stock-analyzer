from fastapi.testclient import TestClient

from app.main import app


def test_stock_regime_endpoint_returns_404_for_unknown_symbol() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/market-intelligence/regime/UNKNOWN_SYMBOL",
        headers={"Authorization": "Bearer test-operator-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown stock symbol: UNKNOWN_SYMBOL"}


def test_stock_regime_endpoint_requires_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/market-intelligence/regime/COMI")

    assert response.status_code == 401
