from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.analysis.automatic_analysis_retention import AutomaticAnalysisRetentionResult
from app.application.analysis.purge_analysis_lifecycle import PurgeAnalysisLifecycleResult
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.maintenance.automatic_retention_command import (
    AutomaticRetentionCommandResult,
    run_automatic_retention,
)


@pytest.fixture
def isolated_lifecycle_store(monkeypatch: pytest.MonkeyPatch):
    """Keep command-contract tests independent from SQLite schema initialization."""
    monkeypatch.setattr(
        "app.infrastructure.maintenance.automatic_retention_command.SQLiteAnalysisLifecycleStore",
        lambda _path: object(),
    )


def test_disabled_retention_is_a_successful_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_lifecycle_store):
    calls = []

    class FakeRetention:
        def __init__(self, lifecycle_store, policy):
            calls.append((lifecycle_store, policy))

    monkeypatch.setattr(
        "app.infrastructure.maintenance.automatic_retention_command.AutomaticAnalysisRetention",
        FakeRetention,
    )
    config = InfrastructureConfig(
        analysis_database_path=str(tmp_path / "analysis.db"),
        automatic_retention_enabled=False,
    )

    result = run_automatic_retention(config)

    assert isinstance(result, AutomaticRetentionCommandResult)
    assert result.status == "disabled"
    assert result.exit_code == 0
    assert result.dry_run is False
    assert calls == []

def test_enabled_command_delegates_to_m58_capability(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_lifecycle_store):
    calls = []
    now = datetime(2026, 9, 21, tzinfo=timezone.utc)

    class FakeRetention:
        def __init__(self, lifecycle_store, policy):
            calls.append((lifecycle_store, policy))

        def execute(self, identity, *, now=None, dry_run=False):
            calls.append((identity, now, dry_run))
            return AutomaticAnalysisRetentionResult(
                enabled=True,
                cutoff=now,
                purge=None,
            )

    monkeypatch.setattr(
        "app.infrastructure.maintenance.automatic_retention_command.AutomaticAnalysisRetention",
        FakeRetention,
    )
    config = InfrastructureConfig(
        analysis_database_path=str(tmp_path / "analysis.db"),
        automatic_retention_enabled=True,
        automatic_retention_days=30,
        automatic_retention_batch_limit=25,
    )

    result = run_automatic_retention(config, dry_run=True, now=now)

    assert result.status == "completed"
    assert result.exit_code == 0
    assert result.dry_run is True
    assert result.purged_lifecycle_units == 0
    assert calls[0][1].preservation_days == config.automatic_retention_days
    assert calls[0][1].batch_limit == config.automatic_retention_batch_limit
    identity, received_now, received_dry_run = calls[1]
    assert identity.subject == "operator"
    assert received_now == now
    assert received_dry_run is True


def test_failed_purge_is_reported_as_failed_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_lifecycle_store):
    class FakeRetention:
        def __init__(self, lifecycle_store, policy):
            pass

        def execute(self, identity, *, now=None, dry_run=False):
            return AutomaticAnalysisRetentionResult(
                enabled=True,
                cutoff=now,
                purge=PurgeAnalysisLifecycleResult(
                    operation_id=uuid4(),
                    dry_run=False,
                    purged_run_ids=(),
                    purged_snapshot_ids=(),
                    failure_resource_id=uuid4(),
                    failure_reason="OperationalError",
                ),
            )

    monkeypatch.setattr(
        "app.infrastructure.maintenance.automatic_retention_command.AutomaticAnalysisRetention",
        FakeRetention,
    )
    config = InfrastructureConfig(
        analysis_database_path=str(tmp_path / "analysis.db"),
        automatic_retention_enabled=True,
    )

    result = run_automatic_retention(config)

    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.purge.failure_reason == "OperationalError"


def test_command_contract_exposes_unexpected_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_lifecycle_store):
    class FakeRetention:
        def __init__(self, lifecycle_store, policy):
            pass

        def execute(self, identity, *, now=None, dry_run=False):
            raise RuntimeError("maintenance failure")

    monkeypatch.setattr(
        "app.infrastructure.maintenance.automatic_retention_command.AutomaticAnalysisRetention",
        FakeRetention,
    )
    config = InfrastructureConfig(
        analysis_database_path=str(tmp_path / "analysis.db"),
        automatic_retention_enabled=True,
    )

    with pytest.raises(RuntimeError, match="maintenance failure"):
        run_automatic_retention(config)

def test_invalid_retention_configuration_fails_before_maintenance(
    tmp_path: Path,
    isolated_lifecycle_store,
):
    config = InfrastructureConfig(
        analysis_database_path=str(tmp_path / "analysis.db"),
        automatic_retention_enabled=True,
        automatic_retention_days=0,
    )

    with pytest.raises(ValueError, match="(?i)preservation.*positive"):
        run_automatic_retention(config)


def test_repeated_invocation_reuses_the_same_command_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    isolated_lifecycle_store,
):
    calls = []

    class FakeRetention:
        def __init__(self, lifecycle_store, policy):
            pass

        def execute(self, identity, *, now=None, dry_run=False):
            calls.append((identity.subject, now, dry_run))
            return AutomaticAnalysisRetentionResult(
                enabled=True,
                cutoff=now,
                purge=None,
            )

    monkeypatch.setattr(
        "app.infrastructure.maintenance.automatic_retention_command.AutomaticAnalysisRetention",
        FakeRetention,
    )
    config = InfrastructureConfig(
        analysis_database_path=str(tmp_path / "analysis.db"),
        automatic_retention_enabled=True,
    )

    first = run_automatic_retention(config)
    second = run_automatic_retention(config)

    assert first.status == "completed"
    assert second.status == "completed"
    assert len(calls) == 2
