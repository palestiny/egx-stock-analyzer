import os

import pytest
from fastapi.testclient import TestClient

from app.main import create_development_application_from_environment


@pytest.mark.integration
def test_egal_real_data_vertical_slice() -> None:
    if not os.getenv("FINNHUB_API_KEY"):
        pytest.skip("FINNHUB_API_KEY is required for the real-data vertical slice")

    app = create_development_application_from_environment()

    with TestClient(app) as client:
        response = client.post("/api/v1/analysis/EGAL")

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["symbol"] == "EGAL"
    assert isinstance(body["technical_score"], int)
    assert isinstance(body["fundamental_score"], int)
    assert isinstance(body["stock_quality"], int)
    assert isinstance(body["entry_quality"], int)
    assert body["opportunity"] in {"buy", "watch", "hold", "avoid"}
