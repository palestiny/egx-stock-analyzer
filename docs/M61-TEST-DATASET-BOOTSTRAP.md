# M61 test dataset bootstrap

## Purpose

Use a reproducible, local dataset to test ingestion, storage, analysis, API, and backtesting plumbing while the real historical-data source is unresolved. This is an explicit test-only path; it does not change the M61 real-data acceptance gate.

## Generate it on Windows / PowerShell

From the repository root:

```powershell
python -m tools.m61_generate_test_dataset --output-dir .\artifacts\m61-test-dataset
```

Optional shorter smoke dataset:

```powershell
python -m tools.m61_generate_test_dataset --output-dir .\artifacts\m61-test-smoke --from-date 2021-01-01 --to-date 2021-12-31
```

The output directory must be absent or empty. The generator writes:
- `market_observations.csv`: synthetic weekday OHLCV for the ten-stock M61 cohort from 2019 through 2025 by default.
- `financial_snapshots.csv`: synthetic annual point-in-time-shaped records for 2018–2025.
- `manifest.json`: schema-v3 manifest, checksums, row counts, coverage, stable development-catalog identity mapping, and explicit synthetic provenance.

## Important limits

- Prices, volumes, and financials are formula-generated. They are **not** actual EGX observations.
- Weekdays are used as a calendar approximation; exchange holidays, suspensions, symbol changes, corporate actions, and real provider semantics are not modeled.
- The generated financial values are placeholders for exercising code paths, not company disclosures.
- Do not use this dataset to assess strategy profitability, calibrate thresholds, make trading decisions, or claim M61 acceptance.
- The loader's integrity and schema checks remain enabled. This bypasses external source acquisition as a test dependency; it does not bypass malformed-row or checksum protection.

The real-data status remains unchanged: source-permission evidence and the real ten-symbol market/financial artifacts are still required before investment research or performance claims.
