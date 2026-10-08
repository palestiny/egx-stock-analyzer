from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.research.dataset import ResearchBar, ResearchDataQuality, validate_research_bars


def bar(day: int, **overrides) -> ResearchBar:
    values = {"symbol":"COMI","timeframe":"1d","source_timestamp":datetime(2026,10,day,tzinfo=timezone.utc),"ingestion_timestamp":datetime(2026,10,day,16,tzinfo=timezone.utc),"open":Decimal("100"),"high":Decimal("105"),"low":Decimal("95"),"close":Decimal("102"),"volume":Decimal("1000"),"provider":"fixture","dataset_version":"fixture-v1"}
    values.update(overrides)
    return ResearchBar(**values)


def test_rejects_future_data_at_point_in_time():
    with pytest.raises(ValueError, match="future data"): validate_research_bars((bar(7),), as_of=datetime(2026,10,6,23,tzinfo=timezone.utc))


def test_rejects_duplicate_timestamp():
    with pytest.raises(ValueError, match="duplicate"): validate_research_bars((bar(7),bar(7)))


def test_rejects_out_of_order_bars():
    with pytest.raises(ValueError, match="ordered"): validate_research_bars((bar(8),bar(7)))


def test_rejects_non_valid_quality():
    with pytest.raises(ValueError, match="research-ineligible"): validate_research_bars((bar(7,quality=ResearchDataQuality.PARTIAL),))


def test_accepts_valid_point_in_time_series():
    validate_research_bars((bar(6),bar(7)), as_of=datetime(2026,10,7,23,tzinfo=timezone.utc))


def test_rejects_mixed_symbols_in_one_series():
    with pytest.raises(ValueError, match="share symbol"):
        validate_research_bars((bar(6), bar(7, symbol="EGAL")))


def test_rejects_mixed_adjustment_modes_in_one_series():
    from app.domain.research.dataset import PriceAdjustment

    with pytest.raises(ValueError, match="share symbol"):
        validate_research_bars((bar(6), bar(7, adjustment=PriceAdjustment.ADJUSTED)))
