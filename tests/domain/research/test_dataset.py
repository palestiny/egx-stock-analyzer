from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.research.dataset import PriceAdjustment, ResearchBar, ResearchCostConfig, ResearchDataQuality, ResearchRunConfig


def make_bar(**overrides) -> ResearchBar:
    values = {
        "symbol": "COMI", "timeframe": "1d",
        "source_timestamp": datetime(2026, 10, 7, tzinfo=timezone.utc),
        "ingestion_timestamp": datetime(2026, 10, 7, 16, tzinfo=timezone.utc),
        "open": Decimal("100"), "high": Decimal("105"), "low": Decimal("95"),
        "close": Decimal("102"), "volume": Decimal("1000"),
        "provider": "fixture", "dataset_version": "fixture-v1",
    }
    values.update(overrides)
    return ResearchBar(**values)


def test_research_bar_rejects_naive_source_timestamp():
    with pytest.raises(ValueError, match="source timestamp"):
        make_bar(source_timestamp=datetime(2026, 10, 7))


def test_research_bar_rejects_invalid_ohlc():
    with pytest.raises(ValueError, match="high"):
        make_bar(high=Decimal("101"), close=Decimal("102"))


def test_research_bar_rejects_negative_volume():
    with pytest.raises(ValueError, match="volume"):
        make_bar(volume=Decimal("-1"))


def test_non_valid_quality_is_explicit():
    bar = make_bar(quality=ResearchDataQuality.PARTIAL)
    assert bar.quality is ResearchDataQuality.PARTIAL


def test_costs_are_explicit_and_non_negative():
    config = ResearchCostConfig(commission_rate=Decimal("0.001"), slippage_rate=Decimal("0.002"))
    assert config.commission_rate == Decimal("0.001")


def test_negative_costs_are_rejected():
    with pytest.raises(ValueError, match="costs"):
        ResearchCostConfig(commission_rate=Decimal("-0.001"), slippage_rate=Decimal("0"))


def test_run_config_captures_reproducibility_identity():
    config = ResearchRunConfig(dataset_version="egx-fixture-v1", provider="fixture", strategy_id="breakout-trend", strategy_version="1.0", evaluator_version="research-1", adjustment=PriceAdjustment.UNADJUSTED)
    assert config.dataset_version == "egx-fixture-v1"
    assert config.strategy_id == "breakout-trend"
