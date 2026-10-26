import json
from datetime import datetime, timezone

import httpx
from fastapi.testclient import TestClient

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.notifications.telegram_account_linking import TelegramAccountLinkingService
from app.infrastructure.notifications.telegram_provider import TelegramNotificationProvider
from app.infrastructure.persistence.sqlite_telegram_account_link_store import SQLiteTelegramAccountLinkStore
from app.application.security.identity import LEGACY_OPERATOR_USER_ID
from app.api.main import create_app


BOT_TOKEN = "123456:TEST-TOKEN"
WEBHOOK_SECRET = "telegram-webhook-secret"


def make_client(tmp_path):
    sent_requests = []

    def telegram_handler(request: httpx.Request) -> httpx.Response:
        sent_requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    provider = TelegramNotificationProvider(
        BOT_TOKEN,
        None,
        client=httpx.Client(transport=httpx.MockTransport(telegram_handler)),
    )
    linking = TelegramAccountLinkingService(
        SQLiteTelegramAccountLinkStore(tmp_path / "accounts.db"),
        token_factory=lambda: "test-link-token",
    )
    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        telegram_account_linking=linking,
        telegram_notification_provider=provider,
        telegram_webhook_secret=WEBHOOK_SECRET,
    )
    return TestClient(app), linking, sent_requests


def test_authenticated_user_can_issue_and_unlink_telegram_account(tmp_path):
    client, linking, _ = make_client(tmp_path)

    response = client.post(
        "/api/v1/telegram/link-challenges",
        headers={"Authorization": "Bearer test-operator-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "test-link-token"
    assert body["expires_at"].endswith("+00:00")
    assert "/start <token>" in body["instruction"]

    assert linking.consume(
        body["token"],
        "chat-123",
        now=datetime.now(timezone.utc),
    ) is not None
    unlink = client.delete(
        "/api/v1/telegram/link",
        headers={"Authorization": "Bearer test-operator-token"},
    )
    assert unlink.status_code == 200
    assert unlink.json() == {"unlinked": True}


def test_telegram_webhook_requires_secret_and_links_chat(tmp_path):
    client, linking, sent_requests = make_client(tmp_path)
    challenge = client.post(
        "/api/v1/telegram/link-challenges",
        headers={"Authorization": "Bearer test-operator-token"},
    ).json()

    update = {
        "update_id": 101,
        "message": {
            "text": f"/start {challenge['token']}",
            "chat": {"id": 987654321},
        },
    }
    denied = client.post("/api/v1/telegram/webhook", json=update)
    assert denied.status_code == 403

    accepted = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
        json=update,
    )
    assert accepted.status_code == 200
    assert accepted.json() == {"ok": True}
    assert linking.get_chat_id(LEGACY_OPERATOR_USER_ID) == "987654321"
    assert len(sent_requests) == 1
    assert json.loads(sent_requests[0].content)["chat_id"] == "987654321"
    assert "now linked" in json.loads(sent_requests[0].content)["text"]

    replay = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
        json=update,
    )
    assert replay.status_code == 200
    assert replay.json() == {"ok": True, "duplicate": True}
    assert len(sent_requests) == 1


def test_telegram_webhook_rejects_wrong_secret_without_sending(tmp_path):
    client, _, sent_requests = make_client(tmp_path)
    response = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        json={"message": {"text": "/start token", "chat": {"id": 1}}},
    )
    assert response.status_code == 403
    assert sent_requests == []


def test_malformed_webhook_update_does_not_consume_update_id(tmp_path):
    client, linking, sent_requests = make_client(tmp_path)
    challenge = client.post(
        "/api/v1/telegram/link-challenges",
        headers={"Authorization": "Bearer test-operator-token"},
    ).json()
    headers = {"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET}
    update_id = 202

    malformed = client.post(
        "/api/v1/telegram/webhook",
        headers=headers,
        json={"update_id": update_id, "message": {"text": "/start"}},
    )
    assert malformed.status_code == 200

    valid = client.post(
        "/api/v1/telegram/webhook",
        headers=headers,
        json={
            "update_id": update_id,
            "message": {
                "text": f"/start {challenge['token']}",
                "chat": {"id": 987654321},
            },
        },
    )
    assert valid.status_code == 200
    assert valid.json() == {"ok": True}
    assert linking.get_chat_id(LEGACY_OPERATOR_USER_ID) == "987654321"
    assert len(sent_requests) == 1

