from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ElliottDirection(StrEnum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True)
class ElliottImpulseCandidate:
    """A candidate count supplied with explicit six swing prices, not an automatic wave detector."""

    direction: ElliottDirection
    points: tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]

    def __post_init__(self) -> None:
        if len(self.points) != 6:
            raise ValueError("an impulse candidate requires six swing points")
        if any(not point.is_finite() or point <= 0 for point in self.points):
            raise ValueError("swing points must be finite positive prices")

    @property
    def wave_lengths(self) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
        return tuple(
            abs(current - previous)
            for previous, current in zip(self.points, self.points[1:])
        )  # type: ignore[return-value]

    @property
    def rule_violations(self) -> tuple[str, ...]:
        p0, p1, p2, p3, p4, p5 = self.points
        violations: list[str] = []

        if self.direction is ElliottDirection.UP:
            if not p1 > p0:
                violations.append("wave_1_direction")
            if p2 < p0:
                violations.append("wave_2_exceeds_origin")
            if not p3 > p1:
                violations.append("wave_3_does_not_extend_wave_1")
            if not p4 > p1:
                violations.append("wave_4_overlaps_wave_1_territory")
        else:
            if not p1 < p0:
                violations.append("wave_1_direction")
            if p2 > p0:
                violations.append("wave_2_exceeds_origin")
            if not p3 < p1:
                violations.append("wave_3_does_not_extend_wave_1")
            if not p4 < p1:
                violations.append("wave_4_overlaps_wave_1_territory")

        wave_1, wave_2, wave_3, wave_4, wave_5 = self.wave_lengths
        if wave_3 < min(wave_1, wave_5):
            violations.append("wave_3_is_shortest")
        return tuple(violations)

    @property
    def warnings(self) -> tuple[str, ...]:
        """Return non-fatal Elliott interpretations, including a possible truncated fifth."""
        _, _, _, p3, _, p5 = self.points
        if self.direction is ElliottDirection.UP and p5 <= p3:
            return ("possible_truncated_wave_5",)
        if self.direction is ElliottDirection.DOWN and p5 >= p3:
            return ("possible_truncated_wave_5",)
        return ()

    @property
    def is_rule_consistent(self) -> bool:
        return not self.rule_violations
