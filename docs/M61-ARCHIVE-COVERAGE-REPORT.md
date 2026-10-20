# M61 — Per-symbol archive coverage report

## Purpose

Summarize the private archive's existing `data-quality-audit-YYYY-MM-DD.json` into a compact, sortable JSON report. This lets research prioritize symbols with more structurally valid history without requiring the large compressed archive to be committed to the analyzer repository.

## Run

Copy the desired audit report from `palestiny/egx-market-data-private` into a local path, then run:

~~~powershell
python tools/m61_archive_coverage_report.py --input "G:\path\to\data-quality-audit-2026-10-20.json" --output ".\artifacts\m61-archive-coverage-report.json"
~~~

The tool uses only the Python standard library. It summarizes the audit report's per-symbol row counts, calculates the structurally valid percentage, and sorts symbols by valid-row count descending. It fails on inconsistent row totals rather than silently reconciling them.

## Interpretation boundary

- This tool reads the quality-audit JSON, not the underlying price archive. It does not independently repeat OHLC validation.
- Structurally valid bars are not necessarily accurate, adjusted correctly, licensed for research, or representative of the complete EGX listing universe.
- A higher valid-row count is not a recommendation to buy or trade a symbol.
- It does not infer missing exchange sessions, repair prices, change production ranking, or claim strategy performance.
