# M8 — Backtesting MVP Completion

**Status:** Complete

## Delivered

- Historical evaluation of the existing Opportunity Classification Strategy v0.
- Signal history is restricted to data available at the signal timestamp.
- BUY execution is evaluated from the next available daily bar.
- Configurable forward outcome window.
- Gross forward return measurement only.
- No hidden stop-loss, target, position sizing, transaction-cost, or slippage logic.
- Deterministic backtest result and MVP metrics:
  - BUY signal count
  - positive outcome count
  - negative outcome count
  - win rate
  - average forward return
  - median forward return
  - minimum forward return
  - maximum forward return

## Verification

The M8 test suite covers the DEC-039 acceptance criteria and the result metrics. Local green verification is supplied by the project workflow; GitHub currently has no configured CI status checks for these commits.

## Explicit Boundary

M8 is an outcome evaluator, not a full trading simulator.

The following remain deferred to a future design gate:

- position lifecycle
- stop-loss and target execution
- transaction costs and slippage
- portfolio allocation
- position sizing
- intraday execution
- optimization
- ranking strategies

## Next Milestone

M11 — Reporting & Alerts.
