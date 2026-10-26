from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Protocol
from uuid import UUID


@dataclass(frozen=True)
class IssuedTelegramLinkChallenge:
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class LinkedTelegramAccount:
    user_id: UUID
    chat_id: str


class TelegramChatAlreadyLinked(ValueError):
    """Raised when a Telegram chat is already owned by another account."""


class TelegramAccountLinkStore(Protocol):
    def create_challenge(
        self,
        user_id: UUID,
        token_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None: ...

    def consume_challenge(
        self,
        token_hash: str,
        chat_id: str,
        now: datetime,
    ) -> UUID | None: ...

    def get_chat_id(self, user_id: UUID) -> str | None: ...
    def list_linked_accounts(self) -> tuple[LinkedTelegramAccount, ...]: ...
    def claim_webhook_update(self, update_id: str, now: datetime) -> bool: ...

    def unlink(self, user_id: UUID, occurred_at: datetime) -> bool: ...


class TelegramAccountLinkingService:
    """Issue single-use Telegram link tokens without storing their plaintext value."""

    DEFAULT_TTL = timedelta(minutes=10)

    def __init__(
        self,
        store: TelegramAccountLinkStore,
        *,
        token_factory: Callable[[], str] | None = None,
        ttl: timedelta = DEFAULT_TTL,
    ) -> None:
        if ttl <= timedelta(0):
            raise ValueError("Telegram link challenge TTL must be positive")
        self._store = store
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._ttl = ttl

    def issue(self, user_id: UUID, *, now: datetime) -> IssuedTelegramLinkChallenge:
        self._require_aware(now, "now")
        token = self._token_factory()
        if not token.strip():
            raise ValueError("Telegram link token cannot be empty")
        expires_at = now + self._ttl
        self._store.create_challenge(
            user_id,
            self._hash_token(token),
            now,
            expires_at,
        )
        return IssuedTelegramLinkChallenge(token=token, expires_at=expires_at)

    def consume(
        self,
        token: str,
        chat_id: str,
        *,
        now: datetime,
    ) -> UUID | None:
        self._require_aware(now, "now")
        if not token.strip():
            return None
        if not chat_id.strip():
            raise ValueError("Telegram chat ID cannot be empty")
        return self._store.consume_challenge(
            self._hash_token(token),
            chat_id.strip(),
            now,
        )

    def claim_webhook_update(self, update_id: str, *, now: datetime) -> bool:
        self._require_aware(now, "now")
        if not update_id.strip():
            raise ValueError("Telegram update ID is required")
        return self._store.claim_webhook_update(update_id.strip(), now)

    def get_chat_id(self, user_id: UUID) -> str | None:
        return self._store.get_chat_id(user_id)

    def unlink(self, user_id: UUID, *, now: datetime) -> bool:
        self._require_aware(now, "now")
        return self._store.unlink(user_id, now)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
