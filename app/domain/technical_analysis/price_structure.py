from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Sequence


class SwingKind(StrEnum):
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True)
class SwingPoint:
    index: int
    kind: SwingKind
    price: Decimal
