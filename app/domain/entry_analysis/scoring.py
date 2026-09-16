from dataclasses import dataclass

from app.domain.entry_analysis.context import EntryContext


@dataclass(frozen=True)
class EntryQualityScore:
    support_points: int
    resistance_points: int
    total_score: int


class EntryQualityScorer:
    @staticmethod
    def score(context: EntryContext) -> EntryQualityScore:
        support_points = 1 if context.nearest_support is not None else 0
        resistance_points = 1 if context.nearest_resistance is not None else 0

        return EntryQualityScore(
            support_points=support_points,
            resistance_points=resistance_points,
            total_score=support_points + resistance_points,
        )
