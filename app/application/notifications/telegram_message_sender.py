from typing import Protocol


class TelegramDeliveryRejected(RuntimeError):
    """Telegram definitively rejected a send request; retry is a policy decision."""


class TelegramDeliveryOutcomeUnknown(RuntimeError):
    """The request may have reached Telegram, so automatic resend is unsafe."""


class TelegramMessageSender(Protocol):
    """Application-facing transport port for a prepared Telegram message.

    Implementations expose the effective request timeout so the dispatcher can
    derive its claim lease from the configured transport behavior.
    """

    @property
    def timeout_seconds(self) -> float: ...

    def send_message(self, chat_id: str, message: str) -> None: ...
