from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.notifications.telegram_account_linking import (
    TelegramAccountLinkingService,
    TelegramChatAlreadyLinked,
)
from app.infrastructure.persistence.sqlite_telegram_account_link_store import (
    SQLiteTelegramAccountLinkStore,
)


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def service_for(database, token: str = "single-use-token"):
    return TelegramAccountLinkingService(
        SQLiteTelegramAccountLinkStore(database),
        token_factory=lambda: token,
    )


def test_telegram_link_challenge_is_single_use_and_restart_safe(tmp_path) -> None:
    database = tmp_path / "accounts.db"
    user_id = uuid4()
    service = service_for(database)
    challenge = service.issue(user_id, now=NOW)

    assert challenge.token == "single-use-token"
    assert challenge.expires_at == NOW + timedelta(minutes=10)
    assert service.get_chat_id(user_id) is None
    assert service.consume(
        challenge.token,
        "chat-123",
        now=NOW + timedelta(minutes=1),
    ) == user_id

    reopened = service_for(database, "another-token")
    assert reopened.get_chat_id(user_id) == "chat-123"
    assert reopened.consume(
        challenge.token,
        "chat-123",
        now=NOW + timedelta(minutes=2),
    ) == user_id
    assert reopened.consume(
        challenge.token,
        "different-chat",
        now=NOW + timedelta(minutes=2),
    ) is None


def test_telegram_link_challenge_expiry_and_naive_time_are_rejected(tmp_path) -> None:
    service = service_for(tmp_path / "accounts.db")
    user_id = uuid4()
    challenge = service.issue(user_id, now=NOW)

    assert service.consume(
        challenge.token,
        "chat-123",
        now=challenge.expires_at,
    ) is None

    with pytest.raises(ValueError, match="timezone-aware"):
        service.issue(user_id, now=datetime(2026, 10, 26, 12, 0))


def test_telegram_chat_cannot_be_linked_to_two_users(tmp_path) -> None:
    database = tmp_path / "accounts.db"
    first_user = uuid4()
    second_user = uuid4()
    first = service_for(database, "token-one")
    second = service_for(database, "token-two")

    first.issue(first_user, now=NOW)
    second.issue(second_user, now=NOW)

    assert first.consume("token-one", "shared-chat", now=NOW) == first_user
    with pytest.raises(TelegramChatAlreadyLinked, match="another account"):
        second.consume("token-two", "shared-chat", now=NOW)

    assert first.get_chat_id(first_user) == "shared-chat"
    assert second.get_chat_id(second_user) is None


def test_telegram_relink_replaces_old_chat_and_unlink_is_audited(tmp_path) -> None:
    database = tmp_path / "accounts.db"
    user_id = uuid4()
    first = service_for(database, "token-one")
    first.issue(user_id, now=NOW)
    assert first.consume("token-one", "old-chat", now=NOW) == user_id

    second = service_for(database, "token-two")
    second.issue(user_id, now=NOW + timedelta(minutes=1))
    assert second.consume(
        "token-two",
        "new-chat",
        now=NOW + timedelta(minutes=2),
    ) == user_id
    assert second.get_chat_id(user_id) == "new-chat"

    assert second.unlink(user_id, now=NOW + timedelta(minutes=3)) is True
    assert second.get_chat_id(user_id) is None
    assert second.unlink(user_id, now=NOW + timedelta(minutes=4)) is False


def test_telegram_link_challenge_does_not_store_plaintext_token(tmp_path) -> None:
    database = tmp_path / "accounts.db"
    service = service_for(database, "do-not-store-this-token")
    service.issue(uuid4(), now=NOW)

    import sqlite3

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT token_hash FROM telegram_link_challenges"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0][0] != "do-not-store-this-token"
    assert len(rows[0][0]) == 64


def test_telegram_webhook_update_claim_is_idempotent_and_persistent(tmp_path) -> None:
    database = tmp_path / "accounts.db"
    store = SQLiteTelegramAccountLinkStore(database)

    assert store.claim_webhook_update("update-101", NOW) is True
    assert store.claim_webhook_update("update-101", NOW) is False
    assert SQLiteTelegramAccountLinkStore(database).claim_webhook_update("update-101", NOW) is False


def test_telegram_recipient_directory_lists_linked_accounts(tmp_path) -> None:
    from app.application.notifications.telegram_account_linking import LinkedTelegramAccount

    database = tmp_path / "accounts.db"
    user_id = uuid4()
    service = service_for(database, "recipient-token")
    service.issue(user_id, now=NOW)
    assert service.consume("recipient-token", "chat-123", now=NOW) == user_id

    store = SQLiteTelegramAccountLinkStore(database)
    assert store.list_linked_accounts() == (
        LinkedTelegramAccount(user_id=user_id, chat_id="chat-123"),
    )
