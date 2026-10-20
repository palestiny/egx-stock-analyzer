# COMI momentum and volume forward-signal diagnostic

## Purpose

Measure whether the existing production technical-analysis components identify
COMI sessions that are followed by positive price movement. This is a functional
research diagnostic, not a new buy strategy and not an accepted M61 dataset.

The command is:

```powershell
python -m tools.m61_public_comi_signal_diagnostic
python -m pytest tests/m61/test_public_comi_signal_diagnostic.py -q
```

The GitHub Actions unit-test job runs the command and prints its JSON report.

## Signal groups

- `all_eligible_sessions`: every eligible evaluation session; comparison baseline.
- `positive_momentum`: the existing production MomentumAnalyzer reports positive
  five-session rate of change.
- `positive_momentum_and_volume_at_least_1_5x`: positive momentum and current
  session volume at least 1.5 times the average volume of the preceding five
  sessions. The current session is excluded from that average.
- `strategy_buy`: the existing StockAnalysisPipeline classifies the opportunity
  as BUY using the available point-in-time fundamentals and technical inputs.

## Forward-return calculation

For a signal on session t, the assumed entry is the next session's open. The
return is measured from that entry to the close of session t+h for horizons
h = 1, 3, 5, and 10 sessions. Signals without a complete horizon are omitted
from that horizon's statistics. The report includes sample count, mean and
median return, win rate, best return, and worst return.

This entry assumption avoids pretending that a signal computed from a completed
daily bar can be executed at that same close. It is still a simplified price
return: it excludes transaction costs, slippage, portfolio constraints, and
risk adjustment.

## Interpretation constraints

- Only one symbol (COMI) and a limited historical window are covered.
- The public price source's market-data redistribution rights and corporate
  action adjustment semantics are not independently verified.
- Signals can overlap, so observations are not independent.
- The BUY group is the existing rule-based classifier, not an AI prediction.
- Results do not establish causality, future profitability, or an investment
  recommendation. Any promising result must be replicated across more symbols
  and time periods, with stricter data-quality and cost controls.
- This diagnostic does not satisfy the M61 ten-symbol/2021–2025 acceptance gate.


## Observed CI run

The diagnostic was executed successfully in GitHub Actions run
[39406651020](https://github.com/palestiny/egx-stock-analyzer/actions/runs/39406651020)
on 2026-10-20. The following figures are from that run. Mean returns are
arithmetic averages of the forward price returns, shown as percentages; win rate
is the share of samples with a strictly positive return.

| Signal group | Horizon | Samples | Mean return | Win rate |
|---|---:|---:|---:|---:|
| All eligible sessions | 1 session | 203 | 0.06% | 46.3% |
| All eligible sessions | 3 sessions | 201 | 0.40% | 50.7% |
| All eligible sessions | 5 sessions | 199 | 0.84% | 54.3% |
| All eligible sessions | 10 sessions | 194 | 2.16% | 50.5% |
| Positive momentum | 1 session | 109 | 0.25% | 51.4% |
| Positive momentum | 3 sessions | 108 | 0.85% | 50.9% |
| Positive momentum | 5 sessions | 108 | 1.63% | 58.3% |
| Positive momentum | 10 sessions | 108 | 3.61% | 58.3% |
| Positive momentum + volume >= 1.5x | 1 session | 20 | 0.49% | 45.0% |
| Positive momentum + volume >= 1.5x | 3 sessions | 20 | 2.28% | 70.0% |
| Positive momentum + volume >= 1.5x | 5 sessions | 20 | 2.82% | 75.0% |
| Positive momentum + volume >= 1.5x | 10 sessions | 20 | 4.99% | 70.0% |
| Existing strategy BUY | 1 session | 51 | 0.37% | 52.9% |
| Existing strategy BUY | 3 sessions | 51 | 0.83% | 52.9% |
| Existing strategy BUY | 5 sessions | 51 | 0.86% | 52.9% |
| Existing strategy BUY | 10 sessions | 51 | 3.02% | 54.9% |

### What this suggests—and does not prove

In this COMI sample, the combined momentum-plus-volume group had higher average
forward returns at 3, 5, and 10 sessions than either the all-session baseline
or the positive-momentum-only group. However, it contains only 20 observations;
its one-session win rate was just 45%, and the observations overlap. This is a
promising hypothesis to test, not a validated trading edge. These figures are
gross forward price returns, not strategy portfolio returns, and they do not
include costs, drawdown-based selection, or risk adjustment.

The existing `strategy_buy` group did not outperform the combined momentum and
volume group in this sample. That is a reason to investigate the current
classification logic, not to change its thresholds based on one symbol.

### Next validation gates

1. Test the same signal definitions on additional symbols and disjoint periods.
2. Include transaction costs, slippage, liquidity constraints, and maximum
   adverse/favorable excursion or equivalent risk metrics.
3. Compare against simple baselines and use a time-ordered holdout period.
4. Inspect signal timestamps and ensure each feature uses only data available
   at the decision time.
5. Keep news/disclosure signals separate until timestamped historical news can
   be tested without look-ahead bias.
