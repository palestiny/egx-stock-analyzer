import pytest
from fastapi.testclient import TestClient

from app.main import create_development_application_from_environment


@pytest.mark.integration
def test_egal_real_data_vertical_slice() -> None:
    app = create_development_application_from_environment()

    with TestClient(app) as client:
        analysis_response = client.post("/api/v1/analysis/EGAL")

        assert analysis_response.status_code == 200, analysis_response.text

        analysis_body = analysis_response.json()
        assert analysis_body["symbol"] == "EGAL"
        assert isinstance(analysis_body["technical_score"], int)
        assert isinstance(analysis_body["fundamental_score"], int)
        assert isinstance(analysis_body["stock_quality"], int)
        assert isinstance(analysis_body["entry_quality"], int)
        assert analysis_body["opportunity"] in {"buy", "watch", "hold", "avoid"}

        report_response = client.get("/api/v1/reports/EGAL")
        assert report_response.status_code == 200, report_response.text

        report_body = report_response.json()
        assert report_body["symbol"] == "EGAL"
        assert isinstance(report_body["analysis_date"], str)
        assert isinstance(report_body["technical_score"], int)
        assert isinstance(report_body["fundamental_score"], int)
        assert isinstance(report_body["stock_quality"], int)
        assert isinstance(report_body["entry_quality"], int)
        assert report_body["opportunity"] in {"buy", "watch", "hold", "avoid"}

        alert_response = client.get("/api/v1/alerts/EGAL")
        assert alert_response.status_code in {200, 404}, alert_response.text

        if alert_response.status_code == 200:
            alert_body = alert_response.json()
            assert alert_body["classification"] == "buy"
            assert isinstance(alert_body["stock_quality_score"], int)
            assert isinstance(alert_body["entry_quality_score"], int)
