from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.market_data.data_quality import (
    DataQualityIssueCode,
    DataQualityStatus,
)
from app.domain.market_data.data_quality_assessor import DataQualityAssessor
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe


STOCK_ID = uuid4()
TIMESTAMP = datetime(2026, 9, 16, tzinfo=timezone.utc)


def observation(**overrides) -> RawPriceBarObservation:
    values = {
        "stock_id": STOCK_ID,
        "timeframe": Timeframe.DAILY,
        "timestamp": TIMESTAMP,
        "open": Decimal("100"),
        "high": Decimal("110"),
        "low": Decimal("95"),
        "close": Decimal("105"),
        "volume": 1000,
    }
    values.update(overrides)
    return RawPriceBarObservation(**values)


def test_valid_observation_is_valid_and_eligible():
    result = DataQualityAssessor.assess([observation()])

    assert result[0].status is DataQualityStatus.VALID
    assert result[0].issues == ()
    assert result[0].is_eligible_for_analysis() is True


def test_missing_value_is_invalid():
    result = DataQualityAssessor.assess([observation(close=None)])

    assert result[0].status is DataQualityStatus.INVALID
    assert DataQualityIssueCode.MISSING_VALUE in {
        issue.code for issue in result[0].issues
    }


def test_negative_price_or_volume_is_invalid():
    result = DataQualityAssessor.assess([observation(low=Decimal("-1"), volume=-1)])

    assert result[0].status is DataQualityStatus.INVALID
    assert DataQualityIssueCode.INVALID_VALUE in {
        issue.code for issue in result[0].issues
    }


@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
@pytest.mark.parametrize(
    "value",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_non_positive_or_non_finite_ohlc_is_invalid(field, value):
    result = DataQualityAssessor.assess([observation(**{field: value})])

    assert result[0].status is DataQualityStatus.INVALID
    assert DataQualityIssueCode.INVALID_VALUE in {
        issue.code for issue in result[0].issues
    }


def test_naive_timestamp_is_invalid():
    result = DataQualityAssessor.assess(
        [observation(timestamp=datetime(2026, 9, 16))]
    )

    assert result[0].status is DataQualityStatus.INVALID
    assert DataQualityIssueCode.INVALID_TIMESTAMP in {
        issue.code for issue in result[0].issues
    }


def test_inconsistent_ohlc_is_invalid():
    result = DataQualityAssessor.assess(
        [observation(high=Decimal("90"))]
    )

    assert result[0].status is DataQualityStatus.INVALID
    assert DataQualityIssueCode.OHLC_INCONSISTENCY in {
        issue.code for issue in result[0].issues
    }


def test_duplicate_observation_is_suspect():
    first = observation()
    second = observation()

    result = DataQualityAssessor.assess([first, second])

    assert result[0].status is DataQualityStatus.SUSPECT
    assert result[1].status is DataQualityStatus.SUSPECT
    assert all(
        DataQualityIssueCode.DUPLICATE_OBSERVATION in {
            issue.code for issue in assessment.issues
        }
        for assessment in result
    )


def test_invalid_issue_takes_precedence_over_duplicate():
    first = observation(close=None)
    second = observation(close=None)

    result = DataQualityAssessor.assess([first, second])

    assert result[0].status is DataQualityStatus.INVALID
    assert result[1].status is DataQualityStatus.INVALID
    assert {
        issue.code for issue in result[0].issues
    } == {
        DataQualityIssueCode.MISSING_VALUE,
        DataQualityIssueCode.DUPLICATE_OBSERVATION,
    }


def test_empty_input_produces_empty_assessment_result():
    assert DataQualityAssessor.assess([]) == ()


def test_assessment_is_deterministic():
    observations = [
        observation(),
        observation(timestamp=datetime(2026, 9, 17, tzinfo=timezone.utc)),
    ]

    first = DataQualityAssessor.assess(observations)
    second = DataQualityAssessor.assess(observations)

    assert first == second


def test_future_timestamp_is_invalid_when_after_assessment_time():
    as_of = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
    result = DataQualityAssessor.assess(
        [
            observation(
                timestamp=datetime(
                    2026, 9, 16, 12, 0, 1, tzinfo=timezone.utc
                )
            )
        ],
        as_of=as_of,
    )

    assert result[0].status is DataQualityStatus.INVALID
    assert DataQualityIssueCode.FUTURE_TIMESTAMP in {
        issue.code for issue in result[0].issues
    }


def test_timestamp_equal_to_assessment_time_is_not_future():
    as_of = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
    result = DataQualityAssessor.assess(
        [observation(timestamp=as_of)],
        as_of=as_of,
    )

    assert result[0].status is DataQualityStatus.VALID
    assert result[0].issues == ()


def test_future_timestamp_comparison_respects_timezone_offsets():
    as_of = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
    timestamp = datetime.fromisoformat("2026-09-16T15:00:01+03:00")
    result = DataQualityAssessor.assess(
        [observation(timestamp=timestamp)],
        as_of=as_of,
    )

    assert result[0].status is DataQualityStatus.INVALID
    assert DataQualityIssueCode.FUTURE_TIMESTAMP in {
        issue.code for issue in result[0].issues
    }


def test_naive_assessment_time_is_rejected():
    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        DataQualityAssessor.assess(
            [observation()],
            as_of=datetime(2026, 9, 16, 12),
        )
