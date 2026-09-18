from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.analysis.input_assembler import (
    AnalysisInputAssembler,
    AnalysisInputAssemblyPolicy,
)
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe


STOCK_ID = uuid4()


def observation(day: int, *, valid: bool = True) -> RawPriceBarObservation:
    return RawPriceBarObservation(
        stock_id=STOCK_ID,
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 9, day, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("110") if valid else Decimal("90"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=1000,
    )


def test_invalid_observation_is_excluded_when_enough_valid_data_remains():
    observations = [
        observation(1),
        observation(2, valid=False),
        observation(3),
        observation(4),
        observation(5),
        observation(6),
    ]

    result = AnalysisInputAssembler._build_price_bars(
        observations,
        minimum_price_bars=5,
    )

    assert len(result) == 5
    assert all(bar.timestamp.day != 2 for bar in result)


def test_suspect_duplicate_observations_are_excluded():
    observations = [
        observation(1),
        observation(1),
        observation(2),
        observation(3),
    ]

    result = AnalysisInputAssembler._build_price_bars(
        observations,
        minimum_price_bars=3,
    )

    assert len(result) == 2
    assert [bar.timestamp.day for bar in result] == [2, 3]


def test_insufficient_valid_observations_fail_with_data_sufficiency_error():
    observations = [
        observation(1),
        observation(2, valid=False),
        observation(3),
    ]

    with pytest.raises(ValueError, match="Insufficient valid market data observations"):
        AnalysisInputAssembler._build_price_bars(
            observations,
            minimum_price_bars=3,
        )


def test_minimum_price_bars_supports_the_largest_technical_lookback():
    policy = AnalysisInputAssemblyPolicy(
        momentum_lookback=10,
        volume_lookback=5,
    )

    assert policy.minimum_price_bars == 11


def test_minimum_price_bars_uses_volume_lookback_when_larger():
    policy = AnalysisInputAssemblyPolicy(
        momentum_lookback=5,
        volume_lookback=10,
    )

    assert policy.minimum_price_bars == 11
