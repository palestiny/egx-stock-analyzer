from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.application.analysis.automatic_analysis_retention import AutomaticAnalysisRetentionResult
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.maintenance.automatic_retention_command import (
    AutomaticRetentionCommandResult,
    run_automatic_retention,
)


def test_disabled_retention_is_a_successful_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    calls = []

    class FakeRetention:
        def __init__(self, lifecycle_store, policy):
            calls.append((lifecycle_store, policy))

        def execute(self, identity, *, dry_run=False):
            raise AssertionError("disabled policy must not invoke the capability")

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
    assert result.dry_run is False


def test_enabled_command_delegates_to_m58_capability(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
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
    assert result.dry_run is True
    assert result.purged_lifecycle_units == 0
    assert calls[0][1] == config.automatic_retention_days
    assert calls[0][2] == config.automatic_retention_batch_limit
    identity, received_now, received_dry_run = calls[1]
    assert identity.subject == "operator"
    assert received_now == now
    assert received_dry_run is True


def test_command_contract_exposes_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
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