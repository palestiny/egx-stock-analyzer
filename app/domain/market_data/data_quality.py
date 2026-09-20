from dataclasses import dataclass
from enum import Enum


class DataQualityStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    SUSPECT = "suspect"
    UNKNOWN = "unknown"


class DataQualityIssueCode(Enum):
    MISSING_VALUE = "missing_value"
    INVALID_VALUE = "invalid_value"
    INVALID_TIMESTAMP = "invalid_timestamp"
    DUPLICATE_OBSERVATION = "duplicate_observation"
    OHLC_INCONSISTENCY = "ohlc_inconsistency"


@dataclass(frozen=True)
class DataQualityIssue:
    code: DataQualityIssueCode



@dataclass(frozen=True)
class DataQualityAssessment:
    status: DataQualityStatus
    issues: tuple[DataQualityIssue, ...] = ()

    def is_eligible_for_analysis(self) -> bool:
        return self.status is DataQualityStatus.VALID
