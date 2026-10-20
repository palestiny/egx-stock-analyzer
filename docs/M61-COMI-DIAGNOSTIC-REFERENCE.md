# M61 — COMI Public-History Diagnostic Reference

This page preserves a stable reference on `main` to the exploratory COMI historical-data diagnostic.

## Primary artifacts

- Diagnostic report and data provenance: https://github.com/palestiny/egx-stock-analyzer/blob/test/m61-public-comi-sample-backtest/docs/M61-PUBLIC-COMI-SAMPLE-DIAGNOSTIC.md
- Pull request containing the fixture, runner, test, and CI integration: https://github.com/palestiny/egx-stock-analyzer/pull/321
- Upstream public price-history file: https://github.com/M-Abdelmegeed/Project-EGX/blob/main/EGX%20Stock%20data/COMI%20Historical%20Data.csv

## Recorded diagnostic result

Initial successful diagnostic execution:

- Symbol: COMI
- Price bars accepted by the runner: 730
- Price data range: 2020-01-02 to 2022-12-29
- Evaluation window: 2022-03-01 to 2022-12-31
- Warm-up bars: 526
- Evaluation bars: 204
- Completed trades: 31 (16 winners, 15 losers)
- Win rate: 51.61%
- Average net trade return: approximately 0.598%
- Compounded net trade return: approximately 18.23%
- Assumed transaction costs: 0.1%; assumed slippage: 0.1%

## Interpretation and limitations

These figures confirm that the existing backtest runner can execute against a public EGX-specific COMI price sample without an API key. They are **exploratory software-diagnostic output only**, not a validated strategy-performance estimate or investment recommendation.

The upstream project's public availability and project license do not independently establish the underlying market-data redistribution rights, completeness, or corporate-action adjustment methodology. The diagnostic uses only FY2020/FY2021 CIB financial snapshots, which remain stale during the 2022 evaluation period. This sample does not meet the M61 ten-symbol/2021–2025 acceptance gate.

The primary artifact currently lives on the open draft PR branch; review PR #321 before relying on it as merged project functionality.
