from typing import Protocol


class TelegramMessageSender(Protocol):
    """Application-facing transport port for a prepared Telegram message."""

    def send_message(self, chat_id: str, message: str) -> None: ...
