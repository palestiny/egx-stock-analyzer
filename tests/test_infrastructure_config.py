from app.infrastructure.config import InfrastructureConfig


def test_from_environment_does_not_require_external_credentials() -> None:
    config = InfrastructureConfig.from_environment()

    assert config == InfrastructureConfig()
