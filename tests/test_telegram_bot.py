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



def test_polling_errors_never_log_telegram_bot_token(caplog: pytest.LogCaptureFixture) -> None:
    token = "telegram-secret-must-not-appear-in-logs"
    telegram_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal telegram_calls
        if request.url.host != "api.telegram.org":
            return httpx.Response(200, json={"report": "saved"})
        telegram_calls += 1
        if telegram_calls == 1:
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": [
                        {
                            "update_id": 1,
                            "message": {
                                "from": {"id": 123},
                                "chat": {"id": 123, "type": "private"},
                                "text": "/report EGAL",
                            },
                        }
                    ],
                },
            )
        raise httpx.ConnectError(
            f"failed to reach {request.url}",
            request=request,
        )

    async def cancel_after_logged_error(_: float) -> None:
        raise asyncio.CancelledError

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            bot = EgxTelegramBot(
                token,
                "http://egx.test",
                "api-secret",
                frozenset({123}),
                http=client,
            )
            original_sleep = asyncio.sleep
            try:
                asyncio.sleep = cancel_after_logged_error  # type: ignore[assignment]
                with pytest.raises(asyncio.CancelledError):
                    await bot.run(poll_seconds=0)
            finally:
                asyncio.sleep = original_sleep  # type: ignore[assignment]

    caplog.set_level("ERROR", logger="egx.telegram")
    asyncio.run(scenario())
    assert "EGX API request failed" in caplog.text
    assert "Failed to process Telegram update" in caplog.text
    assert token not in caplog.text
