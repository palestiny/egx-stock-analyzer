# M61 — Public multi-symbol technical diagnostic results

**Observed run:** [GitHub Actions run 39454016865](https://github.com/palestiny/egx-stock-analyzer/actions/runs/39454016865)  
**Date recorded:** 2026-10-20  
**Status:** exploratory; not accepted M61 evidence

## Dataset actually retrieved

- Symbols: COMI, EGAL, ABUK, TMGH, EAST, FWRY, ETEL, EFIH, HRHO, ADIB (10 symbols).
- Shared date window: 2021-10-25 through 2026-10-19.
- The latest run reported no source-fetch failures and produced a private CI artifact named m61-multi-symbol-diagnostic.
- Source: public static Mubasher historical CSVs, referenced through AhmedYasserShalaby/egx-research-toolkit. The underlying data rights, corporate-action treatment, and completeness are not independently verified.
- A 20% close-to-close or overnight-gap discontinuity audit flagged 16 observations across the ten symbols. These are manual-review flags, not proof of bad data; raw values were not changed.

## Pooled forward-return comparison

Signal is computed after the session close. Entry is the next observed session's open. Exit is the close after 1, 3, 5, or 10 observed sessions. Returns are gross price returns.

| Signal group | Horizon | Samples | Mean return | Win rate |
|---|---:|---:|---:|---:|
| All eligible sessions (baseline) | 1 | 9,607 | -0.15% | 41.48% |
| All eligible sessions (baseline) | 3 | 9,587 | +0.26% | 47.63% |
| All eligible sessions (baseline) | 5 | 9,567 | +0.67% | 50.50% |
| All eligible sessions (baseline) | 10 | 9,517 | +1.75% | 53.58% |
| Positive 5-session momentum | 1 | 5,068 | -0.11% | 41.52% |
| Positive 5-session momentum | 3 | 5,065 | +0.31% | 47.09% |
| Positive 5-session momentum | 5 | 5,063 | +0.78% | 50.98% |
| Positive 5-session momentum | 10 | 5,040 | +1.83% | 54.56% |
| Momentum + volume at least 1.5x prior 5-session average | 1 | 1,245 | -0.16% | 39.44% |
| Momentum + volume at least 1.5x prior 5-session average | 3 | 1,244 | +0.36% | 44.77% |
| Momentum + volume at least 1.5x prior 5-session average | 5 | 1,244 | +0.65% | 49.20% |
| Momentum + volume at least 1.5x prior 5-session average | 10 | 1,235 | +1.85% | 53.12% |
| Pre-breakout proxy near prior 20-session resistance | 1 | 541 | -0.01% | 40.30% |
| Pre-breakout proxy near prior 20-session resistance | 3 | 541 | +0.52% | 44.73% |
| Pre-breakout proxy near prior 20-session resistance | 5 | 541 | +0.62% | 48.43% |
| Pre-breakout proxy near prior 20-session resistance | 10 | 536 | +1.63% | 53.17% |

## What the result supports

- The pre-breakout proxy did **not** outperform the all-session baseline on mean return at 5 or 10 sessions in this run.
- Positive 5-session momentum was slightly higher than baseline on mean gross return at 5 and 10 sessions, but this comparison is not risk-adjusted and does not control for selection, overlapping observations, or multiple testing.
- Momentum + volume was not consistently better: its 5-session mean was below baseline, while its 10-session mean was only marginally higher.
- Extreme worst observed forward returns (down to approximately -53.4% in the pooled sample) make corporate-action and source-gap reconciliation a priority before interpreting the averages.

## Decision

Use these results to prioritize **data quality and robust validation features**, not to alter production ranking weights. Keep the current opportunity ranking unchanged until the proxy is evaluated with reconciled corporate actions, costs/slippage, liquidity constraints, a time-ordered holdout, and per-symbol results. The public diagnostic is not the production nearest-swing-resistance algorithm and is not a trading recommendation.

The private archive's 181,203 structurally valid rows across 195 symbols remain another available research input, but its workflow could not execute in the private repository environment at the time of this run. Its results must not be inferred from the ten-symbol Mubasher run above.
