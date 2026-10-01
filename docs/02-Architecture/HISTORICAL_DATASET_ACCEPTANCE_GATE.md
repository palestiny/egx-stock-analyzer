# Historical Dataset Acceptance Gate

## Purpose

A historical dataset may be used for strategy evaluation only after it passes both integrity validation and acceptance validation.

## Required evidence

The acceptance gate requires:

- valid manifest and artifact checksums;
- deterministic artifact ordering and coverage;
- timezone-aware market timestamps and acquisition metadata;
- valid OHLCV relationships and non-negative volume;
- point-in-time financial availability (available_at >= period_end);
- stable symbol mappings;
- explicit corporate-action convention;
- explicit missing-data and exclusion notes;
- licensing/usage notes;
- transformation manifest;
- retained raw-source evidence with a dataset-root-relative reference and matching SHA-256.

## Backtest rule

HistoricalDatasetAcceptanceValidator is the infrastructure boundary for deciding whether a dataset is sufficiently evidenced for strategy evaluation. Passing this gate does **not** establish that a strategy is profitable or predictive; it establishes that the tested historical input is sufficiently integrity-checked and reproducible for the next validation stage.

Synthetic fixtures are valid for automated contract tests, but they are not evidence that an external market-data provider is licensed, complete, or suitable for production research.

## Current status

The acceptance gate and fixture tests are implemented on the remediation branch. No external historical dataset has been declared accepted by this change.
