from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from app.domain.technical_analysis.elliott import (
    ElliottDirection,
    ElliottImpulseCandidate,
)
from app.domain.technical_analysis.price_structure import SwingKind, SwingPoint


@dataclass(frozen=True)
class ElliottWaveCount:
    candidate: ElliottImpulseCandidate
    swing_indices: tuple[int, int, int, int, int, int]
    invalidation_level: Decimal
    methodology_version: str = "elliott-impulse-candidate-v1"


def generate_elliott_impulse_candidates(
    swings: Sequence[SwingPoint],
) -> tuple[ElliottWaveCount, ...]:
    """Enumerate rule-consistent six-pivot impulse candidates without assigning probabilities."""
    ordered = tuple(swings)
    for previous, current in zip(ordered, ordered[1:]):
        if current.index <= previous.index:
            raise ValueError("swing points must be strictly ordered by index")

    candidates: list[ElliottWaveCount] = []
    seen: set[tuple[int, ...]] = set()
    for start in range(max(0, len(ordered) - 5)):
        points = ordered[start:start + 6]
        if len(points) != 6:
            continue
        if any(left.kind is right.kind for left, right in zip(points, points[1:])):
            continue
        if points[0].kind is SwingKind.LOW and points[-1].kind is SwingKind.HIGH:
            direction = ElliottDirection.UP
        elif points[0].kind is SwingKind.HIGH and points[-1].kind is SwingKind.LOW:
            direction = ElliottDirection.DOWN
        else:
            continue

        indices = tuple(point.index for point in points)
        if indices in seen:
            continue
        candidate = ElliottImpulseCandidate(
            direction=direction,
            points=tuple(point.price for point in points),  # type: ignore[arg-type]
        )
        if not candidate.is_rule_consistent:
            continue
        seen.add(indices)
        candidates.append(
            ElliottWaveCount(
                candidate=candidate,
                swing_indices=indices,  # type: ignore[arg-type]
                invalidation_level=points[0].price,
            )
        )
    return tuple(candidates)
