"""Opt-in live Telegram delivery test.

This test is intentionally excluded from normal CI and never sends without an explicit opt-in.
"""
import os
from uuid import uuid4

import pytest

from app.domain.reporting.alerts import AlertCandidate
from app.infrastructure.notifications.telegram_provider import TelegramNotificationProvider


@pytest.mark.integration
@pytest.mark.external
def test_live_telegram_delivery_when_explicitly_enabled() -> None:
    if os.getenv("EGX_TELEGRAM_LIVE_TEST", "").strip() != "1":
        pytest.skip("Live Telegram delivery requires EGX_TELEGRAM_LIVE_TEST=1")

    bot_token = os.getenv("EGX_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("EGX_TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        pytest.fail(
            "Live Telegram delivery is enabled but required Telegram credentials are missing"
        )

    candidate = AlertCandidate(
        stock_id=uuid4(),
        snapshot_id=uuid4(),
        classification="connection_test",
        stock_quality_score=0,
        entry_quality_score=0,
    )
    provider = TelegramNotificationProvider(bot_token, chat_id)
    try:
        # The provider only returns after Telegram responds with {"ok": true}.
        provider.send(candidate, "telegram")
    finally:
        provider.close()
