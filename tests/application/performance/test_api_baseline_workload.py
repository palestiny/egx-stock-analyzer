from fastapi.testclient import TestClient

from app.api.main import create_app


class _Store:
    def get(self, symbol, owner_user_id=None):
        class Result:
            technical_score = type("Score", (), {"total_score": 70})()
            fundamental_score = type("Score", (), {"total": 65})()
            stock_quality = type("Score", (), {"total_score": 68})()
            entry_quality = type("Score", (), {"total_score": 72})()
            opportunity = type(
                "Opportunity", (), {"classification": type("Classification", (), {"value": "WATCH"})()}
            )()

        return Result() if symbol == "COMI" else None


def test_deterministic_analysis_read_workload_contract() -> None:
    client = TestClient(create_app(_Store()))

    first = client.get("/api/v1/analysis/COMI")
    second = client.get("/api/v1/analysis/COMI")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json() == {
        "symbol": "COMI",
        "technical_score": 70,
        "fundamental_score": 65,
        "stock_quality": 68,
        "entry_quality": 72,
        "opportunity": "WATCH",
    }
