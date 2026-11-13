from app.infrastructure.persistence.sqlite_signal_history_store import (
    SQLiteSignalHistoryStore,
)
from tools.benchmark_lifecycle_projection import benchmark_size


def test_lifecycle_projection_benchmark_seeds_and_measures_disk_database(tmp_path):
    result = benchmark_size(
        20,
        samples=2,
        warmups=0,
        writer_operations=10,
        root=tmp_path,
    )

    assert result["opportunity_identities"] == 20
    assert result["expected_active_published_revisions"] == 18
    assert result["database_bytes"] > 0
    assert result["first_query_ms"] > 0
    assert result["reopened_first_query_ms"] > 0
    assert result["warm"]["p50_ms"] > 0
    assert result["under_concurrent_writer"]["p50_ms"] > 0
    assert any(
        "signal_opportunity_projection" in item
        for item in result["query_plan"]
    )
    assert any(
        "idx_signal_revision_parent" in item
        for item in result["query_plan"]
    )

    reopened = SQLiteSignalHistoryStore(
        tmp_path / "lifecycle-projection-20.sqlite3"
    )
    assert len(reopened.latest_active_published_opportunities()) == 18
