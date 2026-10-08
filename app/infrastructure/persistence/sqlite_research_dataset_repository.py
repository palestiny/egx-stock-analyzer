from __future__ import annotations
from app.infrastructure.persistence.sqlite_connection import connect_sqlite

import hashlib
import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.application.research.dataset_repository import ResearchDataset
from app.domain.research.dataset import PriceAdjustment, ResearchBar, ResearchDataQuality


class ResearchDatasetConflictError(ValueError):
    """An immutable dataset identity was already registered with different contents."""


class SQLiteResearchDatasetRepository:
    """Durable immutable dataset registry and OHLCV storage."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        if str(path) != ":memory:":
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
                CREATE TABLE IF NOT EXISTS research_datasets (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    version TEXT NOT NULL,
                    adjustment TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    bar_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, timeframe, provider, version, adjustment)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_bars (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    version TEXT NOT NULL,
                    adjustment TEXT NOT NULL,
                    source_timestamp TEXT NOT NULL,
                    ingestion_timestamp TEXT NOT NULL,
                    open TEXT NOT NULL,
                    high TEXT NOT NULL,
                    low TEXT NOT NULL,
                    close TEXT NOT NULL,
                    volume TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    PRIMARY KEY (
                        symbol, timeframe, provider, version, adjustment, source_timestamp
                    ),
                    FOREIGN KEY (symbol, timeframe, provider, version, adjustment)
                        REFERENCES research_datasets(
                            symbol, timeframe, provider, version, adjustment
                        ) ON DELETE CASCADE
                )
                """
            )

    def register(self, dataset: ResearchDataset) -> str:
        """Register a dataset immutably; same identity+content is idempotent."""
        self._validate_identity(dataset)
        fingerprint = self._fingerprint(dataset)
        identity = self._identity_values(dataset)
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT fingerprint FROM research_datasets
                WHERE symbol = ? AND timeframe = ? AND provider = ? AND version = ? AND adjustment = ?
                """,
                identity,
            ).fetchone()
            if existing is not None:
                if existing[0] != fingerprint:
                    raise ResearchDatasetConflictError(
                        "dataset identity already exists with different contents; publish a new version"
                    )
                return fingerprint

            connection.execute(
                """
                INSERT INTO research_datasets (
                    symbol, timeframe, provider, version, adjustment, fingerprint, bar_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (*identity, fingerprint, len(dataset.bars)),
            )
            for bar in dataset.bars:
                connection.execute(
                    """
                    INSERT INTO research_bars (
                        symbol, timeframe, provider, version, adjustment, source_timestamp,
                        ingestion_timestamp, open, high, low, close, volume, quality
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        *identity,
                        bar.source_timestamp.isoformat(),
                        bar.ingestion_timestamp.isoformat(),
                        str(bar.open), str(bar.high), str(bar.low), str(bar.close),
                        str(bar.volume), bar.quality.value,
                    ),
                )
        return fingerprint

    def get(
        self,
        *,
        symbol: str,
        timeframe: str,
        provider: str,
        version: str,
        adjustment: PriceAdjustment,
    ) -> ResearchDataset | None:
        identity = (symbol, timeframe, provider, version, adjustment.value)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT fingerprint, bar_count FROM research_datasets
                WHERE symbol = ? AND timeframe = ? AND provider = ? AND version = ? AND adjustment = ?
                """,
                identity,
            ).fetchone()
            if row is None:
                return None
            stored_fingerprint, expected_count = row
            rows = connection.execute(
                """
                SELECT source_timestamp, ingestion_timestamp, open, high, low, close, volume, quality
                FROM research_bars
                WHERE symbol = ? AND timeframe = ? AND provider = ? AND version = ? AND adjustment = ?
                """,
                identity,
            ).fetchall()

        rows.sort(key=lambda row: datetime.fromisoformat(row[0]))
        if len(rows) != expected_count:
            raise RuntimeError("stored research dataset bar count does not match its manifest")

        bars = tuple(
            ResearchBar(
                symbol=symbol,
                timeframe=timeframe,
                source_timestamp=datetime.fromisoformat(row[0]),
                ingestion_timestamp=datetime.fromisoformat(row[1]),
                open=Decimal(row[2]),
                high=Decimal(row[3]),
                low=Decimal(row[4]),
                close=Decimal(row[5]),
                volume=Decimal(row[6]),
                provider=provider,
                dataset_version=version,
                quality=ResearchDataQuality(row[7]),
                adjustment=adjustment,
            )
            for row in rows
        )
        dataset = ResearchDataset(symbol, timeframe, provider, version, adjustment, bars)
        if self._fingerprint(dataset) != stored_fingerprint:
            raise RuntimeError("stored research dataset fingerprint verification failed")
        return dataset

    @staticmethod
    def _identity_values(dataset: ResearchDataset) -> tuple[str, str, str, str, str]:
        return (
            dataset.symbol, dataset.timeframe, dataset.provider, dataset.version,
            dataset.adjustment.value,
        )

    @staticmethod
    def _validate_identity(dataset: ResearchDataset) -> None:
        previous: datetime | None = None
        seen: set[datetime] = set()
        for bar in dataset.bars:
            if (
                bar.symbol != dataset.symbol
                or bar.timeframe != dataset.timeframe
                or bar.provider != dataset.provider
                or bar.dataset_version != dataset.version
                or bar.adjustment is not dataset.adjustment
            ):
                raise ValueError("all bars must match the registered dataset identity")
            if bar.source_timestamp in seen:
                raise ValueError("duplicate source timestamp in research dataset")
            if previous is not None and bar.source_timestamp < previous:
                raise ValueError("research dataset bars must be ordered by source timestamp")
            seen.add(bar.source_timestamp)
            previous = bar.source_timestamp

    @classmethod
    def _fingerprint(cls, dataset: ResearchDataset) -> str:
        manifest = {
            "identity": cls._identity_values(dataset),
            "bars": [
                [
                    bar.source_timestamp.isoformat(), bar.ingestion_timestamp.isoformat(),
                    str(bar.open), str(bar.high), str(bar.low), str(bar.close),
                    str(bar.volume), bar.quality.value,
                ]
                for bar in dataset.bars
            ],
        }
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
