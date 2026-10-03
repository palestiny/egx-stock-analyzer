import pytest

from app.application.capabilities import (
    Capability,
    CapabilityRegistry,
    DataReadiness,
    FeatureStatus,
)


def test_registry_preserves_feature_readiness() -> None:
    registry = CapabilityRegistry(
        (
            Capability(
                key="technical_analysis",
                name="Technical Analysis",
                status=FeatureStatus.IMPLEMENTED,
                data_readiness=DataReadiness.HISTORICAL,
                description="Deterministic technical analysis.",
            ),
        )
    )

    capability = registry.get("technical_analysis")

    assert capability.status is FeatureStatus.IMPLEMENTED
    assert capability.data_readiness is DataReadiness.HISTORICAL


def test_registry_rejects_duplicate_keys() -> None:
    capability = Capability(
        key="signals",
        name="Signals",
        status=FeatureStatus.PLANNED,
        data_readiness=DataReadiness.FIXTURE_ONLY,
        description="Structured signals.",
    )
    registry = CapabilityRegistry((capability,))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(capability)


def test_registry_rejects_unknown_capability() -> None:
    with pytest.raises(KeyError, match="unknown capability"):
        CapabilityRegistry().get("does_not_exist")
