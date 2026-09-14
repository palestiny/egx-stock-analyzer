
from enum import Enum

import pytest

from app.domain.market_data.data_quality import (
    DataQualityAssessment,
    DataQualityStatus,
)


def test_data_quality_assessment_can_represent_a_status():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.VALID,
    )

    assert assessment.status is DataQualityStatus.VALID


def test_data_quality_assessment_can_represent_invalid_data():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.INVALID,
    )

    assert assessment.status is DataQualityStatus.INVALID

def test_data_quality_assessment_can_represent_suspect_data():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.SUSPECT,
    )

    assert assessment.status is DataQualityStatus.SUSPECT


def test_data_quality_assessment_can_represent_unknown_data():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.UNKNOWN,
    )

    assert assessment.status is DataQualityStatus.UNKNOWN

def test_valid_data_quality_is_eligible_for_analysis():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.VALID,
    )

    assert assessment.is_eligible_for_analysis() is True

@pytest.mark.parametrize(
    "status",
    [
        DataQualityStatus.INVALID,
        DataQualityStatus.SUSPECT,
        DataQualityStatus.UNKNOWN,
    ],
)
def test_non_valid_data_quality_is_not_eligible_for_analysis(status):
    assessment = DataQualityAssessment(status=status)

    assert assessment.is_eligible_for_analysis() is False

