from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from app.application.signals.store import (
    PublishedOpportunityRevision,
    SignalHistoryStore,
    SignalPublicationRecord,
    SignalRecord,
    SignalRevisionLink,
)
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteSignalHistoryStore(SignalHistoryStore):
    """Durable signal identity and append-only signal history backed by SQLite."""

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
                CREATE TABLE IF NOT EXISTS signal_identities (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    UNIQUE(symbol, strategy_id, strategy_version, generated_at)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    signal_json TEXT NOT NULL,
                    UNIQUE(signal_id, event, recorded_at),
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_revision_links (
                    signal_id TEXT PRIMARY KEY,
                    parent_signal_id TEXT NOT NULL,
                    revision_number INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    parent_snapshot_sha256 TEXT NOT NULL,
                    revised_snapshot_sha256 TEXT NOT NULL,
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id),
                    FOREIGN KEY(parent_signal_id) REFERENCES signal_identities(signal_id),
                    CHECK(signal_id != parent_signal_id),
                    CHECK(revision_number >= 2)
                )
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_signal_revision_links_no_update
                BEFORE UPDATE ON signal_revision_links
                BEGIN
                    SELECT RAISE(ABORT, 'signal revision links are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_signal_revision_links_no_delete
                BEFORE DELETE ON signal_revision_links
                BEGIN
                    SELECT RAISE(ABORT, 'signal revision links are append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_history_timeline
                ON signal_history(signal_id, id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_identity_symbol
                ON signal_identities(symbol)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signal_revision_parent
                ON signal_revision_links(parent_signal_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_opportunity_projection (
                    signal_id TEXT PRIMARY KEY,
                    latest_history_id INTEGER NOT NULL,
                    publication_history_id INTEGER NOT NULL,
                    FOREIGN KEY(signal_id) REFERENCES signal_identities(signal_id),
                    FOREIGN KEY(latest_history_id) REFERENCES signal_history(id),
                    FOREIGN KEY(publication_history_id) REFERENCES signal_history(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_signal_history_projection_insert
                AFTER INSERT ON signal_history
                BEGIN
                    INSERT INTO signal_opportunity_projection(
                        signal_id, latest_history_id, publication_history_id
                    )
                    SELECT
                        NEW.signal_id,
                        NEW.id,
                        CASE
                            WHEN NEW.event IN ('PUBLISHED', 'PUBLISHED_VERSION') THEN NEW.id
                            ELSE NULL
                        END
                    WHERE NEW.event IN ('PUBLISHED', 'PUBLISHED_VERSION')
                    ON CONFLICT(signal_id) DO UPDATE SET
                        latest_history_id = NEW.id,
                        publication_history_id = COALESCE(
                            signal_opportunity_projection.publication_history_id,
                            excluded.publication_history_id
                        );

                    UPDATE signal_opportunity_projection
                    SET latest_history_id = NEW.id
                    WHERE signal_id = NEW.signal_id
                      AND NEW.event NOT IN ('PUBLISHED', 'PUBLISHED_VERSION');
                END
                """
            )
            connection.execute(
                """
                INSERT INTO signal_opportunity_projection(
                    signal_id, latest_history_id, publication_history_id
                )
                SELECT
                    signal_id,
                    MAX(id),
                    MIN(CASE
                        WHEN event IN ('PUBLISHED', 'PUBLISHED_VERSION') THEN id
                    END)
                FROM signal_history
                GROUP BY signal_id
                HAVING MIN(CASE
                    WHEN event IN ('PUBLISHED', 'PUBLISHED_VERSION') THEN id
                END) IS NOT NULL
                ON CONFLICT(signal_id) DO UPDATE SET
                    latest_history_id = excluded.latest_history_id,
                    publication_history_id = excluded.publication_history_id
                """
            )

    def record(self, signal: Signal, event: str, recorded_at: datetime) -> SignalRecord:
        if not event.strip():
            raise ValueError("event is required")
        self._require_aware(recorded_at, "recorded_at")
        normalized_symbol = signal.symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("signal symbol is required")
        payload = self._serialize_signal(signal)
        identity = (
            normalized_symbol,
            signal.strategy_id,
            signal.strategy_version,
            signal.generated_at.isoformat(),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO signal_identities(
                    signal_id, symbol, strategy_id, strategy_version, generated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid4()), *identity),
            )
            row = connection.execute(
                """
                SELECT signal_id FROM signal_identities
                WHERE symbol = ? AND strategy_id = ? AND strategy_version = ? AND generated_at = ?
                """,
                identity,
            ).fetchone()
            if row is None:
                raise RuntimeError("Signal identity was not persisted")
            signal_id = UUID(str(row[0]))
            existing = connection.execute(
                """
                SELECT signal_json FROM signal_history
                WHERE signal_id = ? AND event = ? AND recorded_at = ?
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat()),
            ).fetchone()
            if existing is not None:
                if str(existing[0]) != payload:
                    raise ValueError("different signal event already recorded")
                return SignalRecord(signal_id, signal, recorded_at, event.strip())

            connection.execute(
                """
                INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                VALUES (?, ?, ?, ?)
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat(), payload),
            )
        return SignalRecord(signal_id, signal, recorded_at, event.strip())

    def record_for_signal(
        self,
        signal_id: UUID,
        signal: Signal,
        event: str,
        recorded_at: datetime,
    ) -> SignalRecord:
        if not event.strip():
            raise ValueError("event is required")
        self._require_aware(recorded_at, "recorded_at")
        payload = self._serialize_signal(signal)
        with self._connect() as connection:
            identity = connection.execute(
                "SELECT symbol, strategy_id, generated_at FROM signal_identities WHERE signal_id = ?",
                (str(signal_id),),
            ).fetchone()
            if identity is None:
                raise ValueError("signal identity does not exist")
            if (
                str(identity[0]).strip().upper() != signal.symbol.strip().upper()
                or str(identity[1]) != signal.strategy_id
                or datetime.fromisoformat(str(identity[2])) != signal.generated_at
            ):
                raise ValueError("signal update must preserve its immutable identity")
            latest_payload = connection.execute(
                """
                SELECT signal_json FROM signal_history
                WHERE signal_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(signal_id),),
            ).fetchone()
            if latest_payload is None:
                raise ValueError("signal identity has no history")
            current_signal = self._deserialize_signal(str(latest_payload[0]))
            if current_signal.strategy_version != signal.strategy_version:
                raise ValueError("signal update must preserve its immutable identity")
            existing = connection.execute(
                """
                SELECT signal_json FROM signal_history
                WHERE signal_id = ? AND event = ? AND recorded_at = ?
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat()),
            ).fetchone()
            if existing is not None:
                if str(existing[0]) != payload:
                    raise ValueError("different signal event already recorded")
                return SignalRecord(signal_id, signal, recorded_at, event.strip())
            connection.execute(
                """
                INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                VALUES (?, ?, ?, ?)
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat(), payload),
            )
        return SignalRecord(signal_id, signal, recorded_at, event.strip())

    def record_revision(
        self,
        signal: Signal,
        event: str,
        recorded_at: datetime,
        *,
        parent_signal_id: UUID,
        reason: str,
    ) -> SignalRecord:
        if not event.strip():
            raise ValueError("event is required")
        if not reason.strip():
            raise ValueError("revision reason is required")
        self._require_aware(recorded_at, "recorded_at")
        parent = self.get(parent_signal_id)
        if parent is None:
            raise ValueError("parent signal identity does not exist")
        if parent.signal.status is not SignalStatus.ACTIVE:
            raise ValueError("terminal opportunities cannot be revised")
        latest = self.latest_for_identity(
            parent.signal.symbol,
            parent.signal.strategy_id,
            parent.signal.strategy_version,
            parent.signal.generated_at,
        )
        if latest is None or latest.signal_id != parent_signal_id:
            raise ValueError("revision parent must be the latest opportunity revision")
        if (
            parent.signal.symbol.strip().upper() != signal.symbol.strip().upper()
            or parent.signal.strategy_id != signal.strategy_id
            or parent.signal.strategy_version != signal.strategy_version
            or parent.signal.generated_at != signal.generated_at
        ):
            raise ValueError("revision must preserve the parent opportunity identity")

        with self._connect() as connection:
            parent_link = connection.execute(
                "SELECT revision_number FROM signal_revision_links WHERE signal_id = ?",
                (str(parent_signal_id),),
            ).fetchone()
            revision_number = (int(parent_link[0]) if parent_link else 1) + 1
            signal_id = uuid4()
            synthetic_identity_version = f"{signal.strategy_version}#revision-{signal_id}"
            connection.execute(
                """
                INSERT INTO signal_identities(
                    signal_id, symbol, strategy_id, strategy_version, generated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(signal_id),
                    signal.symbol.strip().upper(),
                    signal.strategy_id,
                    synthetic_identity_version,
                    signal.generated_at.isoformat(),
                ),
            )
            payload = self._serialize_signal(signal)
            parent_payload = self._serialize_signal(parent.signal)
            connection.execute(
                """
                INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                VALUES (?, ?, ?, ?)
                """,
                (str(signal_id), event.strip(), recorded_at.isoformat(), payload),
            )
            connection.execute(
                """
                INSERT INTO signal_revision_links(
                    signal_id, parent_signal_id, revision_number, reason, recorded_at,
                    parent_snapshot_sha256, revised_snapshot_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(signal_id),
                    str(parent_signal_id),
                    revision_number,
                    reason.strip(),
                    recorded_at.isoformat(),
                    hashlib.sha256(parent_payload.encode("utf-8")).hexdigest(),
                    hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                ),
            )
        return SignalRecord(signal_id, signal, recorded_at, event.strip())

    def revision_link(self, signal_id: UUID) -> SignalRevisionLink | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT signal_id, parent_signal_id, revision_number, reason, recorded_at
                FROM signal_revision_links WHERE signal_id = ?
                """,
                (str(signal_id),),
            ).fetchone()
        if row is None:
            return None
        return SignalRevisionLink(
            signal_id=UUID(str(row[0])),
            parent_signal_id=UUID(str(row[1])),
            revision_number=int(row[2]),
            reason=str(row[3]),
            recorded_at=datetime.fromisoformat(str(row[4])),
        )

    def get(self, signal_id: UUID) -> SignalRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT signal_id, event, recorded_at, signal_json
                FROM signal_history
                WHERE signal_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(signal_id),),
            ).fetchone()
        return self._to_record(row) if row else None

    def history(self, signal_id: UUID) -> tuple[SignalRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT signal_id, event, recorded_at, signal_json
                FROM signal_history
                WHERE signal_id = ?
                ORDER BY id ASC
                """,
                (str(signal_id),),
            ).fetchall()
        return tuple(self._to_record(row) for row in rows)

    def latest(self, symbol: str) -> SignalRecord | None:
        normalized = symbol.strip().upper()
        if not normalized:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT h.signal_id, h.event, h.recorded_at, h.signal_json
                FROM signal_history h
                JOIN signal_identities i ON i.signal_id = h.signal_id
                WHERE i.symbol = ?
                ORDER BY h.id DESC
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
        return self._to_record(row) if row else None

    def latest_for_identity(
        self,
        symbol: str,
        strategy_id: str,
        strategy_version: str,
        generated_at: datetime,
    ) -> SignalRecord | None:
        normalized = symbol.strip().upper()
        for record in reversed(self.all_records()):
            if (
                record.signal.symbol.strip().upper() == normalized
                and record.signal.strategy_id == strategy_id
                and record.signal.strategy_version == strategy_version
                and record.signal.generated_at == generated_at
            ):
                return record
        return None

    def all_records(self) -> tuple[SignalRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT signal_id, event, recorded_at, signal_json
                FROM signal_history
                ORDER BY id ASC
                """
            ).fetchall()
        return tuple(self._to_record(row) for row in rows)

    def latest_active_published_opportunities(self) -> tuple[PublishedOpportunityRevision, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    latest.signal_id, latest.event, latest.recorded_at, latest.signal_json,
                    publication.signal_id, publication.event,
                    publication.recorded_at
                FROM signal_opportunity_projection AS projection
                JOIN signal_history AS latest
                  ON latest.id = projection.latest_history_id
                JOIN signal_history AS publication
                  ON publication.id = projection.publication_history_id
                WHERE (
                    json_extract(latest.signal_json, '$.status') = 'ACTIVE'
                    OR json_extract(latest.signal_json, '$.status') NOT IN (
                        'ACTIVE', 'TRIGGERED', 'INVALIDATED', 'EXPIRED', 'CLOSED'
                    )
                    OR json_type(latest.signal_json, '$.status') IS NULL
                    OR json_type(latest.signal_json, '$.status') = 'null'
                )
                  AND NOT EXISTS (
                    SELECT 1 FROM signal_revision_links AS revision
                    WHERE revision.parent_signal_id = projection.signal_id
                )
                ORDER BY projection.signal_id ASC
                """
            ).fetchall()
        candidates: list[PublishedOpportunityRevision] = []
        for row in rows:
            latest = self._to_record(row[:4])
            if latest.signal.status.value != "ACTIVE":
                continue
            publication = SignalPublicationRecord(
                signal_id=UUID(str(row[4])),
                event=str(row[5]),
                recorded_at=datetime.fromisoformat(str(row[6])),
            )
            candidates.append(PublishedOpportunityRevision(latest=latest, publication=publication))
        return tuple(candidates)

    @staticmethod
    def _require_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")

    @staticmethod
    def _serialize_signal(signal: Signal) -> str:
        payload = {
            "symbol": signal.symbol.strip().upper(),
            "direction": signal.direction.value,
            "status": signal.status.value,
            "generated_at": signal.generated_at.isoformat(),
            "timeframe": signal.timeframe,
            "entry_zone": {
                "lower": str(signal.entry_zone.lower),
                "upper": str(signal.entry_zone.upper),
            },
            "invalidation": str(signal.invalidation),
            "targets": [
                {"price": str(target.price), "label": target.label}
                for target in signal.targets
            ],
            "confidence": str(signal.confidence),
            "risk_score": str(signal.risk_score),
            "evidence": [
                {
                    "kind": evidence.kind,
                    "description": evidence.description,
                    "weight": str(evidence.weight),
                }
                for evidence in signal.evidence
            ],
            "strategy_id": signal.strategy_id,
            "strategy_version": signal.strategy_version,
            "data_timestamp": signal.data_timestamp.isoformat(),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def _to_record(cls, row: tuple[object, ...]) -> SignalRecord:
        return SignalRecord(
            signal_id=UUID(str(row[0])),
            event=str(row[1]),
            recorded_at=datetime.fromisoformat(str(row[2])),
            signal=cls._deserialize_signal(str(row[3])),
        )

    @staticmethod
    def _deserialize_signal(payload_text: str) -> Signal:
        payload = json.loads(payload_text)
        return Signal(
            symbol=str(payload["symbol"]),
            direction=SignalDirection(str(payload["direction"])),
            status=SignalStatus(str(payload["status"])),
            generated_at=datetime.fromisoformat(str(payload["generated_at"])),
            timeframe=str(payload["timeframe"]),
            entry_zone=PriceZone(
                lower=Decimal(str(payload["entry_zone"]["lower"])),
                upper=Decimal(str(payload["entry_zone"]["upper"])),
            ),
            invalidation=Decimal(str(payload["invalidation"])),
            targets=tuple(
                Target(price=Decimal(str(item["price"])), label=str(item["label"]))
                for item in payload["targets"]
            ),
            confidence=Decimal(str(payload["confidence"])),
            risk_score=Decimal(str(payload["risk_score"])),
            evidence=tuple(
                SignalEvidence(
                    kind=str(item["kind"]),
                    description=str(item["description"]),
                    weight=Decimal(str(item["weight"])),
                )
                for item in payload["evidence"]
            ),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            data_timestamp=datetime.fromisoformat(str(payload["data_timestamp"])),
        )
