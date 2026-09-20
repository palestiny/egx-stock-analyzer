# DEC-030 — Technical Analysis Evidence Composition

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis

## Decision

Technical Analysis is a composition of independent analytical evidence rather than a single calculation.

The MVP evidence set currently includes:

- Trend Evidence
- Support / Resistance Evidence
- Momentum Evidence
- Volume Evidence

Each analyzer remains responsible for discovering its own evidence. No analyzer decides BUY/SELL, assigns opportunity scores, or combines evidence into a trading decision.

## Result Boundary

A future `TechnicalAnalysisResult` will compose the independent evidence produced by these analyzers together with explicit analysis context such as stock, timeframe, and analysis period.

The result is a container/composition boundary, not a replacement for the individual analyzers.

## Data Sufficiency

Each analytical capability owns its own minimum-data semantics. Insufficient data for one evidence type must not automatically invalidate unrelated evidence types.

For example, Trend may be insufficient while Volume Ratio is available.

## Determinism

Evidence must remain deterministic and reproducible for the same input observations and configuration.

## Out of Scope

This decision does not define:

- Technical-analysis scoring
- BUY/SELL signal generation
- Opportunity Score
- Confidence calculation
- Weighting between evidence types
- Fundamental analysis
- Data-quality validation rules
- Provider-specific behavior

Those concerns require their own design decisions.

## Consequence

M4 can continue by composing the already-defined evidence without prematurely coupling analyzers to scoring or trading decisions.
