from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.market_data.data_quality import (
    DataQualityAssessment,
    DataQualityIssue,
    DataQualityIssueCode,
    DataQualityStatus,
)
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.price_bar_factory import PriceBarFactory
from app.domain.market_data.timeframe import Timeframe


def valid_observation() -> RawPriceBarObservation:
    return RawPriceBarObservation(
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        timestamp=datetime(2026, 1, 5, tzinfo=timezone.utc),
        open=Decimal("10.00"),
        high=Decimal("11.00"),
        low=Decimal("9.50"),
        close=Decimal("10.50"),
        volume=1000,
    )


def assessment(status: DataQualityStatus) -> DataQualityAssessment:
    return DataQualityAssessment(status=status)


def test_valid_observation_converts_to_price_bar() -> None:
    observation = valid_observation()

    result = PriceBarFactory.create(
        observation,
        assessment(DataQualityStatus.VALID),
    )

    assert isinstance(result, PriceBar)
    assert result.stock_id == observation.stock_id
    assert result.timeframe == observation.timeframe
    assert result.timestamp == observation.timestamp
    assert result.open.value == observation.open
    assert result.high.value == observation.high
    assert result.low.value == observation.low
    assert result.close.value == observation.close
    assert result.volume.value == observation.volume


@pytest.mark.parametrize(
    "status",
    [
        DataQualityStatus.SUSPECT,
        DataQualityStatus.INVALID,
        DataQualityStatus.UNKNOWN,
    ],
)
def test_non_valid_observation_is_rejected(status: DataQualityStatus) -> None:
    with pytest.raises(ValueError, match="must be VALID"):
        PriceBarFactory.create(
            valid_observation(),
            assessment(status),
        )


def test_factory_does_not_mutate_inputs() -> None:
    observation = valid_observation()
    quality = DataQualityAssessment(
        status=DataQualityStatus.VALID,
        issues=(),
    )

    PriceBarFactory.create(observation, quality)

    assert observation.open == Decimal("10.00")
    assert quality.status is DataQualityStatus.VALID
    assert quality.issues == ()


def test_conversion_is_deterministic() -> None:
    observation = valid_observation()
    quality = assessment(DataQualityStatus.VALID)

    first = PriceBarFactory.create(observation, quality)
    second = PriceBarFactory.create(observation, quality)

    assert first == second
