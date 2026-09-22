# DEC-126 — M61 Backtesting & Strategy Validation Design Gate

**Status:** Accepted — implementation authorized  
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

## 6. Accepted Design Decisions

### D1 — Backtest Execution Model

**Accepted: event-driven bar-by-bar simulation.**

Each historical bar advances the simulation clock. Analysis can only consume observations available at that point.

This provides the strongest boundary against look-ahead leakage while naturally modeling signal/execution timing.

### D2 — Signal Timing

**Accepted: signal is known only after the source bar closes.**

Execution may not occur before the next accepted execution boundary.

This prevents using a bar's closing information to claim execution at that same close.

### D3 — Execution Price

**Accepted: next-bar open for the MVP.**

The first slice uses the next bar's open as the deterministic execution price. Intrabar execution models are deferred.

### D4 — Position Model

**Accepted: single-position, long-only MVP.**

No overlapping positions and no short positions are introduced in M61.

### D5 — Exit Semantics

**Accepted first-strategy semantics:**

1. **Strategy Invalidation is the primary exit.**
   The open position is closed when the same production strategy no longer satisfies its accepted validity condition. The invalidation decision must be based only on observations available at the decision bar close.
2. **Time-based Exit is the safety boundary.**
   The strategy configuration must provide an explicit maximum holding period in bars. When that limit is reached, the position is closed at the next accepted execution boundary.
3. **Stop-loss and take-profit are deferred.**
   M61 must not invent SL/TP levels from support/resistance or other analytical values. They require a separate strategy decision.

The backtester owns lifecycle mechanics; the strategy owns the validity decision. For Strategy v0, strategy validity is defined as the existing production Opportunity Classification remaining `BUY`; the adapter delegates to the production analysis result and does not duplicate classification thresholds.

### D6 — Costs / Slippage

**Accepted: explicit transaction-cost and slippage configuration.**

The simulation contract always carries these assumptions, even when the first configured values are zero. Results must preserve their applied cost/slippage values and impact.

### D7 — Historical Data Quality

**Accepted: reuse the existing data-quality boundary.**

The simulator must not invent a second quality policy. Each input bar must be classified by the existing quality boundary as usable, excluded, or run-blocking according to the established contract.

### D8 — Result Model

The backtest result must preserve at minimum:

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

Aggregate metrics are derived from individual simulated outcomes.

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
Strategy invalidation primary exit
+
Configured maximum-holding-period safety exit
+
Explicit cost/slippage configuration
+
Trade-level result
+
Deterministic aggregate summary
```

The maximum holding period is a required strategy configuration for the backtest slice; it is not a universal market rule. M61 must not silently choose a business/trading value when the strategy configuration does not provide one.

Prove simulation semantics before adding multiple strategies, portfolios, optimization, or UI. The M61 application boundary binds the simulator to Strategy v0 through an adapter around the existing `StockAnalysisPipeline` result rather than reimplementing opportunity-classification rules.

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

## 10. Implementation Authorization

The owner has accepted the recommended simulation baseline and the first strategy exit semantics:

```
Event-driven simulation
        +
Signal after bar close
        +
Next-bar-open execution
        +
Single long-only position
        +
Strategy invalidation primary exit
        +
Configured maximum-holding-period safety exit
        +
Explicit cost/slippage configuration
        +
Existing data-quality boundary
        +
Trade-level explainable results
```

M61 implementation is authorized within this boundary.

Any new strategy rule, SL/TP semantics, portfolio behavior, optimization, live execution, or material architectural expansion requires a new design decision rather than being inferred inside the implementation.
