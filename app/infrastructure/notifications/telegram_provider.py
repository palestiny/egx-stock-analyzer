from __future__ import annotations

from typing import Any

import httpx

from app.application.notifications.provider import NotificationProvider
from app.application.notifications.telegram_message_sender import (
    TelegramDeliveryOutcomeUnknown,
    TelegramDeliveryRejected,
)
from app.domain.reporting.alerts import AlertCandidate


class TelegramNotificationProviderError(TelegramDeliveryRejected):
    """Raised when Telegram notification delivery cannot be completed."""


class TelegramNotificationProvider(NotificationProvider):
    CHANNEL = "telegram"
    DEFAULT_TIMEOUT_SECONDS = 10.0
    API_BASE_URL = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: str,
        chat_id: str | None,
        *,
        client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        normalized_token = bot_token.strip()
        normalized_chat_id = chat_id.strip() if chat_id is not None else None
        if not normalized_token:
            raise ValueError("Telegram bot token cannot be empty")
        if chat_id is not None and not normalized_chat_id:
            raise ValueError("Telegram chat ID cannot be empty")
        if timeout <= 0:
            raise ValueError("Telegram timeout must be positive")

        self._bot_token = normalized_token
        self._chat_id = normalized_chat_id
        self._timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    def send(self, candidate: AlertCandidate, channel: str) -> None:
        if channel.strip().lower() != self.CHANNEL:
            raise TelegramNotificationProviderError(
                f"Unsupported notification channel: {channel}"
            )
        if self._chat_id is None:
            raise TelegramNotificationProviderError(
                "Telegram chat ID is not configured for legacy single-chat delivery"
            )
        self.send_message(self._chat_id, self._format_message(candidate))

    def send_message(self, chat_id: str, message: str) -> None:
        """Send a prepared message to one explicitly selected recipient.

        Callers must authorize the recipient and check entitlements before calling
        this transport primitive. The recipient ID is never inferred from message
        content and the bot token is never included in raised error text.
        """
        normalized_chat_id = chat_id.strip()
        normalized_message = message.strip()
        if not normalized_chat_id:
            raise ValueError("Telegram chat ID cannot be empty")
        if not normalized_message:
            raise ValueError("Telegram message cannot be empty")

        try:
            response = self._client.post(
                f"{self.API_BASE_URL}/bot{self._bot_token}/sendMessage",
                json={"chat_id": normalized_chat_id, "text": normalized_message},
                timeout=self._timeout,
            )
        except httpx.TimeoutException:
            # Telegram may have accepted the request before the client timed out.
            raise TelegramDeliveryOutcomeUnknown(
                "Telegram request timed out; delivery outcome is unknown"
            ) from None
        except httpx.RequestError as error:
            # Connection loss can happen after the remote side accepted the request.
            raise TelegramDeliveryOutcomeUnknown(
                f"Telegram request outcome unknown: {error.__class__.__name__}"
            ) from None

        if response.status_code >= 500:
            raise TelegramDeliveryOutcomeUnknown(
                f"Telegram returned HTTP {response.status_code}; delivery outcome is unknown"
            )
        if response.status_code >= 400:
            raise TelegramNotificationProviderError(
                f"Telegram rejected the request with HTTP status {response.status_code}"
            )

        try:
            body: dict[str, Any] = response.json()
        except ValueError:
            raise TelegramDeliveryOutcomeUnknown(
                "Telegram returned an invalid response; delivery outcome is unknown"
            ) from None

        if body.get("ok") is not True:
            description = body.get("description")
            detail = str(description) if description else "provider rejected the request"
            if self._bot_token in detail:
                detail = "provider rejected the request"
            raise TelegramNotificationProviderError(
                f"Telegram rejected the request: {detail}"
            )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @staticmethod
    def _format_message(candidate: AlertCandidate) -> str:
        snapshot = str(candidate.snapshot_id) if candidate.snapshot_id is not None else "unknown"
        classification = getattr(candidate.classification, "value", candidate.classification)
        return (
            "EGX Stock Alert\n"
            f"Stock ID: {candidate.stock_id}\n"
            f"Classification: {classification}\n"
            f"Stock Quality: {candidate.stock_quality_score}\n"
            f"Entry Quality: {candidate.entry_quality_score}\n"
            f"Snapshot: {snapshot}"
        )
