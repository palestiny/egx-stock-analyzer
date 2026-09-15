
from enum import Enum

import pytest


from dataclasses import FrozenInstanceError

from app.domain.market_data.data_quality import (
    DataQualityAssessment,
    DataQualityIssue,
    DataQualityIssueCode,
    DataQualityStatus,
)


# Tests that a DataQualityAssessment can represent the VALID status.
# This exists because status is the main classification of an assessment.
# Its function is to verify that a valid assessment stores its status correctly.
def test_data_quality_assessment_can_represent_a_status():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.VALID,
    )

    assert assessment.status is DataQualityStatus.VALID


# Tests that an assessment can explicitly represent INVALID data.
# This exists because invalid data must be distinguishable from valid, suspect, and unknown data.
# Its function is to protect the INVALID status representation.
def test_data_quality_assessment_can_represent_invalid_data():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.INVALID,
    )

    assert assessment.status is DataQualityStatus.INVALID


# Tests that an assessment can explicitly represent SUSPECT data.
# This exists because questionable data is different from definitively invalid data.
# Its function is to protect the SUSPECT status representation.
def test_data_quality_assessment_can_represent_suspect_data():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.SUSPECT,
    )

    assert assessment.status is DataQualityStatus.SUSPECT


# Tests that an assessment can explicitly represent UNKNOWN data quality.
# This exists because the system may not always have enough information to classify an observation.
# Its function is to protect the UNKNOWN status representation.
def test_data_quality_assessment_can_represent_unknown_data():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.UNKNOWN,
    )

    assert assessment.status is DataQualityStatus.UNKNOWN


# Tests that VALID data is eligible for analysis.
# This exists because the assessment exposes the boundary between accepted data and data that should not proceed.
# Its function is to verify the current eligibility rule for VALID status.
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
# Tests that every non-VALID status is currently ineligible for analysis.
# This exists to protect the explicit analysis-entry rule for INVALID, SUSPECT, and UNKNOWN data.
# Its function is to verify all three non-valid statuses without duplicating the same test body.
def test_non_valid_data_quality_is_not_eligible_for_analysis(status):
    assessment = DataQualityAssessment(status=status)

    assert assessment.is_eligible_for_analysis() is False


# Tests that a DataQualityIssue can carry a structured issue code.
# This exists because quality evidence should be machine-readable rather than only free-form text.
# Its function is to verify that an issue stores its classification code.
def test_data_quality_issue_can_represent_a_structured_code():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_PRICE,
    )

    assert issue.code is DataQualityIssueCode.INVALID_PRICE


# Tests that DataQualityIssue is immutable.
# This exists because issue evidence should not change after it has been recorded.
# Its function is to protect the frozen Value Object contract.
def test_data_quality_issue_is_immutable():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_PRICE,
    )

    with pytest.raises(FrozenInstanceError):
        issue.code = DataQualityIssueCode.INVALID_VOLUME


# Tests that the initial DataQualityIssueCode vocabulary exists with stable string values.
# This exists because these codes form the initial structured vocabulary for quality evidence.
# Its function is to protect the currently agreed issue-code names from accidental changes.
def test_data_quality_issue_code_has_initial_vocabulary():
    assert DataQualityIssueCode.MISSING_VALUE.value == "missing_value"
    assert DataQualityIssueCode.INVALID_VALUE.value == "invalid_value"
    assert DataQualityIssueCode.INVALID_TIMESTAMP.value == "invalid_timestamp"
    assert DataQualityIssueCode.DUPLICATE_OBSERVATION.value == "duplicate_observation"
    assert DataQualityIssueCode.OHLC_INCONSISTENCY.value == "ohlc_inconsistency"


# Tests again that a DataQualityIssue can store the current generic INVALID_VALUE code.
# This exists to exercise the structured issue representation using the current issue vocabulary.
# Its function is to verify that the issue preserves the exact supplied code.
def test_data_quality_issue_can_represent_a_structured_code():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_VALUE,
    )

    assert issue.code is DataQualityIssueCode.INVALID_VALUE


# Tests again that a DataQualityIssue using INVALID_VALUE cannot be mutated.
# This exists to protect immutability for the current issue representation.
# Its function is to verify that changing the code after construction raises FrozenInstanceError.
def test_data_quality_issue_is_immutable():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_VALUE,
    )

    with pytest.raises(FrozenInstanceError):
        issue.code = DataQualityIssueCode.MISSING_VALUE


# Tests that a DataQualityAssessment can contain structured issue evidence.
# This exists because an assessment needs both a status and the evidence explaining that status.
# Its function is to verify that issues are stored as part of the assessment.
def test_data_quality_assessment_can_contain_issues():
    issue = DataQualityIssue(
        code=DataQualityIssueCode.INVALID_VALUE,
    )

    assessment = DataQualityAssessment(
        status=DataQualityStatus.SUSPECT,
        issues=(issue,),
    )

    assert assessment.issues == (issue,)


# Tests that DataQualityAssessment itself is immutable.
# This exists because an assessment represents recorded quality evidence and should not mutate after creation.
# Its function is to protect the frozen assessment contract.
def test_data_quality_assessment_is_immutable():
    assessment = DataQualityAssessment(
        status=DataQualityStatus.VALID,
        issues=(),
    )

    with pytest.raises(FrozenInstanceError):
        assessment.status = DataQualityStatus.INVALID