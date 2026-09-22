# DEC-127 — M61 Historical Point-in-Time Input Design Gate

**Status:** Proposed  
**Date:** 2026-09-22  
**Milestone:** M61 — Backtesting & Strategy Validation

## 1. Purpose

The first M61 simulator slice is implemented and CI-verified. The next step is historical strategy evaluation.

Repository review found a critical boundary that must be resolved before running Strategy v0 on real historical observations: the production analysis contract requires both historical price bars and financial periods, while the current Yahoo Finance fundamental source reconstructs annual periods from the provider's current financial statements.

A backtest must not treat a currently retrieved financial statement as if it were necessarily known to the market at an earlier historical decision date.

This gate therefore defines the historical-input boundary before aggregate backtest results are produced.

## 2. Problem

Strategy v0 delegates to the production Opportunity Classification result. That production result depends on:

- technical analysis over price bars;
- fundamental analysis over current and previous financial periods;
- scoring;
- stock quality;
- entry context and quality;
- opportunity classification.

The current `AnalysisInputAssembler` accepts an `as_of` date, but its Yahoo Finance fundamental source selects annual periods by period-end date. This does not establish that the values were publicly available at that historical decision time.

Therefore a naive loop such as:

```
for each historical bar:
    analyze(historical_price_bars, current_yahoo_financial_periods)
```

could introduce look-ahead information through fundamentals even when the price-bar simulation itself is leakage-safe.

## 3. Decision Required

Before historical Strategy v0 evaluation, choose and document a point-in-time financial-input strategy.

### Option A — Historical Fundamental Snapshot Dataset

Create a provider-neutral historical financial snapshot boundary containing only financial facts that were considered available as of an explicit effective/available date.

**Advantages**
- strongest point-in-time semantics;
- explicit auditability;
- reusable for future backtests;
- separates provider retrieval from historical availability.

**Trade-offs**
- requires a historical dataset/source that contains availability dates;
- additional data acquisition/storage work;
- initial coverage may be limited.

### Option B — Price-Only Strategy Validation Slice

Temporarily validate a strategy that depends only on price/volume observations, while keeping Strategy v0's fundamental dependency out of the historical claim.

**Advantages**
- immediately testable with existing historical market observations;
- avoids fabricating historical fundamentals;
- keeps leakage boundary explicit.

**Trade-offs**
- does not validate the existing Strategy v0 end-to-end;
- requires a separately versioned price-only strategy;
- cannot be presented as validation of the current Opportunity Classification strategy.

### Option C — Period-End Proxy

Use the latest financial period whose period-end is no later than the decision date.

**Advantages**
- minimal implementation effort;
- uses existing financial model.

**Trade-offs**
- period-end is not the same as public availability;
- can contain future information relative to the historical decision date;
- unsuitable as evidence for a leakage-safe end-to-end Strategy v0 backtest.

**Recommendation:** do not accept Option C for strategy-performance claims. Prefer Option A for end-to-end Strategy v0 validation. Option B may be used as a separate diagnostic experiment if explicitly versioned and documented.

## 4. Proposed Historical Input Contract

A historical analysis input should be bound to a decision timestamp and contain:

```
HistoricalAnalysisInput
    stock
    decision_timestamp
    eligible_price_bars
    available_financial_periods
    analysis configuration/version
```

For financial data, eligibility should be based on an explicit availability/effective timestamp, not only `period_end`.

A fact must not be visible to analysis at decision time T unless its availability boundary is <= T.

The backtester remains responsible for event timing; the historical input boundary is responsible for point-in-time data eligibility.

## 5. Data-Quality Boundary

The historical adapter must reuse the existing raw-observation → quality assessment → PriceBar boundary.

It must not silently convert invalid observations into valid bars.

For financial inputs, unavailable or non-point-in-time data must be excluded from the historical decision context rather than substituted with current values.

If the required historical inputs cannot be assembled for a decision point, the system must produce an explicit unavailable/blocked outcome rather than silently weakening the strategy input.

## 6. Strategy Identity

Strategy v0 remains:

- ID: `opportunity-classification`
- Version: `0`

No Strategy v0 thresholds or classification formulas are changed by this gate.

A price-only diagnostic strategy, if used, must receive a distinct strategy identity/version and must not be represented as Strategy v0.

## 7. Non-Goals

This gate does not authorize:

- parameter optimization;
- strategy threshold tuning;
- SL/TP invention;
- portfolio optimization;
- ML/AI-generated strategy rules;
- live trading;
- changing Opportunity Classification semantics;
- treating current financial statements as historical truth.

## 8. Acceptance Criteria

This gate should be accepted only when:

- the historical financial-input boundary is explicitly chosen;
- availability semantics are documented;
- the adapter contract is testable;
- future financial facts cannot enter an earlier decision point;
- missing/unavailable historical inputs are explicit;
- Strategy v0 remains delegated to the production analysis path;
- aggregate backtest metrics are only calculated after the historical-input boundary is satisfied.

## 9. Consequence

Until this gate is accepted and implemented, M61's deterministic simulator is verified as a simulation mechanism, but no historical Strategy v0 performance conclusion should be drawn from it.

## 10. Implementation Authorization

No production historical backtest integration is authorized by this proposed gate.

After acceptance, implementation should follow:

```
TDD RED
  ↓
Historical input adapter
  ↓
Point-in-time eligibility tests
  ↓
Strategy v0 historical integration
  ↓
Aggregate metrics
  ↓
Determinism + leakage verification
  ↓
Review / CI
```
