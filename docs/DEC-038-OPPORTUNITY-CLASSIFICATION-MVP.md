# DEC-038 — Opportunity Classification MVP

**Status:** Accepted  
**Milestone:** M7 — Opportunity Detection

## Context

The project now has two independent dimensions:

- **Stock Quality:** underlying fundamental + technical quality.
- **Entry Quality:** current price context relative to structural support/resistance.

Opportunity Classification must combine these dimensions into an actionable classification without pretending that the classification is a probability or expected-return estimate.

## Decision

The MVP uses an explicit rule matrix based on Stock Quality and Entry Quality.

### AVOID

`Stock Quality <= -2`

The stock's current underlying quality is sufficiently negative for the MVP classification to avoid treating the current context as an opportunity.

### BUY

`Stock Quality >= +4` **and** `Entry Quality >= +1`

Both underlying quality and at least one favorable structural entry-context component are present.

### WATCH

`Stock Quality >= +2` **and** `Entry Quality == 0`

or

`Stock Quality in {+2, +3}` **and** `Entry Quality >= +1`

The stock has positive quality evidence, but the combination does not satisfy the MVP BUY rule.

### HOLD

All remaining combinations.

This is a classification of the current analytical state, not a guarantee of future price movement.

## Precedence

Rules are evaluated in this order:

```text
AVOID
  ↓
BUY
  ↓
WATCH
  ↓
HOLD
```

The explicit precedence prevents overlapping conditions from producing ambiguous results.

## Input Contract

The classifier consumes:

- `StockQualityScore`
- `EntryQualityScore`

It does not consume raw market data or raw financial data.

## Explicitly Excluded

- Probability of success
- Expected return
- Ranking between stocks
- Position sizing
- Stop-loss calculation
- Target calculation
- Risk/reward calculation
- Backtesting validation
- Configurable thresholds
- Strategy optimization
- AI

The thresholds are intentionally fixed for the MVP and must be changed through a new design decision backed by tests and historical validation.

## TDD Acceptance Criteria

1. Strong stock quality + favorable entry context produces BUY.
2. Strong stock quality + no entry-context contribution produces WATCH.
3. Positive but not strong stock quality + favorable entry context produces WATCH.
4. Positive stock quality + no entry-context contribution produces WATCH.
5. Neutral combinations produce HOLD.
6. Negative stock quality within the HOLD range produces HOLD.
7. Sufficiently negative stock quality produces AVOID regardless of entry context.
8. Result is immutable.
9. Classification is deterministic.
