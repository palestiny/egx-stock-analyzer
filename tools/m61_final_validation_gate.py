#!/usr/bin/env python3
"""Check completeness of an M61 final-evaluation evidence package.

This gate deliberately does not judge whether Strategy v0 performed well.
It only determines whether the evidence package is complete enough to report
historical results reproducibly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_FILES = (
    "manifest.json",
    "evaluation.json",
    "reproducibility.json",
)

REQUIRED_SYMBOLS = {
    "COMI", "EGAL", "SWDY", "ETEL", "EAST",
    "TMGH", "PHDC", "FWRY", "EFID", "HRHO",
}


def build_report(root: Path) -> dict:
    report = {"status": "BLOCKED", "checks": {}, "errors": []}

    if not root.is_dir():
        report["errors"].append("Final-evaluation package directory does not exist.")
        return report

    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        report["errors"].append("Missing required files: " + ", ".join(missing))
        return report

    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        evaluation = json.loads((root / "evaluation.json").read_text(encoding="utf-8"))
        reproducibility = json.loads(
            (root / "reproducibility.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        report["errors"].append(f"Invalid evidence JSON: {exc}")
        return report

    report["checks"]["manifest"] = "PASS"
    report["checks"]["evaluation"] = "PASS"
    report["checks"]["reproducibility"] = "PASS"

    if manifest.get("status") != "ACCEPTED":
        report["checks"]["accepted_dataset"] = "FAIL"
        report["errors"].append("Dataset manifest is not marked ACCEPTED.")
    else:
        report["checks"]["accepted_dataset"] = "PASS"

    symbols = set(manifest.get("symbols", []))
    if symbols != REQUIRED_SYMBOLS:
        report["checks"]["cohort"] = "FAIL"
        report["errors"].append("Manifest cohort does not exactly match the bounded M61 cohort.")
    else:
        report["checks"]["cohort"] = "PASS"

    if manifest.get("evaluation_start") != "2021-01-01":
        report["errors"].append("Evaluation start must be 2021-01-01.")
        report["checks"]["evaluation_window"] = "FAIL"
    elif manifest.get("evaluation_end") != "2025-12-31":
        report["errors"].append("Evaluation end must be 2025-12-31.")
        report["checks"]["evaluation_window"] = "FAIL"
    else:
        report["checks"]["evaluation_window"] = "PASS"

    if manifest.get("minimum_warmup_observations") != 252:
        report["checks"]["warmup"] = "FAIL"
        report["errors"].append("Minimum warm-up observations must be 252.")
    else:
        report["checks"]["warmup"] = "PASS"

    if not evaluation.get("strategy_id") or not evaluation.get("strategy_version"):
        report["checks"]["strategy_identity"] = "FAIL"
        report["errors"].append("Evaluation must identify strategy id and version.")
    else:
        report["checks"]["strategy_identity"] = "PASS"

    if not evaluation.get("dataset_version"):
        report["checks"]["evaluation_dataset_link"] = "FAIL"
        report["errors"].append("Evaluation must identify the dataset version.")
    else:
        report["checks"]["evaluation_dataset_link"] = "PASS"

    if reproducibility.get("repeat_run_match") is not True:
        report["checks"]["reproducibility_match"] = "FAIL"
        report["errors"].append("Reproducibility record does not prove identical repeat output.")
    else:
        report["checks"]["reproducibility_match"] = "PASS"

    report["status"] = (
        "PASS"
        if not report["errors"] and all(value == "PASS" for value in report["checks"].values())
        else "BLOCKED"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the M61 final-evaluation evidence package.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    report = build_report(args.package)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
