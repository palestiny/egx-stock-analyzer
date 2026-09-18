from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InfrastructureConfig:
    """Configuration for infrastructure composition.

    External data-source credentials are intentionally not required for the
    current development vertical slice. Yahoo Finance is used as the live
    data source for both market and fundamental data.
    """

    @classmethod
    def from_environment(cls) -> InfrastructureConfig:
        return cls()
