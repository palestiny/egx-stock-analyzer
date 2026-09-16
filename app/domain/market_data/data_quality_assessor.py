from collections import Counter
from datetime import datetime
from decimal import Decimal

from app.domain.market_data.data_quality import (
    DataQualityAssessment,
    DataQualityIssue,
    DataQualityIssueCode,
    DataQualityStatus,
)
from app.domain.market_data.raw_observation import RawPriceBarObservation


class DataQualityAssessor:
    @staticmethod
    def assess(
        observations: list[RawPriceBarObservation],
    ) -> tuple[DataQualityAssessment, ...]:
        if not observations:
            return ()

        identities = [
            (observation.stock_id, observation.timeframe, observation.timestamp)
            for observation in observations
        ]
        identity_counts = Counter(identities)

        assessments: list[DataQualityAssessment] = []

        for observation in observations:
            issues: list[DataQualityIssue] = []

            values = (
                observation.stock_id,
                observation.timeframe,
                observation.timestamp,
                observation.open,
                observation.high,
                observation.low,
                observation.close,
                observation.volume,
            )

            if any(value is None for value in values):
                issues.append(DataQualityIssue(DataQualityIssueCode.MISSING_VALUE))

            if observation.timestamp is not None:
                if (
                    observation.timestamp.tzinfo is None
                    or observation.timestamp.utcoffset() is None
                ):
                    issues.append(
                        DataQualityIssue(DataQualityIssueCode.INVALID_TIMESTAMP)
                    )

            numeric_values = (
                observation.open,
                observation.high,
                observation.low,
                observation.close,
            )
            if any(
                value is not None and value < Decimal("0")
                for value in numeric_values
            ) or (
                observation.volume is not None and observation.volume < 0
            ):
                issues.append(DataQualityIssue(DataQualityIssueCode.INVALID_VALUE))

            if all(value is not None for value in numeric_values):
                assert observation.open is not None
                assert observation.high is not None
                assert observation.low is not None
                assert observation.close is not None

                if (
                    observation.high < max(observation.open, observation.close)
                    or observation.low > min(observation.open, observation.close)
                    or observation.high < observation.low
                ):
                    issues.append(
                        DataQualityIssue(DataQualityIssueCode.OHLC_INCONSISTENCY)
                    )

            identity = (
                observation.stock_id,
                observation.timeframe,
                observation.timestamp,
            )
            if identity_counts[identity] > 1:
                issues.append(
                    DataQualityIssue(DataQualityIssueCode.DUPLICATE_OBSERVATION)
                )

            if any(
                issue.code
                in {
                    DataQualityIssueCode.MISSING_VALUE,
                    DataQualityIssueCode.INVALID_VALUE,
                    DataQualityIssueCode.INVALID_TIMESTAMP,
                    DataQualityIssueCode.OHLC_INCONSISTENCY,
                }
                for issue in issues
            ):
                status = DataQualityStatus.INVALID
            elif any(
                issue.code is DataQualityIssueCode.DUPLICATE_OBSERVATION
                for issue in issues
            ):
                status = DataQualityStatus.SUSPECT
            else:
                status = DataQualityStatus.VALID

            assessments.append(
                DataQualityAssessment(
                    status=status,
                    issues=tuple(issues),
                )
            )

        return tuple(assessments)
