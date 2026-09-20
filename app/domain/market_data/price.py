from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Price:
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Price cannot be negative")
