from __future__ import annotations

from typing import Any

import httpx

from app.application.notifications.provider import NotificationProvider
from app.domain.reporting.alerts import AlertCandidate


class TelegramNotificationProviderError(RuntimeError):
    """Raised when Telegram notification delivery cannot be completed."""


class TelegramNotificationProvider(NotificationProvider):
    CHANNEL = "telegram"
    DEFAULT_TIMEOUT_SECONDS = 10.0
    API_BASE_URL = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        *,
        client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        normalized_token = bot_token.strip()
        normalized_chat_id = chat_id.strip()
        if not normalized_token:
            raise ValueError("Telegram bot token cannot be empty")
        if not normalized_chat_id:
            raise ValueError("Telegram chat ID cannot be empty")
        if timeout <= 0:
            raise ValueError("Telegram timeout must be positive")

        self._bot_token = normalized_token
        self._chat_id = normalized_chat_id
        self._timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def send(self, candidate: AlertCandidate, channel: str) -> None:
        if channel.strip().lower() != self.CHANNEL:
            raise TelegramNotificationProviderError(
                f"Unsupported notification channel: {channel}"
            )

        payload = {
            "chat_id": self._chat_id,
            "text": self._format_message(candidate),
        }

        try:
            response = self._client.post(
                f"{self.API_BASE_URL}/bot{self._bot_token}/sendMessage",
                json=payload,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as error:
            raise TelegramNotificationProviderError(
                "Telegram request timed out"
            ) from error
        except httpx.RequestError as error:
            raise TelegramNotificationProviderError(
                f"Telegram request failed: {error.__class__.__name__}"
            ) from error

        if response.status_code >= 400:
            raise TelegramNotificationProviderError(
                f"Telegram request failed with HTTP status {response.status_code}"
            )

        try:
            body: dict[str, Any] = response.json()
        except ValueError as error:
            raise TelegramNotificationProviderError(
                "Telegram returned an invalid response"
            ) from error

        if body.get("ok") is not True:
            description = body.get("description")
            detail = str(description) if description else "provider rejected the request"
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
