from app.infrastructure.config import InfrastructureConfig


def test_from_environment_reads_operator_token(monkeypatch) -> None:
    monkeypatch.setenv("EGX_OPERATOR_TOKEN", "test-token")

    config = InfrastructureConfig.from_environment()

    assert config.operator_token == "test-token"


def test_from_environment_allows_missing_operator_token_at_parse_boundary(monkeypatch) -> None:
    monkeypatch.delenv("EGX_OPERATOR_TOKEN", raising=False)

    config = InfrastructureConfig.from_environment()

    assert config.operator_token is None


def test_from_environment_reads_telegram_configuration(monkeypatch) -> None:
    monkeypatch.setenv("EGX_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("EGX_TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("EGX_TELEGRAM_TIMEOUT_SECONDS", "12.5")

    config = InfrastructureConfig.from_environment()

    assert config.telegram_bot_token == "token"
    assert config.telegram_chat_id == "chat"
    assert config.telegram_timeout_seconds == 12.5


def test_default_configuration_keeps_telegram_disabled() -> None:
    config = InfrastructureConfig()

    assert config.telegram_bot_token is None
    assert config.telegram_chat_id is None
    assert config.telegram_timeout_seconds == 10.0


def test_from_environment_reads_user_bearer_tokens(monkeypatch) -> None:
    user_id = "11111111-1111-1111-1111-111111111111"
    monkeypatch.setenv(
        "EGX_USER_TOKENS",
        '{"' + user_id + '":"user-token"}',
    )

    config = InfrastructureConfig.from_environment()

    from uuid import UUID

    assert config.user_bearer_tokens == {"user-token": UUID(user_id)}


def test_from_environment_rejects_invalid_user_token_configuration(monkeypatch) -> None:
    monkeypatch.setenv("EGX_USER_TOKENS", "not-json")

    import pytest

    with pytest.raises(ValueError, match="valid JSON"):
        InfrastructureConfig.from_environment()
