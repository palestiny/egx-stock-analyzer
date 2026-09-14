
from enum import Enum

import pytest


from dataclasses import FrozenInstanceError

from app.domain.market_data.data_quality import (
    DataQualityAssessment,
    DataQualityIssue,
    DataQualityIssueCode,
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


def test_data_quality_issue_can_represent_a_structured_code():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_PRICE,
    )

    assert issue.code is DataQualityIssueCode.INVALID_PRICE


def test_data_quality_issue_is_immutable():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_PRICE,
    )

    with pytest.raises(FrozenInstanceError):
        issue.code = DataQualityIssueCode.INVALID_VOLUME

def test_data_quality_issue_code_has_initial_vocabulary():
    assert DataQualityIssueCode.MISSING_VALUE.value == "missing_value"
    assert DataQualityIssueCode.INVALID_VALUE.value == "invalid_value"
    assert DataQualityIssueCode.INVALID_TIMESTAMP.value == "invalid_timestamp"
    assert DataQualityIssueCode.DUPLICATE_OBSERVATION.value == "duplicate_observation"
    assert DataQualityIssueCode.OHLC_INCONSISTENCY.value == "ohlc_inconsistency"


def test_data_quality_issue_can_represent_a_structured_code():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_VALUE,
    )

    assert issue.code is DataQualityIssueCode.INVALID_VALUE


def test_data_quality_issue_is_immutable():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_VALUE,
    )

    with pytest.raises(FrozenInstanceError):
        issue.code = DataQualityIssueCode.MISSING_VALUE


def test_data_quality_assessment_can_contain_issues():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_VALUE,
    )

    assessment = DataQualityAssessment(
        status=DataQualityStatus.SUSPECT,
        issues=(issue,),
    )

    assert assessment.issues == (issue,)


def test_data_quality_assessment_is_immutable():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.VALID,
        issues=(),
    )

    with pytest.raises(FrozenInstanceError):
        assessment.status = DataQualityStatus.INVALID