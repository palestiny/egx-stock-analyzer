# M61 — API-independent execution checkpoint — 2026-10-20

## Owner decision

Defer all API/provider-access investigation. Continue engineering with the deterministic test dataset already implemented in the repository, and run the production data-loading/analysis/backtest path for functional verification. Do not block code validation on historical-data credentials.

## What is available now

- `tools/m61_generate_test_dataset.py` creates a deterministic schema-v3 dataset for the fixed ten-symbol cohort, with market-shaped OHLCV rows, point-in-time-shaped financial records, checksums, and explicit synthetic provenance.
- `docs/M61-TEST-DATASET-BOOTSTRAP.md` documents the Windows/PowerShell generation command.
- PR #311 added the synthetic dataset generator and loader checks.
- PR #312 added an end-to-end test that loads the generated package through the production loader and runs `HistoricalDatasetBacktestRunner` twice for COMI, with warm-up/evaluation separation and deterministic-result assertions.
- The last documented main CI run passed the repository's Python tests, frontend checks, dependency audit, and container build (run #37927196545; recorded in `docs/M61-HISTORICAL-DATASET-ACQUISITION-STATUS.md`).

References:
- https://github.com/palestiny/egx-stock-analyzer/pull/311
- https://github.com/palestiny/egx-stock-analyzer/pull/312
- https://github.com/palestiny/egx-stock-analyzer/actions/runs/37927196545

## Execution commands (Windows PowerShell)

From the repository root:

```powershell
python -m tools.m61_generate_test_dataset --output-dir .\artifacts\m61-test-dataset
python -m pytest
```

The generator requires the output directory to be absent or empty. Use a separate empty output path for each fresh run.

## Interpretation rules

This route is for verifying that dataset generation, manifest/checksum validation, loading, analysis, and backtest execution work end to end. Synthetic prices and financial values are formula-generated and are not EGX observations. Weekday dates do not model EGX holidays, suspensions, corporate actions, or actual disclosures.

Therefore:
- Functional pass/fail results may be reported for the software path.
- Synthetic strategy returns, trade counts, win rate, drawdown, or other performance statistics must not be presented as evidence of real-market strategy quality.
- Do not loosen the real-data acceptance gate or relabel synthetic rows as historical data.
- A real-market performance evaluation remains unavailable until actual market history and point-in-time financial evidence are supplied and accepted.

## Current decision

**Proceed with API-independent software verification now.** Historical data acquisition is deferred, not a code-execution prerequisite. Real-market strategy evaluation remains explicitly blocked; this checkpoint does not claim that tests were run by this documentation change.
