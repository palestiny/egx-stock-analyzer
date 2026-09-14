from dataclasses import dataclass
from enum import Enum


class DataQualityStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    SUSPECT = "suspect"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DataQualityAssessment:
    status: DataQualityStatus

    def is_eligible_for_analysis(self) -> bool:
        return self.status is DataQualityStatus.VALID
