from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import AnalysisResultStore
from app.application.performance.baseline import PerformanceSample, measure


@dataclass(frozen=True)
class _StubResult:
    technical_score: SimpleNamespace
    fundamental_score: SimpleNamespace
    stock_quality: SimpleNamespace
    entry_quality: SimpleNamespace
    opportunity: SimpleNamespace


class _DeterministicStore:
    def __init__(self) -> None:
        self._result = _StubResult(
            technical_score=SimpleNamespace(total_score=70),
            fundamental_score=SimpleNamespace(total=65),
            stock_quality=SimpleNamespace(total_score=68),
            entry_quality=SimpleNamespace(total_score=72),
            opportunity=SimpleNamespace(classification=SimpleNamespace(value="WATCH")),
        )

    def get(self, symbol: str, owner_user_id=None):
        if symbol != "COMI":
            return None
        return self._result

    def get_record(self, symbol: str, owner_user_id=None):
        return None

    def get_snapshot(self, snapshot_id, owner_user_id=None):
        return None

    def get_history_by_analysis_run(self, analysis_run_id, owner_user_id=None):
        return ()

    def get_history(self, symbol: str, start_date=None, end_date=None, owner_user_id=None):
        return ()


def _environment() -> dict[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "repository_commit": commit,
    }


def _sample_payload(sample: PerformanceSample) -> dict[str, object]:
    return {
        "repetitions": sample.repetitions,
        "warmup_runs": sample.warmup_runs,
        "durations_seconds": list(sample.durations_seconds),
        "p50_seconds": sample.p50_seconds,
        "p95_seconds": sample.p95_seconds,
        "p99_seconds": sample.p99_seconds,
        "operations_per_second": sample.operations_per_second,
    }


def main() -> None:
    store: AnalysisResultStore = _DeterministicStore()
    app = create_app(store)
    client = TestClient(app)

    # This workload deliberately excludes provider/network calls. It measures
    # the deterministic API read path: routing, authentication adapter,
    # application read service, response mapping, and JSON serialization.
    response = client.get("/api/v1/analysis/COMI")
    response.raise_for_status()

    sample = measure(
        lambda: client.get("/api/v1/analysis/COMI").raise_for_status(),
        repetitions=10,
        warmup_runs=2,
    )

    payload = {
        "protocol": "PERFORMANCE_BASELINE_PROTOCOL",
        "measured_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").UTC
        ).isoformat(),
        "workload": {
            "id": "api.analysis_read.deterministic",
            "method": "GET",
            "path": "/api/v1/analysis/COMI",
            "external_network": False,
            "provider_calls": False,
            "repetitions": sample.repetitions,
            "warmup_runs": sample.warmup_runs,
        },
        "environment": _environment(),
        "result": _sample_payload(sample),
    }

    output = Path("artifacts/performance/api-analysis-read-baseline.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
