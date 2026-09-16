from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class InfrastructureConfig:
    finnhub_api_key: str

    @classmethod
    def from_environment(cls) -> InfrastructureConfig:
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise ValueError("FINNHUB_API_KEY is required")
        return cls(finnhub_api_key=api_key)
