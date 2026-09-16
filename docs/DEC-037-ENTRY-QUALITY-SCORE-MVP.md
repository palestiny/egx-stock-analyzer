# DEC-037 — Entry Quality Score MVP

**Status:** Accepted  
**Milestone:** M7 — Opportunity Detection

## Context

Stock Quality describes the underlying stock using fundamental and technical evidence. Entry Quality must answer a different question: how favorable is the current price location for a potential entry?

Entry Quality therefore uses Entry Context, not Stock Quality.

## Decision

The MVP Entry Quality Score evaluates only the relationship between the current price and the nearest structural support/resistance levels.

- Support available + current price at or above support: `+1`
- No support available: `0`
- Resistance available + current price at or below resistance: `+1`
- No resistance available: `0`
- Total range: `0..+2`
- Preserve individual contributions for explainability.

This MVP intentionally measures **context availability and favorable price location**, not expected return or probability of success.

## Explicitly Excluded

- Stock Quality Score
- BUY/SELL decisions
- fixed distance thresholds
- risk/reward calculation
- stop-loss or target calculation
- support/resistance strength
- volume confirmation
- trend confirmation
- configurable weighting
- normalization
- AI

## TDD Acceptance Criteria

1. Support and resistance both available produce `+2`.
2. Support only produces `+1`.
3. Resistance only produces `+1`.
4. Neither level available produces `0`.
5. Result preserves explainable support/resistance contributions.
6. Result is immutable.
7. Repeated scoring is deterministic.
