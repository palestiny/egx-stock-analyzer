# DEC-039 — Backtesting MVP

**Status:** Accepted
**Milestone:** M8 — Backtesting

## Context

The analytical core now produces:

- Stock Quality Score
- Entry Quality Score
- Opportunity Classification: BUY / WATCH / HOLD / AVOID

The next step is to test whether the current classification rules have useful historical behavior.

Backtesting must measure the behavior of the existing analytical strategy without silently changing its rules.

## Decision

The first backtesting MVP will validate the current Opportunity Classification strategy on historical **daily** market data.

The current Opportunity Classification rules are treated as **Strategy v0** for the backtest.

The backtest is initially an **event/outcome evaluator**, not a full trading simulator, because the current strategy does not yet define stop-loss, target, position sizing, or a complete exit policy.

## 1. Strategy Under Test

Strategy v0 consists of the existing pipeline:

```text
Historical Daily Price Data
        ↓
Technical Analysis
        ↓
Fundamental Analysis
        ↓
Scoring
        ↓
Entry Context
        ↓
Entry Quality
        ↓
Opportunity Classification
```

The classification rules remain exactly those documented in `DEC-038`.

No threshold or scoring rule is changed as part of backtesting.

## 2. Signal Timestamp

A signal is generated from information available at the close of a daily bar.

The signal timestamp is the timestamp of that completed bar.

No information from later bars may be used when producing the signal.

## 3. Execution Timing

The MVP does **not** assume execution at the same close that generated the signal.

For a future trading simulation, execution must occur no earlier than the next available trading session/bar after the signal.

This avoids look-ahead caused by treating the closing price used to generate a signal as if it were known before execution.

## 4. Outcome Window

Because no exit strategy exists yet, the MVP evaluates a fixed forward outcome window rather than simulating a complete position lifecycle.

The initial outcome window is a configurable number of subsequent daily bars.

The exact default lookahead period will be defined by the implementation contract and tests; it is not part of the Opportunity Classification rules.

The evaluator records the forward price return over that window.

## 5. Classification Scope

The primary classification under evaluation is **BUY**.

WATCH, HOLD, and AVOID remain observable classifications but are not treated as entries in the MVP.

This keeps the first backtest focused on whether the current BUY classification is associated with measurable subsequent price behavior.

## 6. Costs and Slippage

The first outcome evaluator reports **gross price return** only.

Transaction costs, commissions, taxes, and slippage are explicitly excluded from the first MVP because no actual execution simulator exists yet.

They must be introduced before treating the system as a realistic trading-performance simulator.

## 7. Position Lifecycle

The MVP does not create persistent positions.

Conceptually:

```text
BUY classification
      ↓
Next-session observation
      ↓
Fixed forward outcome window
      ↓
Return measurement
```

A full position lifecycle with entry, holding, exit, stop-loss, target, and position sizing is deferred.

## 8. Metrics

The MVP will support measurements that can be derived from forward outcomes, including:

- number of BUY signals
- positive-outcome count
- negative-outcome count
- win rate
- average forward return
- median forward return
- minimum forward return
- maximum forward return

More advanced trading metrics such as maximum drawdown, profit factor, expectancy after costs, exposure, and position-level performance are deferred until a full trading simulation exists.

## 9. Look-Ahead and Leakage Rules

The backtest must enforce:

- signal calculations use only information available at the signal timestamp
- future price bars cannot affect the signal
- execution cannot occur before the signal is generated
- future fundamentals cannot be used for an earlier signal
- outcome calculation may use future prices only after the signal is fixed

## 10. Reproducibility

A backtest result must be reproducible from:

```text
Historical Data
+
Strategy Version
+
Backtest Configuration
```

The result must not depend on current market data or mutable external state.

## 11. Explicitly Excluded

- Stop-loss rules
- Target rules
- Position sizing
- Portfolio allocation
- Short selling
- Transaction costs
- Slippage simulation
- Intraday execution
- Strategy optimization
- Parameter optimization
- Ranking strategies by performance
- AI-generated strategy changes
- Provider integration
- Detailed Data Quality implementation

These require separate design decisions.

## 12. TDD Acceptance Criteria

The first implementation must prove at least:

1. A signal generated on day N cannot use price data after day N.
2. A BUY signal is evaluated from the next available daily bar, not the signal close.
3. The configured forward outcome window is respected.
4. Future price data affects only outcome measurement, not signal generation.
5. BUY signals produce measurable forward-return outcomes.
6. No BUY signals produces an empty but valid result.
7. Results are deterministic for the same input data and configuration.
8. The evaluator does not create a hidden stop-loss or target rule.
9. Repeated evaluation of the same historical input produces the same result.

## Trade-offs

### Same-close execution vs next-session execution

**Rejected:** same-close execution.

**Reason:** the close is part of the information used to produce the signal. Treating that same close as an executable price introduces look-ahead/execution-timing ambiguity.

**Chosen:** next available daily bar/session.

### Full trading simulator vs outcome evaluator

**Rejected for MVP:** full simulator.

**Reason:** the current strategy does not yet define exits, stop-loss, targets, or position sizing. Building those rules now would introduce new strategy decisions unrelated to validating the current analytical classification.

**Chosen:** fixed forward outcome evaluator.

### Gross vs net return

**Chosen for MVP:** gross return.

**Reason:** execution costs require a later execution model. Adding assumed costs now would mix backtesting design with an unapproved trading-cost model.

## Future Evolution

After the MVP validates the analytical behavior, a later design gate may introduce:

```text
Signal
  ↓
Execution Model
  ↓
Position
  ↓
Exit Rules
  ↓
Costs / Slippage
  ↓
Portfolio Performance
```

That future model must be designed separately rather than being hidden inside the MVP.
