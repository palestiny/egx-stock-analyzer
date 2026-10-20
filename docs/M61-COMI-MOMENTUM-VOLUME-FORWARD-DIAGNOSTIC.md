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
