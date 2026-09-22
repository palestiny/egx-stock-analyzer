# DEC-126 — M61 Backtesting & Strategy Validation Design Gate

**Status:** Proposed — awaiting owner decision  
**Date:** 2026-09-22  
**Milestone:** M61 — Backtesting & Strategy Validation

## 1. Purpose

M60 completed the production deployment mapping for the existing maintenance capability. The repository was then reviewed against the actual analytical implementation.

The review confirms that the core stock-analysis path already exists:

```
Price Bars + Financial Periods
        ↓
Technical Analysis + Fundamental Analysis
        ↓
Technical / Fundamental Scores
        ↓
Stock Quality
        ↓
Entry Context
        ↓
Entry Quality
        ↓
Opportunity Classification
        ↓
Persisted Analysis Result / Report / Alert Projections
```

Existing implemented analytical slices include technical analysis, structural support/resistance, momentum/volume analysis, fundamental analysis, explainable scoring, stock quality, entry context, entry quality, and opportunity classification.

Therefore M61 should **not rebuild the core analysis pipeline**. The next unresolved analytical boundary is validation of analytical strategies against historical data.

## 2. Problem

The current opportunity classification is deterministic and explainable, but deterministic output is not evidence that the rules are useful historically.

The system needs a controlled way to answer:

- What would a strategy have produced on historical data?
- When exactly was a signal considered known?
- At what price/time would execution be simulated?
- How long was a position held?
- What happened after the signal?
- What costs or slippage assumptions were applied?
- How should results be compared across strategy versions?

Without these semantics, a backtest can produce precise-looking numbers while representing an incorrect simulation.

## 3. M61 Objective

Define and implement a **deterministic, leakage-safe, explainable backtesting boundary** that evaluates a versioned analytical strategy against historical market observations without changing production analysis semantics.

First vertical slice:

```
Historical PriceBars
      ↓
Point-in-time analysis
      ↓
Strategy signal
      ↓
Simulated execution
      ↓
Position lifecycle
      ↓
Trade outcomes
      ↓
Backtest result + explanation
```

## 4. Boundaries to Preserve

M61 preserves:

- modular-monolith architecture;
- domain-first analytical logic;
- deterministic/explainable scoring;
- separation of Stock Quality from Entry Quality;
- external market data as observations;
- data-quality assessment as a separate concern;
- persistence behind application-facing contracts;
- existing analysis/report/alert contracts;
- AI as a replaceable capability, not analytical authority;
- no real trade execution.

Backtesting consumes analytical capabilities rather than duplicating their formulas.

## 5. Explicit Non-Goals

M61 does not introduce:

- real brokerage/trade execution;
- live paper-trading automation;
- portfolio optimization;
- machine-learning training;
- AI-generated trading rules;
- parameter optimization / brute-force strategy search;
- walk-forward optimization;
- Monte Carlo simulation;
- multi-market portfolio backtesting;
- a new persistence platform;
- a second analytical implementation.

## 6. Critical Design Decisions

### D1 — Backtest Execution Model

**Option A — Event-driven bar-by-bar simulation**

Each historical bar advances the simulation clock. Analysis can only consume observations available at that point.

Pros: strongest protection against look-ahead leakage and naturally models signal/execution timing.

Cons: more implementation complexity.

**Recommendation:** Option A.

### D2 — Signal Timing

**Option A — Signal after bar close, execution no earlier than the next bar.**

This prevents using a bar's closing information to claim execution at that same close unless explicitly modeled.

**Option B — Same-bar close execution.**

Simpler but requires stronger assumptions about close execution.

**Recommendation:** Option A.

### D3 — Execution Price

**Option A — Next-bar open.**

Deterministic and directly available from OHLC data, but ignores intrabar mechanics and slippage.

**Option B — Configurable next-bar execution model.**

More flexible but unnecessary for the first slice.

**Recommendation:** Option A for M61, with a future extension point rather than a framework.

### D4 — Position Model

**Option A — Single-position, long-only MVP.**

Pros: understandable lifecycle and enough to validate signal quality.

Cons: no overlapping signals or short positions.

**Recommendation:** Option A.

### D5 — Exit Semantics

The first design must define an explicit exit rule rather than inventing one inside the backtester.

Candidates include:

- stop-loss;
- target;
- time-based exit;
- strategy invalidation.

**Owner decision required:** which exit semantics belong to the first M61 strategy slice.

The backtester must not silently derive stop-loss/target rules from existing support/resistance merely because those values exist.

### D6 — Costs / Slippage

**Option A — Explicit fixed assumptions in backtest configuration.**

Reproducible and visible.

**Option B — Ignore costs in M61.**

Simpler but risks overstating historical results.

**Recommendation:** include explicit transaction-cost and slippage assumptions in the simulation contract, even if first configured values are zero.

### D7 — Historical Data Quality

Backtesting must not silently treat questionable observations as trustworthy.

M61 should integrate the existing data-quality boundary and explicitly define whether a bar is:

- usable;
- excluded;
- or causes the run to fail.

The simulator must not invent its own quality rules.

### D8 — Result Model

The backtest result should preserve at minimum:

- strategy/version identity;
- symbol/timeframe;
- historical period;
- signal timestamp;
- execution timestamp/price;
- entry reason;
- exit timestamp/price;
- exit reason;
- position return;
- cost/slippage impact;
- final outcome;
- sufficient evidence to explain the result.

Aggregate metrics should be derived from individual simulated outcomes.

## 7. Leakage-Safety Invariants

Tests must prove:

1. Future bars cannot affect a signal at time T.
2. A signal from a completed bar cannot execute before the accepted execution boundary.
3. Historical analysis uses production analytical rules rather than a simplified duplicate.
4. Invalid historical observations cannot silently become valid analytical inputs.
5. Identical inputs, strategy version, and configuration produce identical results.
6. Strategy/version/configuration identity is preserved.
7. No real market order is sent.

## 8. First Vertical Slice

```
One symbol
+
Daily PriceBars
+
One explicitly defined strategy
+
One long position
+
Next-bar-open execution
+
Explicit exit rule
+
Explicit cost/slippage configuration
+
Trade-level result
+
Deterministic aggregate summary
```

Prove simulation semantics before adding multiple strategies, portfolios, optimization, or UI.

## 9. Acceptance Criteria

M61 is complete only when:

- the accepted design gate is documented;
- RED tests prove leakage and timing rules;
- GREEN implementation passes the focused suite;
- deterministic rerun behavior is verified;
- trade lifecycle is fully tested;
- cost/slippage treatment is tested;
- invalid-data behavior is tested;
- strategy/version identity is preserved in the backtest result;
- existing production analysis tests remain green;
- review/refactor is complete;
- CI passes;
- roadmap/current-state/decision log are synchronized;
- no real trading capability is introduced.

## 10. Decision Required From Owner

Recommended baseline:

```
Event-driven simulation
        +
Signal after bar close
        +
Next-bar-open execution
        +
Single long-only position
        +
Explicit exit rule
        +
Explicit cost/slippage configuration
        +
Existing data-quality boundary
        +
Trade-level explainable results
```

The unresolved owner decision is primarily the **first strategy exit semantics** and confirmation of the recommended simulation baseline.

No implementation should begin until this design gate is accepted.
