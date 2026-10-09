from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.telegram_bot import EgxTelegramBot, allowed_chat_ids, parse_symbol


def test_parse_symbol_normalizes_and_rejects_invalid_input() -> None:
    assert parse_symbol(" egal ") == "EGAL"
    assert parse_symbol("COMI.CA") == "COMI.CA"
    assert parse_symbol("") is None
    assert parse_symbol("EGAL/../../secret") is None
    assert parse_symbol("EGAL\n") == "EGAL"


def test_allowed_chat_ids_requires_positive_numeric_allowlist() -> None:
    assert allowed_chat_ids("123, 456") == frozenset({123, 456})
    with pytest.raises(ValueError):
        allowed_chat_ids("")
    with pytest.raises(ValueError):
        allowed_chat_ids("123,abc")
    with pytest.raises(ValueError):
        allowed_chat_ids("-1")


def test_health_command_replies_without_exposing_api_token() -> None:
    sent_messages: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.telegram.org":
            payload = json.loads(request.content)
            sent_messages.append(payload)
            return httpx.Response(200, json={"ok": True, "result": True})
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404, json={"detail": "not found"})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            bot = EgxTelegramBot("telegram-secret", "http://egx.test", "api-secret", frozenset({123}), http=client)
            await bot.handle_message({
                "from": {"id": 123},
                "chat": {"id": 123, "type": "private"},
                "text": "/health",
            })

    asyncio.run(scenario())
    assert len(sent_messages) == 1
    assert "تعمل" in str(sent_messages[0]["text"])
    assert "api-secret" not in str(sent_messages)


def test_unauthorized_user_is_rejected_without_calling_egx_api() -> None:
    sent_messages: list[dict[str, object]] = []
    api_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.telegram.org":
            payload = json.loads(request.content)
            sent_messages.append(payload)
            return httpx.Response(200, json={"ok": True, "result": True})
        api_calls.append(str(request.url))
        return httpx.Response(200, json={"status": "ok"})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            bot = EgxTelegramBot("telegram-secret", "http://egx.test", "api-secret", frozenset({123}), http=client)
            await bot.handle_message({
                "from": {"id": 999},
                "chat": {"id": 999, "type": "private"},
                "text": "/analyze EGAL",
            })

    asyncio.run(scenario())
    assert api_calls == []
    assert len(sent_messages) == 1
    assert "غير مصرح" in str(sent_messages[0]["text"])
