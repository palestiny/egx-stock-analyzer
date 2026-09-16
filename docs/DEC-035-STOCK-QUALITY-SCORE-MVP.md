# DEC-035 — Stock Quality Score MVP

**Status:** Accepted  
**Milestone:** M6 — Scoring

## Context

Fundamental Score and Technical Score now exist as independent, explainable MVP scores. We need one combined Stock Quality Score without turning it into an entry signal.

## Decision

Stock Quality Score combines the existing Fundamental Score and Technical Score.

- Fundamental Score range: `-3..+3`
- Technical Score range: `-3..+3`
- Stock Quality Score range: `-6..+6`
- `total_score = fundamental_score.total + technical_score.total`
- Preserve both component scores for explainability.
- Equal contribution is used for the MVP.
- The scorer consumes existing score objects, not raw analysis evidence.

## Explicitly Excluded

- Entry Quality scoring
- Support/Resistance scoring
- BUY/SELL decisions
- ranking
- stop-loss or target calculation
- configurable weighting
- 0–100 normalization
- strategy-specific policies
- AI

Support/Resistance remains reserved for Entry Quality.

## TDD Acceptance Criteria

1. Maximum Fundamental + maximum Technical produces `+6`.
2. Minimum Fundamental + minimum Technical produces `-6`.
3. Mixed component scores are summed exactly.
4. Zero component scores produce zero total.
5. The result is immutable.
6. Repeated scoring of the same inputs is deterministic.
7. Both component scores are preserved in the result for explainability.
