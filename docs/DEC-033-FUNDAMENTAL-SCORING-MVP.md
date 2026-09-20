# DEC-033 — Fundamental Scoring MVP

**Status:** Accepted  
**Milestone:** M6 — Scoring Engine

## Decision

The first scoring vertical slice scores **Fundamental Analysis evidence only**.

The scorer converts already-computed fundamental evidence into a deterministic, explainable score. It does not calculate financial ratios and does not make BUY/SELL decisions.

## MVP Scoring Policy

Each available fundamental evidence area contributes equally:

| Evidence | Positive | Neutral | Negative |
|---|---:|---:|---:|
| Profitability | +1 | 0 | -1 |
| Liquidity | +1 | 0 | -1 |
| Revenue Growth | +1 | 0 | -1 |

`UNDEFINED` and `INSUFFICIENT_DATA` contribute `0` points in the MVP.

Therefore the Fundamental Score range is `-3` to `+3`.

This is an MVP policy, not a claim that all fundamental evidence has equal economic importance. Weighting is intentionally deferred until the scoring model has been exercised and the required strategy behavior is clearer.

## Explainability

The score must preserve its component contributions rather than returning only a total. A consumer must be able to see which evidence contributed each point.

## Boundaries

The scorer does not:

- calculate financial metrics
- fetch financial data
- validate provider data
- compare stocks
- generate BUY/SELL signals
- calculate entry quality
- apply technical-analysis scoring
- apply valuation rules
- use AI

## Stock Quality vs Entry Quality

This scoring slice belongs to **Stock Quality**.

It must not be interpreted as an entry signal. Entry Quality remains a separate concern and will be designed independently.

## Extensibility

The MVP intentionally uses explicit status-to-points mapping. No strategy interface, plugin hierarchy, configurable weighting engine, or speculative abstraction is introduced yet.

When real variation requires different weighting or scoring policies, that will be a separate design decision.

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

After this vertical slice is reviewed, decide whether to extend scoring to Technical Analysis or refine the scoring policy based on requirements revealed by the MVP.
