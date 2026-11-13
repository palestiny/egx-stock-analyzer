from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import statistics
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import Event, Thread
from time import perf_counter
from uuid import uuid4

from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.infrastructure.persistence.sqlite_signal_history_store import (
    SQLiteSignalHistoryStore,
)


# Keep this query synchronized with SQLiteSignalHistoryStore.latest_active_published_opportunities.
PROJECTION_SQL = """
SELECT
    latest.signal_id, latest.event, latest.recorded_at, latest.signal_json,
    publication.signal_id, publication.event,
    publication.recorded_at, publication.signal_json
FROM signal_opportunity_projection AS projection
JOIN signal_history AS latest
  ON latest.id = projection.latest_history_id
JOIN signal_history AS publication
  ON publication.id = projection.publication_history_id
WHERE NOT EXISTS (
    SELECT 1 FROM signal_revision_links AS revision
    WHERE revision.parent_signal_id = projection.signal_id
)
ORDER BY projection.signal_id ASC
"""


def _signal(status: SignalStatus, generated_at: datetime) -> Signal:
    return Signal(
        symbol="COMI",
        direction=SignalDirection.BUY,
        status=status,
        generated_at=generated_at,
        timeframe="DAILY",
        entry_zone=PriceZone(lower=Decimal("99"), upper=Decimal("101")),
        invalidation=Decimal("95"),
        targets=(Target(price=Decimal("109"), label="T1"),),
        confidence=Decimal("80"),
        risk_score=Decimal("20"),
        evidence=(SignalEvidence("benchmark", "Synthetic benchmark fixture"),),
        strategy_id="lifecycle-projection-benchmark",
        strategy_version="1.0",
        data_timestamp=generated_at,
    )


def _seed_database(database: Path, opportunity_count: int) -> tuple[list[str], int]:
    SQLiteSignalHistoryStore(database)
    active_ids: list[str] = []
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            for index in range(opportunity_count):
                generated_at = base_time + timedelta(minutes=index)
                is_terminal = index % 10 == 0
                is_revised = not is_terminal and index % 10 == 1
                status = SignalStatus.INVALIDATED if is_terminal else SignalStatus.ACTIVE
                parent_id = uuid4()
                parent = _signal(status, generated_at)
                parent_payload = SQLiteSignalHistoryStore._serialize_signal(parent)
                connection.execute(
                    """
                    INSERT INTO signal_identities(
                        signal_id, symbol, strategy_id, strategy_version, generated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(parent_id), parent.symbol, parent.strategy_id,
                        parent.strategy_version, generated_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                    VALUES (?, 'PUBLISHED', ?, ?)
                    """,
                    (str(parent_id), generated_at.isoformat(), parent_payload),
                )
                if is_terminal:
                    continue
                if not is_revised:
                    active_ids.append(str(parent_id))
                    continue

                child_id = uuid4()
                child = _signal(SignalStatus.ACTIVE, generated_at)
                child_payload = SQLiteSignalHistoryStore._serialize_signal(child)
                child_version = f"1.0#revision-{child_id}"
                connection.execute(
                    """
                    INSERT INTO signal_identities(
                        signal_id, symbol, strategy_id, strategy_version, generated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(child_id), child.symbol, child.strategy_id,
                        child_version, generated_at.isoformat(),
                    ),
                )
                revised_at = (generated_at + timedelta(minutes=1)).isoformat()
                connection.execute(
                    """
                    INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                    VALUES (?, 'PUBLISHED_VERSION', ?, ?)
                    """,
                    (str(child_id), revised_at, child_payload),
                )
                connection.execute(
                    """
                    INSERT INTO signal_revision_links(
                        signal_id, parent_signal_id, revision_number, reason, recorded_at,
                        parent_snapshot_sha256, revised_snapshot_sha256
                    ) VALUES (?, ?, 2, 'benchmark revision', ?, ?, ?)
                    """,
                    (
                        str(child_id), str(parent_id), revised_at,
                        hashlib.sha256(parent_payload.encode("utf-8")).hexdigest(),
                        hashlib.sha256(child_payload.encode("utf-8")).hexdigest(),
                    ),
                )
                active_ids.append(str(child_id))
    finally:
        connection.close()
    return active_ids, len(active_ids)


def _percentiles(samples_ms: list[float]) -> dict[str, float]:
    ordered = sorted(samples_ms)
    if not ordered:
        raise ValueError("at least one timing sample is required")

    def percentile(fraction: float) -> float:
        index = round((len(ordered) - 1) * fraction)
        return round(ordered[index], 3)

    return {
        "min_ms": round(ordered[0], 3),
        "median_ms": round(statistics.median(ordered), 3),
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "max_ms": round(ordered[-1], 3),
    }


def _measure(callable_, count: int) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(count):
        started = perf_counter()
        callable_()
        samples.append((perf_counter() - started) * 1000)
    return _percentiles(samples)


def _query_plan(database: Path) -> list[str]:
    connection = sqlite3.connect(database)
    try:
        return [
            str(row[3])
            for row in connection.execute("EXPLAIN QUERY PLAN " + PROJECTION_SQL)
        ]
    finally:
        connection.close()


def _concurrent_writer(
    database: Path,
    signal_ids: list[str],
    operations: int,
    stop: Event,
    errors: list[str],
) -> None:
    if not signal_ids or operations == 0:
        return
    connection = sqlite3.connect(database, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        for batch_start in range(0, operations, 25):
            if stop.is_set():
                break
            with connection:
                for offset in range(batch_start, min(batch_start + 25, operations)):
                    signal_id = signal_ids[offset % len(signal_ids)]
                    row = connection.execute(
                        """
                        SELECT signal_json FROM signal_history
                        WHERE signal_id = ? ORDER BY id DESC LIMIT 1
                        """,
                        (signal_id,),
                    ).fetchone()
                    if row is None:
                        continue
                    recorded_at = (
                        datetime(2026, 12, 1, tzinfo=timezone.utc)
                        + timedelta(microseconds=offset)
                    ).isoformat()
                    connection.execute(
                        """
                        INSERT INTO signal_history(signal_id, event, recorded_at, signal_json)
                        VALUES (?, ?, ?, ?)
                        """,
                        (signal_id, f"BENCHMARK_TOUCH_{offset}", recorded_at, str(row[0])),
                    )
    except Exception as error:
        errors.append(f"{type(error).__name__}: {error}")
    finally:
        connection.close()


def _measure_projection_stages(database: Path, samples: int) -> dict[str, object]:
    """Separate SQLite fetch cost from JSON/domain-object materialization cost."""
    query_samples: list[float] = []
    materialization_samples: list[float] = []
    row_count = 0
    active_count = 0
    connection = sqlite3.connect(database)
    try:
        for _ in range(samples):
            started = perf_counter()
            rows = connection.execute(PROJECTION_SQL).fetchall()
            query_samples.append((perf_counter() - started) * 1000)
            row_count = len(rows)

            started = perf_counter()
            active_count = 0
            for row in rows:
                latest = SQLiteSignalHistoryStore._to_record(row[:4])
                if latest.signal.status is SignalStatus.ACTIVE:
                    SQLiteSignalHistoryStore._to_record(row[4:8])
                    active_count += 1
            materialization_samples.append((perf_counter() - started) * 1000)
    finally:
        connection.close()
    return {
        "candidate_rows": row_count,
        "active_rows": active_count,
        "sqlite_fetch": _percentiles(query_samples),
        "deserialize_and_filter": _percentiles(materialization_samples),
    }


def benchmark_size(
    opportunity_count: int,
    *,
    samples: int,
    warmups: int,
    writer_operations: int,
    root: Path,
) -> dict[str, object]:
    database = root / f"lifecycle-projection-{opportunity_count}.sqlite3"
    signal_ids, expected_active = _seed_database(database, opportunity_count)
    store = SQLiteSignalHistoryStore(database)

    started = perf_counter()
    first_result = store.latest_active_published_opportunities()
    first_query_ms = (perf_counter() - started) * 1000
    if len(first_result) != expected_active:
        raise AssertionError(
            f"projection returned {len(first_result)} rows; expected {expected_active}"
        )

    for _ in range(warmups):
        store.latest_active_published_opportunities()
    warm = _measure(store.latest_active_published_opportunities, samples)

    stop = Event()
    writer_errors: list[str] = []
    writer = Thread(
        target=_concurrent_writer,
        args=(database, signal_ids, writer_operations, stop, writer_errors),
        daemon=True,
    )
    writer.start()
    try:
        under_write_pressure = _measure(
            store.latest_active_published_opportunities, samples
        )
    finally:
        stop.set()
        writer.join(timeout=60)
    if writer.is_alive():
        raise RuntimeError("benchmark writer did not stop within 60 seconds")
    if writer_errors:
        raise RuntimeError("concurrent writer failed: " + "; ".join(writer_errors))

    # A new store instance approximates process-cold initialization, not an OS page-cache flush.
    reopened = SQLiteSignalHistoryStore(database)
    started = perf_counter()
    reopened_count = len(reopened.latest_active_published_opportunities())
    reopened_first_query_ms = (perf_counter() - started) * 1000
    if reopened_count != expected_active:
        raise AssertionError("projection result changed after database reopen")

    stage_breakdown = _measure_projection_stages(database, samples)
    if stage_breakdown["active_rows"] != expected_active:
        raise AssertionError("stage breakdown active count differs from expected result")

    return {
        "stage_breakdown": stage_breakdown,
        "opportunity_identities": opportunity_count,
        "expected_active_published_revisions": expected_active,
        "database_bytes": database.stat().st_size,
        "first_query_ms": round(first_query_ms, 3),
        "reopened_first_query_ms": round(reopened_first_query_ms, 3),
        "warm": warm,
        "under_concurrent_writer": under_write_pressure,
        "writer_operations_requested": writer_operations,
        "query_plan": _query_plan(database),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Disk-backed benchmark for active published lifecycle opportunity projection."
    )
    parser.add_argument(
        "--sizes", nargs="+", type=int, default=[10000, 50000, 100000],
        help="Synthetic opportunity identity counts (default: 10000 50000 100000).",
    )
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--writer-operations", type=int, default=250)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes):
        parser.error("all sizes must be at least 2 so the writer fixture has an active opportunity")
    if args.samples < 2 or args.warmups < 0 or args.writer_operations < 0:
        parser.error("samples must be >= 2; warmups and writer operations must be >= 0")

    with tempfile.TemporaryDirectory(prefix="egx-lifecycle-benchmark-") as directory:
        root = Path(directory)
        results = [
            benchmark_size(
                size,
                samples=args.samples,
                warmups=args.warmups,
                writer_operations=args.writer_operations,
                root=root,
            )
            for size in args.sizes
        ]
    report = {
        "benchmark": "sqlite-lifecycle-active-published-projection-v1",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
        },
        "methodology": {
            "storage": "temporary on-disk SQLite database",
            "warm_samples": args.samples,
            "warmups": args.warmups,
            "writer_operations_per_size": args.writer_operations,
            "cold_start_note": (
                "first query on a new store instance; the operating-system page cache "
                "is not flushed and this is not a physical cold-disk measurement"
            ),
            "percentile_method": "nearest-rank approximation using round((n-1)*p)",
        },
        "results": results,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
