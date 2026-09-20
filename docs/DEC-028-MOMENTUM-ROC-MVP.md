# DEC-028 — Momentum ROC MVP

**Status:** Accepted
**Milestone:** M4 — Technical Analysis

## Decision

The first Momentum capability will use **Rate of Change (ROC)** as its MVP measure.

```text
ROC = ((Current Close - Previous Close) / Previous Close) × 100
```

The previous close is the close from `lookback` periods before the current observation.

## Analysis Context

The analyzer API is explicitly contextual:

```python
MomentumAnalyzer.analyze(
    stock_id,
    timeframe,
    price_bars,
    lookback,
)
```

`stock_id` and `timeframe` are analysis context, consistent with the existing Trend and Support/Resistance analyzers. The analyzer does not validate that every bar belongs to that context in this MVP.

## Evidence

Momentum produces immutable evidence:

```python
MomentumEvidence(
    status=...,
    rate_of_change=...
)
```

The evidence preserves the calculated ROC value because the raw analytical value may later be used by scoring, explanation, reporting, or further analysis.

## Status Semantics

The MVP uses sign-based interpretation only:

```text
ROC > 0  → POSITIVE
ROC < 0  → NEGATIVE
ROC == 0 → NEUTRAL
```

No arbitrary strength thresholds are introduced at this stage. Thresholds belong to later analytical/scoring decisions if real requirements justify them.

## Insufficient Data

ROC with `lookback = N` requires at least `N + 1` PriceBars.

```text
len(price_bars) < lookback + 1
        ↓
INSUFFICIENT_DATA
```

The analyzer assumes the supplied bars are ordered oldest-to-newest, matching the existing analytical input contract.

## Undefined ROC

`Price` permits zero as a valid value. If the comparison close from `lookback` periods earlier is zero, percentage ROC is mathematically undefined because division by zero is impossible.

This is not treated as insufficient data. The Momentum status therefore includes:

```text
UNDEFINED
```

with no ROC value.

## Why ROC

ROC was selected over a more complex indicator such as RSI for the first slice because it is:

- simple
- deterministic
- mathematically transparent
- easy to test
- independent of strategy-specific thresholds
- sufficient to establish the Momentum evidence boundary

This does not prevent adding RSI or other momentum evidence later.

## Trade-offs

### ROC vs RSI

ROC keeps the first implementation small and exposes a direct price-change measure. RSI introduces smoothing, window semantics, and additional interpretation rules. Those may be justified later but are not required to establish the first Momentum domain capability.

### Sign-based status vs thresholds

Sign-based status avoids arbitrary business rules. The ROC value remains available for later scoring or strength interpretation.

### Explicit lookback vs hidden default

An explicit `lookback` makes the analysis period part of the call contract and avoids embedding an unexplained magic number inside the analyzer.

## Non-Responsibilities

MomentumAnalyzer does not own:

- trading signals
- buy/sell decisions
- scoring weights
- strategy thresholds
- data-provider rules
- data-quality assessment
- chart presentation
- persistence

## TDD Acceptance Criteria

The first RED tests should cover at minimum:

1. positive ROC
2. negative ROC
3. neutral ROC
4. exact ROC value preservation
5. insufficient data
6. zero comparison close → undefined
7. evidence immutability
8. deterministic repeated analysis

The implementation must not add behavior beyond this decision without a new design decision.
