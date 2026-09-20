from dataclasses import FrozenInstanceError

import pytest

from app.domain.market_data.data_quality import (
    DataQualityAssessment,
    DataQualityIssue,
    DataQualityIssueCode,
    DataQualityStatus,
)


def test_data_quality_assessment_can_represent_each_status():
    for status in DataQualityStatus:
        assessment = DataQualityAssessment(status=status)
        assert assessment.status is status


def test_only_valid_data_quality_is_eligible_for_analysis():
    assert DataQualityAssessment(DataQualityStatus.VALID).is_eligible_for_analysis() is True

    for status in (
        DataQualityStatus.INVALID,
        DataQualityStatus.SUSPECT,
        DataQualityStatus.UNKNOWN,
    ):
        assert DataQualityAssessment(status).is_eligible_for_analysis() is False


def test_data_quality_issue_uses_structured_code():
    issue = DataQualityIssue(DataQualityIssueCode.INVALID_VALUE)
    assert issue.code is DataQualityIssueCode.INVALID_VALUE


def test_data_quality_issue_code_vocabulary_is_stable():
    assert DataQualityIssueCode.MISSING_VALUE.value == "missing_value"
    assert DataQualityIssueCode.INVALID_VALUE.value == "invalid_value"
    assert DataQualityIssueCode.INVALID_TIMESTAMP.value == "invalid_timestamp"
    assert DataQualityIssueCode.DUPLICATE_OBSERVATION.value == "duplicate_observation"
    assert DataQualityIssueCode.OHLC_INCONSISTENCY.value == "ohlc_inconsistency"


def test_data_quality_issue_is_immutable():
    issue = DataQualityIssue(DataQualityIssueCode.INVALID_VALUE)

    with pytest.raises(FrozenInstanceError):
        issue.code = DataQualityIssueCode.MISSING_VALUE


def test_data_quality_assessment_can_contain_issues():
    issue = DataQualityIssue(DataQualityIssueCode.INVALID_VALUE)
    assessment = DataQualityAssessment(
        status=DataQualityStatus.INVALID,
        issues=(issue,),
    )

    assert assessment.issues == (issue,)


def test_data_quality_assessment_is_immutable():
    assessment = DataQualityAssessment(DataQualityStatus.VALID)

    with pytest.raises(FrozenInstanceError):
        assessment.status = DataQualityStatus.INVALID
