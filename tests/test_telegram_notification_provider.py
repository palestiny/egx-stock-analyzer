import json
from uuid import uuid4

import httpx
import pytest

from app.domain.reporting.alerts import AlertCandidate
from app.infrastructure.notifications.telegram_provider import (
    TelegramNotificationProvider,
    TelegramNotificationProviderError,
)


TOKEN = "123456:TEST-TOKEN"
CHAT_ID = "123456789"


def make_candidate() -> AlertCandidate:
    return AlertCandidate(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        classification="buy",
        stock_quality_score=7,
        entry_quality_score=3,
    )


def test_telegram_provider_sends_expected_request():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = TelegramNotificationProvider(TOKEN, CHAT_ID, client=client)

    provider.send(make_candidate(), "telegram")

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == f"/bot{TOKEN}/sendMessage"
    payload = json.loads(request.content)
    assert payload["chat_id"] == CHAT_ID
    assert "Classification: buy" in payload["text"]


def test_telegram_provider_rejects_unsupported_channel():
    provider = TelegramNotificationProvider(
        TOKEN,
        CHAT_ID,
        client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))),
    )

    with pytest.raises(TelegramNotificationProviderError, match="Unsupported"):
        provider.send(make_candidate(), "email")


def test_telegram_provider_maps_provider_rejection_without_exposing_token():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": False, "description": "chat not found"},
        )

    provider = TelegramNotificationProvider(
        TOKEN,
        CHAT_ID,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TelegramNotificationProviderError) as error:
        provider.send(make_candidate(), "telegram")

    assert "chat not found" in str(error.value)
    assert TOKEN not in str(error.value)


def test_telegram_provider_maps_timeout_without_exposing_token():
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    provider = TelegramNotificationProvider(
        TOKEN,
        CHAT_ID,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TelegramNotificationProviderError, match="timed out") as error:
        provider.send(make_candidate(), "telegram")

    assert TOKEN not in str(error.value)


def test_telegram_provider_requires_configuration():
    with pytest.raises(ValueError, match="bot token"):
        TelegramNotificationProvider("", CHAT_ID)

    with pytest.raises(ValueError, match="chat ID"):
        TelegramNotificationProvider(TOKEN, "")

    with pytest.raises(ValueError, match="timeout"):
        TelegramNotificationProvider(TOKEN, CHAT_ID, timeout=0)
