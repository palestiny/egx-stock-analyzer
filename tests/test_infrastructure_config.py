import pytest

from app.infrastructure.config import InfrastructureConfig


def test_from_environment_reads_finnhub_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")

    config = InfrastructureConfig.from_environment()

    assert config.finnhub_api_key == "test-key"


def test_from_environment_rejects_missing_finnhub_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)

    with pytest.raises(ValueError, match="FINNHUB_API_KEY is required"):
        InfrastructureConfig.from_environment()
