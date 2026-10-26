from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock
from app.domain.technical_analysis.indicator_evidence import (
    TechnicalIndicatorEvidence,
    TechnicalIndicatorPoint,
)


def indicator_point(day: int) -> TechnicalIndicatorPoint:
    return TechnicalIndicatorPoint(
        timestamp=datetime(2026, 10, day, tzinfo=timezone.utc),
        close=Decimal("10.25"),
        sma_20=None, sma_50=None, sma_200=None,
        ema_9=None, ema_20=None, ema_50=None, ema_200=None,
        rsi_14=None, macd_line=None, macd_signal=None, macd_histogram=None,
        bollinger_upper=None, bollinger_middle=None, bollinger_lower=None,
        atr_14=None, stochastic_k_14=None, stochastic_d_3=None,
        cci_20=None, obv=0, mfi_14=None, plus_di_14=None, minus_di_14=None,
        adx_14=None, ichimoku_conversion_9=None, ichimoku_base_26=None,
        ichimoku_span_a_unshifted=None, ichimoku_span_b_unshifted=None,
        candlestick_patterns=(),
    )


def test_technical_indicator_route_returns_bounded_history() -> None:
    result = SimpleNamespace(
        technical_analysis=SimpleNamespace(
            timeframe=Timeframe.DAILY,
            indicators=TechnicalIndicatorEvidence(
                (indicator_point(1), indicator_point(2), indicator_point(3))
            ),
            trend=SimpleNamespace(status=SimpleNamespace(value="uptrend")),
            momentum=SimpleNamespace(status=SimpleNamespace(value="positive")),
            volume=SimpleNamespace(status=SimpleNamespace(value="above_average")),
        ),
        fundamental_analysis=SimpleNamespace(
            period_end=date(2026, 6, 30),
            profitability=SimpleNamespace(status=SimpleNamespace(value="profitable")),
            liquidity=SimpleNamespace(status=SimpleNamespace(value="above_one")),
            growth=SimpleNamespace(status=SimpleNamespace(value="positive")),
        ),
        stock_quality=SimpleNamespace(
            technical_score=SimpleNamespace(total_score=26),
            fundamental_score=SimpleNamespace(total=21),
            total_score=47,
        ),
        entry_context=SimpleNamespace(
            current_price=SimpleNamespace(value=Decimal("10")),
            nearest_support=None,
            nearest_resistance=None,
        ),
        entry_quality=SimpleNamespace(total_score=2),
        opportunity=SimpleNamespace(classification=SimpleNamespace(value="watch")),
    )
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", result, analysis_date=date(2026, 10, 3))
    app = create_app(
        store,
        get_analysis_report=GetAnalysisReport(InMemoryStockCatalog([stock]), store),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/technical-indicators/EGAL?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "EGAL"
    assert payload["timeframe"] == Timeframe.DAILY.value
    assert payload["returned_points"] == 2
    assert payload["total_points"] == 3
    assert payload["points"][0]["close"] == "10.25"


def test_technical_indicator_route_rejects_invalid_limit() -> None:
    app = create_app(InMemoryAnalysisResultStore(), get_analysis_report=GetAnalysisReport(
        InMemoryStockCatalog([Stock.create("EGAL", "Egypt Aluminum")]),
        InMemoryAnalysisResultStore(),
    ))
    with TestClient(app) as client:
        response = client.get("/api/v1/technical-indicators/EGAL?limit=1001")
    assert response.status_code == 400
