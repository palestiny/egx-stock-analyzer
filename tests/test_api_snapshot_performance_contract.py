from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.calculate_snapshot_performance import CalculateSnapshotPerformance
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def make_result(price):
    return type('Result', (), {
        'entry_context': type('Context', (), {
            'current_price': type('Price', (), {'value': Decimal(price)})(),
        })(),
    })()


def make_app():
    stock = Stock.create('EGAL', 'Egypt Aluminum')
    store = InMemoryAnalysisResultStore()
    store.save('EGAL', make_result('100'), date(2026, 9, 1))
    store.save('EGAL', make_result('125'), date(2026, 9, 10))
    history = store.get_history('EGAL')
    capability = CalculateSnapshotPerformance(InMemoryStockCatalog([stock]), store)
    app = create_app(InMemoryAnalysisResultStore(), calculate_snapshot_performance=capability)
    return app, history[1], history[0]


def test_performance_endpoint_returns_price_metrics():
    app, before, after = make_app()
    with TestClient(app) as client:
        response = client.get(
            f'/api/v1/performance/EGAL?before={before.snapshot_id}&after={after.snapshot_id}'
        )

    assert response.status_code == 200
    body = response.json()
    assert body['symbol'] == 'EGAL'
    assert body['before']['current_price'] == 100.0
    assert body['after']['current_price'] == 125.0
    assert body['metrics']['price_change'] == 25.0
    assert body['metrics']['price_change_percent'] == 25.0


def test_performance_endpoint_returns_404_for_missing_snapshot():
    app, before, _ = make_app()
    from uuid import uuid4
    with TestClient(app) as client:
        response = client.get(
            f'/api/v1/performance/EGAL?before={before.snapshot_id}&after={uuid4()}'
        )
    assert response.status_code == 404


def test_performance_endpoint_returns_400_for_identical_snapshots():
    app, before, _ = make_app()
    with TestClient(app) as client:
        response = client.get(
            f'/api/v1/performance/EGAL?before={before.snapshot_id}&after={before.snapshot_id}'
        )
    assert response.status_code == 400