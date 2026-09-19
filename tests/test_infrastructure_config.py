from app.infrastructure.config import InfrastructureConfig


def test_operator_token_is_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("EGX_OPERATOR_TOKEN", "test-token")

    config = InfrastructureConfig.from_environment()

    assert config.operator_token == "test-token"


def test_operator_token_is_optional_at_configuration_parsing_boundary(monkeypatch):
    monkeypatch.delenv("EGX_OPERATOR_TOKEN", raising=False)

    config = InfrastructureConfig.from_environment()

    assert config.operator_token is None
