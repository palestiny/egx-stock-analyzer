from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeatureStatus(StrEnum):
    PLANNED = "PLANNED"
    IMPLEMENTED = "IMPLEMENTED"
    PRODUCTION_READY = "PRODUCTION_READY"


class DataReadiness(StrEnum):
    FIXTURE_ONLY = "FIXTURE_ONLY"
    HISTORICAL = "HISTORICAL"
    DELAYED = "DELAYED"
    REAL_TIME = "REAL_TIME"


@dataclass(frozen=True)
class Capability:
    key: str
    name: str
    status: FeatureStatus
    data_readiness: DataReadiness
    description: str

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("capability key is required")
        if not self.name.strip():
            raise ValueError("capability name is required")
        if not self.description.strip():
            raise ValueError("capability description is required")


class CapabilityRegistry:
    def __init__(self, capabilities: tuple[Capability, ...] = ()) -> None:
        self._capabilities = {item.key: item for item in capabilities}

    def register(self, capability: Capability) -> None:
        if capability.key in self._capabilities:
            raise ValueError(f"capability already registered: {capability.key}")
        self._capabilities[capability.key] = capability

    def get(self, key: str) -> Capability:
        try:
            return self._capabilities[key]
        except KeyError as exc:
            raise KeyError(f"unknown capability: {key}") from exc

    def all(self) -> tuple[Capability, ...]:
        return tuple(self._capabilities.values())
