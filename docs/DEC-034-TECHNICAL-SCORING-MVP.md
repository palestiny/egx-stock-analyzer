# DEC-034 — Technical Scoring MVP

**Status:** Accepted  
**Milestone:** M6 — Scoring Engine

## Decision

The second scoring vertical slice scores **Technical Analysis evidence only**.

The scorer converts already-computed technical evidence into a deterministic, explainable score. It does not calculate indicators and does not make BUY/SELL decisions.

## MVP Scoring Policy

Each selected technical evidence area contributes equally:

| Evidence | Positive | Neutral | Negative |
|---|---:|---:|---:|
| Trend | +1 | 0 | -1 |
| Momentum | +1 | 0 | -1 |
| Volume | +1 | 0 | -1 |

### Trend

- `UPTREND` → +1
- `SIDEWAYS` → 0
- `DOWNTREND` → -1
- `INSUFFICIENT_DATA` → 0

### Momentum

- `POSITIVE` → +1
- `NEUTRAL` → 0
- `NEGATIVE` → -1
- `INSUFFICIENT_DATA` → 0
- `UNDEFINED` → 0

### Volume

- `ABOVE_AVERAGE` → +1
- `EQUAL_TO_AVERAGE` → 0
- `BELOW_AVERAGE` → -1
- `INSUFFICIENT_DATA` → 0
- `UNDEFINED` → 0

Therefore the Technical Score range is `-3` to `+3`.

## Support / Resistance Boundary

Support and Resistance are intentionally **not included** in the MVP Technical Score.

They will be used later as evidence for **Entry Quality**, because structural price levels are primarily relevant to entry timing and price location rather than the general quality of the stock.

This preserves the project distinction:

**Stock Quality ≠ Entry Quality**

## Explainability

The score must preserve the individual contributions so a consumer can see how Trend, Momentum, and Volume produced the total.

## Boundaries

The scorer does not:
- calculate technical indicators
- fetch market data
- validate provider data
- calculate Support / Resistance
- generate BUY/SELL signals
- calculate Entry Quality
- apply configurable weighting
- normalize to 0–100
- use AI

## Extensibility

The MVP intentionally uses explicit status-to-points mapping. No strategy interface, plugin hierarchy, configurable weighting engine, or speculative abstraction is introduced.

Different scoring policies or weighting will be a separate design decision when real requirements justify them.

## TDD Slice

The first implementation must verify:
1. all-positive evidence produces `+3`;
2. all-neutral evidence produces `0`;
3. all-negative evidence produces `-3`;
4. undefined/insufficient evidence contributes zero;
5. contributions remain explainable;
6. the score is immutable;
7. repeated scoring is deterministic.

## Next Step

Create RED tests for `TechnicalScorer`, then implement the smallest code that makes them pass. After implementation, review the scoring boundary before extending M6 further.
