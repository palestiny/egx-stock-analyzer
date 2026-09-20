from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class InfrastructureConfig:
    """Configuration for infrastructure composition."""

    analysis_database_path: str = "storage/analysis.db"
    operator_token: str | None = None
    user_bearer_tokens: dict[str, UUID] = field(default_factory=dict)
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_timeout_seconds: float = 10.0
    automatic_alert_delivery_channel: str = "telegram"

    @classmethod
    def from_environment(cls) -> InfrastructureConfig:
        user_bearer_tokens = _parse_user_bearer_tokens(os.getenv("EGX_USER_TOKENS"))
        return cls(
            analysis_database_path=os.getenv(
                "EGX_ANALYSIS_DATABASE_PATH",
                "storage/analysis.db",
            ),
            operator_token=os.getenv("EGX_OPERATOR_TOKEN"),
            user_bearer_tokens=user_bearer_tokens,
            telegram_bot_token=os.getenv("EGX_TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("EGX_TELEGRAM_CHAT_ID"),
            telegram_timeout_seconds=float(
                os.getenv("EGX_TELEGRAM_TIMEOUT_SECONDS", "10")
            ),
            automatic_alert_delivery_channel=os.getenv(
                "EGX_AUTOMATIC_ALERT_DELIVERY_CHANNEL",
                "telegram",
            ),
        )


def _parse_user_bearer_tokens(raw: str | None) -> dict[str, UUID]:
    if raw is None or not raw.strip():
        return {}

    try:
        values = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("EGX_USER_TOKENS must contain valid JSON") from error

    if not isinstance(values, dict):
        raise ValueError("EGX_USER_TOKENS must be a JSON object")

    tokens: dict[str, UUID] = {}
    for raw_user_id, raw_token in values.items():
        try:
            user_id = UUID(str(raw_user_id))
        except (TypeError, ValueError) as error:
            raise ValueError("EGX_USER_TOKENS contains an invalid user ID") from error

        if not isinstance(raw_token, str) or not raw_token.strip():
            raise ValueError("EGX_USER_TOKENS contains an empty token")

        token = raw_token.strip()
        if token in tokens:
            raise ValueError("EGX_USER_TOKENS contains duplicate credentials")

        tokens[token] = user_id

    return tokens
