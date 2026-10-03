from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.market_intelligence.model import MarketOverview, MarketSnapshot


def test_market_overview_derives_breadth():
    snapshot = MarketSnapshot(
        market="EGX",
        timestamp=datetime(2026, 10, 4, tzinfo=timezone.utc),
        index_value=Decimal("40000"),
        index_change_percent=Decimal("1.2"),
        advancers=60,
        decliners=30,
        unchanged=10,
        traded_value=Decimal("1000000000"),
        active_symbols=100,
    )
    overview = MarketOverview.from_snapshot(snapshot)
    assert overview.breadth_ratio == Decimal("0.6666666666666666666666666667")
    assert overview.breadth_status == "ADVANCERS_DOMINANT"


def test_rejects_invalid_breadth_counts():
    with pytest.raises(ValueError):
        MarketSnapshot(
            market="EGX",
            timestamp=datetime.now(timezone.utc),
            index_value=None,
            index_change_percent=None,
            advancers=80,
            decliners=30,
            unchanged=0,
            traded_value=None,
            active_symbols=100,
        )
