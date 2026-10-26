from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.application.opportunities.opportunity_store import (
    OpportunityStateConflict,
)
from app.domain.opportunity.trading_opportunity import (
    OpportunityEvidence,
    OpportunityLifecycleEvent,
    OpportunityStatus,
    OpportunityTarget,
    TradingOpportunity,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteTradingOpportunityStore:
    """Persist current opportunity state and append-only lifecycle events."""

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
                CREATE TABLE IF NOT EXISTS trading_opportunities (
                    opportunity_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trading_opportunities_status_symbol
                ON trading_opportunities(status, symbol)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_lifecycle_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    opportunity_id TEXT NOT NULL,
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    evidence_version TEXT NULL,
                    FOREIGN KEY(opportunity_id)
                        REFERENCES trading_opportunities(opportunity_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_opportunity_events_timeline
                ON opportunity_lifecycle_events(opportunity_id, sequence)
                """
            )

    def create(self, opportunity: TradingOpportunity) -> None:
        if opportunity.status is not OpportunityStatus.DRAFT:
            raise ValueError("A new opportunity must start in draft status")
        if opportunity.lifecycle_events:
            raise ValueError("A new opportunity cannot contain lifecycle events")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trading_opportunities(
                    opportunity_id, symbol, timeframe, status, version, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(opportunity.opportunity_id),
                    opportunity.symbol,
                    opportunity.timeframe,
                    opportunity.status.value,
                    opportunity.version,
                    self._serialize(opportunity),
                ),
            )

    def get(self, opportunity_id: UUID) -> TradingOpportunity | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT opportunity_id, symbol, timeframe, status, version, payload_json
                FROM trading_opportunities
                WHERE opportunity_id = ?
                """,
                (str(opportunity_id),),
            ).fetchone()
            if row is None:
                return None
            events = self._read_events(connection, opportunity_id)
            return self._to_opportunity(row, events)

    def append_transition(
        self,
        opportunity: TradingOpportunity,
        *,
        expected_status: OpportunityStatus,
    ) -> TradingOpportunity:
        if not opportunity.lifecycle_events:
            raise ValueError("A transitioned opportunity must include a lifecycle event")
        event = opportunity.lifecycle_events[-1]
        if event.opportunity_id != opportunity.opportunity_id:
            raise ValueError("Lifecycle event belongs to a different opportunity")
        if event.from_status is not expected_status:
            raise ValueError("Lifecycle event does not match expected prior status")
        if event.to_status is not opportunity.status:
            raise ValueError("Lifecycle event target status does not match opportunity status")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                "SELECT opportunity_id FROM opportunity_lifecycle_events WHERE event_id = ?",
                (str(event.event_id),),
            ).fetchone()
            if duplicate is not None:
                if str(duplicate[0]) != str(opportunity.opportunity_id):
                    raise ValueError("Lifecycle event ID is already used by another opportunity")
                connection.commit()
                existing = self.get(opportunity.opportunity_id)
                if existing is None:
                    raise OpportunityStateConflict("Opportunity disappeared during replay")
                return existing

            updated = connection.execute(
                """
                UPDATE trading_opportunities
                SET status = ?, payload_json = ?
                WHERE opportunity_id = ? AND status = ?
                """,
                (
                    opportunity.status.value,
                    self._serialize(opportunity),
                    str(opportunity.opportunity_id),
                    expected_status.value,
                ),
            )
            if updated.rowcount != 1:
                raise OpportunityStateConflict(
                    "Opportunity state changed or the opportunity does not exist"
                )

            connection.execute(
                """
                INSERT INTO opportunity_lifecycle_events(
                    event_id, opportunity_id, from_status, to_status,
                    occurred_at, reason, actor, evidence_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    str(event.opportunity_id),
                    event.from_status.value,
                    event.to_status.value,
                    event.occurred_at.isoformat(),
                    event.reason,
                    event.actor,
                    event.evidence_version,
                ),
            )
            connection.commit()

        persisted = self.get(opportunity.opportunity_id)
        if persisted is None:
            raise OpportunityStateConflict("Opportunity was not readable after transition")
        return persisted

    def list_by_status(
        self,
        statuses: tuple[OpportunityStatus, ...],
        *,
        limit: int = 100,
    ) -> tuple[TradingOpportunity, ...]:
        if limit <= 0:
            raise ValueError("Opportunity list limit must be positive")
        if not statuses:
            return ()

        status_values = tuple(dict.fromkeys(status.value for status in statuses))
        placeholders = ",".join("?" for _ in status_values)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT opportunity_id
                FROM trading_opportunities
                WHERE status IN ({placeholders})
                ORDER BY symbol, opportunity_id
                LIMIT ?
                """,
                (*status_values, limit),
            ).fetchall()
        result = []
        for row in rows:
            opportunity = self.get(UUID(str(row[0])))
            if opportunity is not None:
                result.append(opportunity)
        return tuple(result)

    @staticmethod
    def _serialize(opportunity: TradingOpportunity) -> str:
        payload = {
            "strategy_version": opportunity.strategy_version,
            "created_at": opportunity.created_at.isoformat(),
            "expires_at": opportunity.expires_at.isoformat(),
            "entry_low": str(opportunity.entry_low),
            "entry_high": str(opportunity.entry_high),
            "invalidation_price": str(opportunity.invalidation_price),
            "targets": [
                {"price": str(target.price), "rationale": target.rationale}
                for target in opportunity.targets
            ],
            "evidence": [
                {
                    "evidence_type": item.evidence_type,
                    "description": item.description,
                    "observed_at": item.observed_at.isoformat(),
                    "source": item.source,
                    "source_version": item.source_version,
                }
                for item in opportunity.evidence
            ],
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _read_events(
        connection: sqlite3.Connection,
        opportunity_id: UUID,
    ) -> tuple[OpportunityLifecycleEvent, ...]:
        rows = connection.execute(
            """
            SELECT event_id, opportunity_id, from_status, to_status, occurred_at,
                   reason, actor, evidence_version
            FROM opportunity_lifecycle_events
            WHERE opportunity_id = ?
            ORDER BY sequence
            """,
            (str(opportunity_id),),
        ).fetchall()
        return tuple(
            OpportunityLifecycleEvent(
                event_id=UUID(str(row[0])),
                opportunity_id=UUID(str(row[1])),
                from_status=OpportunityStatus(str(row[2])),
                to_status=OpportunityStatus(str(row[3])),
                occurred_at=datetime.fromisoformat(str(row[4])),
                reason=str(row[5]),
                actor=str(row[6]),
                evidence_version=str(row[7]) if row[7] is not None else None,
            )
            for row in rows
        )

    @staticmethod
    def _to_opportunity(
        row: tuple[object, ...],
        events: tuple[OpportunityLifecycleEvent, ...],
    ) -> TradingOpportunity:
        payload = json.loads(str(row[5]))
        return TradingOpportunity(
            opportunity_id=UUID(str(row[0])),
            symbol=str(row[1]),
            timeframe=str(row[2]),
            strategy_version=str(payload["strategy_version"]),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            expires_at=datetime.fromisoformat(str(payload["expires_at"])),
            entry_low=Decimal(str(payload["entry_low"])),
            entry_high=Decimal(str(payload["entry_high"])),
            invalidation_price=Decimal(str(payload["invalidation_price"])),
            targets=tuple(
                OpportunityTarget(
                    price=Decimal(str(item["price"])),
                    rationale=str(item["rationale"]),
                )
                for item in payload["targets"]
            ),
            evidence=tuple(
                OpportunityEvidence(
                    evidence_type=str(item["evidence_type"]),
                    description=str(item["description"]),
                    observed_at=datetime.fromisoformat(str(item["observed_at"])),
                    source=str(item["source"]),
                    source_version=str(item["source_version"]),
                )
                for item in payload["evidence"]
            ),
            status=OpportunityStatus(str(row[3])),
            version=int(row[4]),
            lifecycle_events=events,
        )
