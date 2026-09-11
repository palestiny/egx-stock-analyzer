from dataclasses import dataclass
from numbers import Integral


@dataclass(frozen=True)
class Volume:
    value: int

    def __post_init__(self):
        if isinstance(self.value, bool) or not isinstance(self.value, Integral):
            raise TypeError("Volume must be an integer")

        if self.value < 0:
            raise ValueError("Volume cannot be negative")