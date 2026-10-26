from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.technical_analysis.price_structure import SwingKind, SwingPoint


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


@dataclass(frozen=True)
class ElliottWaveCount:
    """One mechanically enumerated five-wave impulse candidate, not a forecast."""

    start_index: int
    end_index: int
    candidate: ElliottImpulseCandidate

    @property
    def rule_violations(self) -> tuple[str, ...]:
        return self.candidate.rule_violations

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.candidate.warnings

    @property
    def is_rule_consistent(self) -> bool:
        return self.candidate.is_rule_consistent

    @property
    def wave_two_invalidation_price(self) -> Decimal:
        """Wave-2 hard invalidation boundary at the wave origin."""
        return self.candidate.points[0]


def enumerate_impulse_counts(
    swing_points: Sequence[SwingPoint],
) -> tuple[ElliottWaveCount, ...]:
    """Enumerate alternating six-pivot windows as candidate counts with explicit rule diagnostics.

    This is a deterministic candidate generator, not an AI wave interpretation or a trade signal.
    It intentionally returns rule-inconsistent alternatives with their violations for auditability.
    """
    points = tuple(swing_points)
    if any(point.index < 0 for point in points):
        raise ValueError("swing indexes must be non-negative")
    if any(not point.price.is_finite() or point.price <= 0 for point in points):
        raise ValueError("swing prices must be finite positive prices")
    if any(current.index < previous.index for previous, current in zip(points, points[1:])):
        raise ValueError("swing points must be ordered by index")

    counts: list[ElliottWaveCount] = []
    for start in range(max(0, len(points) - 5)):
        window = points[start:start + 6]
        if len(window) != 6:
            continue
        if any(
            current.index <= previous.index
            for previous, current in zip(window, window[1:])
        ):
            continue
        kinds = tuple(point.kind for point in window)
        if kinds == (
            SwingKind.LOW, SwingKind.HIGH, SwingKind.LOW,
            SwingKind.HIGH, SwingKind.LOW, SwingKind.HIGH,
        ):
            direction = ElliottDirection.UP
        elif kinds == (
            SwingKind.HIGH, SwingKind.LOW, SwingKind.HIGH,
            SwingKind.LOW, SwingKind.HIGH, SwingKind.LOW,
        ):
            direction = ElliottDirection.DOWN
        else:
            continue

        candidate = ElliottImpulseCandidate(
            direction=direction,
            points=tuple(point.price for point in window),  # type: ignore[arg-type]
        )
        counts.append(ElliottWaveCount(
            start_index=window[0].index,
            end_index=window[-1].index,
            candidate=candidate,
        ))

    return tuple(counts)
