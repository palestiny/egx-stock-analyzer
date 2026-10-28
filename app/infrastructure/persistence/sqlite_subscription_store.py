from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.subscriptions.store import SubscriptionStore
from app.domain.subscriptions.model import (
    EntitlementGrant,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteSubscriptionStore(SubscriptionStore):
    """Versioned plan snapshots and auditable subscription lifecycle persistence."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    plan_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    display_name TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    entitlements_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(plan_id, version)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    plan_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payment_provider TEXT NULL,
                    payment_reference TEXT NULL,
                    FOREIGN KEY(plan_id, plan_version)
                        REFERENCES subscription_plans(plan_id, version)
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_subscription_payment_reference
                ON subscriptions(payment_provider, payment_reference)
                WHERE payment_provider IS NOT NULL AND payment_reference IS NOT NULL
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_subscription_user_status
                ON subscriptions(user_id, status, created_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subscription_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    event TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    previous_status TEXT NULL,
                    new_status TEXT NOT NULL,
                    FOREIGN KEY(subscription_id) REFERENCES subscriptions(subscription_id)
                )
                """
            )

    def save_plan(self, plan: SubscriptionPlan) -> None:
        payload = self._serialize_entitlements(plan.entitlements)
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT display_name, active, entitlements_json, created_at
                FROM subscription_plans WHERE plan_id = ? AND version = ?
                """,
                (plan.plan_id, plan.version),
            ).fetchone()
            expected = (
                plan.display_name,
                int(plan.active),
                payload,
                plan.created_at.isoformat(),
            )
            if existing is not None:
                normalized = (
                    str(existing[0]),
                    int(str(existing[1])),
                    str(existing[2]),
                    str(existing[3]),
                )
                if normalized != expected:
                    raise ValueError("subscription plan versions are immutable")
                return
            connection.execute(
                """
                INSERT INTO subscription_plans(
                    plan_id, version, display_name, active, entitlements_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.version,
                    plan.display_name,
                    int(plan.active),
                    payload,
                    plan.created_at.isoformat(),
                ),
            )

    def get_plan(self, plan_id: str, version: int) -> SubscriptionPlan | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT plan_id, version, display_name, active, entitlements_json, created_at
                FROM subscription_plans WHERE plan_id = ? AND version = ?
                """,
                (plan_id, version),
            ).fetchone()
        return self._to_plan(row) if row else None

    def create(self, subscription: Subscription, *, actor: str, reason: str) -> None:
        self._require_actor_reason(actor, reason)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO subscriptions(
                    subscription_id, user_id, plan_id, plan_version, status,
                    created_at, starts_at, expires_at, updated_at,
                    payment_provider, payment_reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(subscription.subscription_id),
                    str(subscription.user_id),
                    subscription.plan_id,
                    subscription.plan_version,
                    subscription.status.value,
                    subscription.created_at.isoformat(),
                    subscription.starts_at.isoformat(),
                    subscription.expires_at.isoformat(),
                    subscription.updated_at.isoformat(),
                    subscription.payment_provider,
                    subscription.payment_reference,
                ),
            )
            connection.execute(
                """
                INSERT INTO subscription_events(
                    subscription_id, actor, event, reason, occurred_at,
                    previous_status, new_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(subscription.subscription_id),
                    actor.strip(),
                    "SUBSCRIPTION_CREATED",
                    reason.strip(),
                    subscription.created_at.isoformat(),
                    None,
                    subscription.status.value,
                ),
            )

    def get(self, subscription_id: UUID) -> Subscription | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT subscription_id, user_id, plan_id, plan_version, status,
                    created_at, starts_at, expires_at, updated_at,
                    payment_provider, payment_reference
                FROM subscriptions WHERE subscription_id = ?
                """,
                (str(subscription_id),),
            ).fetchone()
        return self._to_subscription(row) if row else None

    def latest_for_user(self, user_id: UUID) -> Subscription | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT subscription_id, user_id, plan_id, plan_version, status,
                    created_at, starts_at, expires_at, updated_at,
                    payment_provider, payment_reference
                FROM subscriptions
                WHERE user_id = ?
                ORDER BY created_at DESC, subscription_id DESC
                LIMIT 1
                """,
                (str(user_id),),
            ).fetchone()
        return self._to_subscription(row) if row else None

    def current_for_user(
        self,
        user_id: UUID,
        *,
        now: datetime,
    ) -> Subscription | None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT subscription_id, user_id, plan_id, plan_version, status,
                    created_at, starts_at, expires_at, updated_at,
                    payment_provider, payment_reference
                FROM subscriptions
                WHERE user_id = ? AND status = 'ACTIVE'
                    AND starts_at <= ? AND expires_at > ?
                ORDER BY created_at DESC, subscription_id DESC
                LIMIT 1
                """,
                (str(user_id), now.isoformat(), now.isoformat()),
            ).fetchone()
        return self._to_subscription(row) if row else None

    def transition(
        self,
        subscription_id: UUID,
        new_status: SubscriptionStatus,
        *,
        occurred_at: datetime,
        actor: str,
        reason: str,
    ) -> Subscription:
        self._require_actor_reason(actor, reason)
        current = self.get(subscription_id)
        if current is None:
            raise LookupError("subscription was not found")
        updated = current.transition_to(new_status, occurred_at=occurred_at)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE subscriptions SET status = ?, updated_at = ?
                WHERE subscription_id = ? AND status = ? AND updated_at = ?
                """,
                (
                    updated.status.value,
                    updated.updated_at.isoformat(),
                    str(subscription_id),
                    current.status.value,
                    current.updated_at.isoformat(),
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("subscription changed concurrently; retry transition")
            connection.execute(
                """
                INSERT INTO subscription_events(
                    subscription_id, actor, event, reason, occurred_at,
                    previous_status, new_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(subscription_id),
                    actor.strip(),
                    "STATUS_TRANSITION",
                    reason.strip(),
                    occurred_at.isoformat(),
                    current.status.value,
                    updated.status.value,
                ),
            )
        return updated

    @staticmethod
    def _serialize_entitlements(entitlements: tuple[EntitlementGrant, ...]) -> str:
        return json.dumps(
            [
                {"code": item.code, "enabled": item.enabled, "limit": item.limit}
                for item in entitlements
            ],
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _to_plan(row: tuple[object, ...]) -> SubscriptionPlan:
        entitlements = json.loads(str(row[4]))
        return SubscriptionPlan(
            plan_id=str(row[0]),
            version=int(str(row[1])),
            display_name=str(row[2]),
            active=bool(int(str(row[3]))),
            entitlements=tuple(
                EntitlementGrant(
                    code=str(item["code"]),
                    enabled=bool(item["enabled"]),
                    limit=int(item["limit"]) if item["limit"] is not None else None,
                )
                for item in entitlements
            ),
            created_at=datetime.fromisoformat(str(row[5])),
        )

    @staticmethod
    def _to_subscription(row: tuple[object, ...]) -> Subscription:
        return Subscription(
            subscription_id=UUID(str(row[0])),
            user_id=UUID(str(row[1])),
            plan_id=str(row[2]),
            plan_version=int(str(row[3])),
            status=SubscriptionStatus(str(row[4])),
            created_at=datetime.fromisoformat(str(row[5])),
            starts_at=datetime.fromisoformat(str(row[6])),
            expires_at=datetime.fromisoformat(str(row[7])),
            updated_at=datetime.fromisoformat(str(row[8])),
            payment_provider=str(row[9]) if row[9] is not None else None,
            payment_reference=str(row[10]) if row[10] is not None else None,
        )

    @staticmethod
    def _require_actor_reason(actor: str, reason: str) -> None:
        if not actor.strip():
            raise ValueError("subscription actor is required")
        if not reason.strip():
            raise ValueError("subscription reason is required")
