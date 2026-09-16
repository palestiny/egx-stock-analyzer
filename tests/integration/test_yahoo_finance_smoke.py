from datetime import date, timedelta
import os

import pytest

from app.domain.market_data.data_quality_assessor import DataQualityAssessor
from app.domain.market_data.data_quality import DataQualityStatus
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.price_bar_factory import PriceBarFactory
from app.domain.stocks.stock import Stock
from app.infrastructure.market_data.yahoo_finance import (
    YahooFinanceAdapter,
    YahooFinanceHistoryClient,
)


@pytest.mark.skipif(
    os.getenv("RUN_YAHOO_SMOKE") != "1",
    reason="Set RUN_YAHOO_SMOKE=1 to run the live Yahoo Finance smoke test",
)
def test_comi_yahoo_to_price_bar_smoke() -> None:
    import yfinance

    stock = Stock.create("COMI", "Commercial International Bank")
    client = YahooFinanceHistoryClient(yfinance)
    adapter = YahooFinanceAdapter(client)

    to_date = date.today()
    from_date = to_date - timedelta(days=30)

    observations = adapter.get_daily_observations(
        stock,
        from_date,
        to_date,
    )

    assert observations

    assessments = DataQualityAssessor.assess(observations)

    assert len(assessments) == len(observations)
    assert all(
        assessment.status is DataQualityStatus.VALID
        for assessment in assessments
    )

    price_bars = [
        PriceBarFactory.create(observation, assessment)
        for observation, assessment in zip(observations, assessments)
    ]

    assert price_bars
    assert all(type(price_bar) is PriceBar for price_bar in price_bars)
    assert all(price_bar.stock_id == stock.id for price_bar in price_bars)
