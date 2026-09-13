# DEC-025 — Trend Detection via Price Structure

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis

## Context

The first Trend Analyzer implementation used a very strict rule: every successive `PriceBar` had to make both a higher high and a higher low (or both a lower high and a lower low).

That rule is useful for a minimal RED/GREEN slice, but it is too strict to represent normal market movement. A market can remain in an uptrend while retracing between meaningful peaks and troughs.

The project therefore needs a domain definition of trend that is based on **price structure** rather than simply comparing every adjacent candle.

## Research / Evidence

Established technical-analysis references commonly describe trend through peaks and troughs:

- Fidelity describes an uptrend as ascending peaks and troughs (higher highs and higher lows), a downtrend as descending peaks and troughs (lower highs and lower lows), and a sideways trend as prices moving within a horizontal range. It also describes trends as being made up of peaks and troughs.
- Charles Schwab similarly describes uptrends through higher highs and higher lows, downtrends through lower highs and lower lows, and sideways movement through roughly equal highs and lows.

Sources:

- Fidelity, "Basic concepts of trend": https://www.fidelity.com/learning-center/trading-investing/technical-analysis/basic-concepts-trend
- Charles Schwab, "How to Read Stock Charts and Trading Patterns": https://www.schwab.com/learn/story/how-to-read-stock-charts-and-trading-patterns

These sources support the **market-knowledge definition** of trend. They do not mandate the exact swing-point algorithm used by this project.

## Strategy Definition

The project's Trend Analyzer will classify trend from meaningful price swings:

### Uptrend

A sequence of meaningful swing points establishes a pattern of:

- Higher Highs (HH)
- Higher Lows (HL)

### Downtrend

A sequence of meaningful swing points establishes a pattern of:

- Lower Highs (LH)
- Lower Lows (LL)

### Sideways

The available price structure does not establish a sufficiently clear sequence of higher or lower highs and lows.

### Insufficient Data

There are not enough observations to establish the required price structure.

## Swing-Point Detection — Initial Project Rule

For the first implementation, a **3-bar swing** is selected as the smallest deterministic swing-point rule:

### Swing High

A bar is a Swing High when its `high` is strictly greater than the `high` of the immediately preceding bar and the immediately following bar.

### Swing Low

A bar is a Swing Low when its `low` is strictly lower than the `low` of the immediately preceding bar and the immediately following bar.

This is an initial project rule, not a universal definition of a market swing.

## Why 3-Bar Swing

The 3-bar rule provides a useful balance for the first vertical slice:

- It identifies peaks and troughs instead of treating every candle as a structural point.
- It is deterministic and easy to test.
- It introduces no configurable lookback parameter yet.
- It keeps the Trend Analyzer domain-focused without introducing a generic indicator framework.
- It can later be replaced or extended if backtesting shows that another swing definition is more appropriate for EGX data.

## Alternatives Considered

### Adjacent-bar comparison

Require every bar to have a higher/lower high and low than the previous bar.

**Rejected as the primary domain rule.** It is too sensitive to ordinary retracements and does not model meaningful peaks and troughs well.

### Configurable N-bar swing

Require a swing point to exceed/fall below a configurable number of neighboring observations.

**Deferred.** More flexible, but introduces configuration and parameter-selection questions before the first domain behavior has been validated.

### More advanced swing algorithms

Examples include volatility-adjusted swings, percentage thresholds, ATR-based swings, or ZigZag-style filtering.

**Deferred.** These may become useful after backtesting and strategy research, but would be premature for the first vertical slice.

## Trade-offs

The 3-bar rule is simple and explainable, but it has limitations:

- It can identify small local fluctuations as swings.
- It requires a bar after the candidate point, so the most recent bar cannot be confirmed as a swing point until later data arrives.
- It does not adapt to volatility.
- It may behave differently across timeframes and securities.

These limitations are accepted for the initial implementation and must not be hidden as if the rule were universally optimal.

## Important Boundary

Trend detection is **analytical evidence**, not a trading signal.

The Trend Analyzer must not directly decide:

- BUY
- WATCH
- HOLD
- AVOID
- entry price
- stop loss
- target

Those decisions belong to later analysis/scoring/opportunity layers.

## Validation / Backtesting Requirement

The selected 3-bar rule is a project strategy hypothesis, not a claim that it is optimal for EGX stocks.

It should eventually be evaluated against historical EGX data during the backtesting milestone. If evidence shows that the rule is inadequate, this decision should be revisited through a new decision record rather than silently changing the algorithm.

## TDD Consequence

The tests should describe market structure rather than require every adjacent candle to move in the same direction.

The next RED tests should cover at minimum:

1. A sequence containing higher swing highs and higher swing lows → `UPTREND`.
2. A sequence containing lower swing highs and lower swing lows → `DOWNTREND`.
3. A sequence without a clear directional swing structure → `SIDEWAYS`.
4. Insufficient observations → `INSUFFICIENT_DATA`.
5. Deterministic repeated analysis → identical result.

## Decision

Use **price structure based on 3-bar swing highs and swing lows** as the initial Trend Analyzer strategy.

The implementation may evolve after TDD and historical evaluation, but changes to this rule require an explicit documented decision.
