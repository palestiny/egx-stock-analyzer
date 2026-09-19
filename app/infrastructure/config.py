from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class InfrastructureConfig:
    """Configuration for infrastructure composition.

    External data-source credentials are intentionally not required for the
    current development vertical slice. Yahoo Finance is used as the live
    data source for both market and fundamental data.
    """

    analysis_database_path: str = "storage/analysis.db"
    operator_token: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_timeout_seconds: float = 10.0
    automatic_alert_delivery_channel: str = "telegram"

    @classmethod
    def from_environment(cls) -> InfrastructureConfig:
        return cls(
            analysis_database_path=os.getenv(
                "EGX_ANALYSIS_DATABASE_PATH",
                "storage/analysis.db",
            ),
            operator_token=os.getenv("EGX_OPERATOR_TOKEN"),
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
