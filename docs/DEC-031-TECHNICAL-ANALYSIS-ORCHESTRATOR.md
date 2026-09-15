# DEC-031 — Technical Analysis Orchestrator

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis

## Decision

Introduce a small application/domain service boundary that orchestrates the existing technical analyzers and composes their independent evidence into `TechnicalAnalysisResult`.

The orchestrator will call:

- `TrendAnalyzer`
- `SupportResistanceAnalyzer`
- `MomentumAnalyzer`
- `VolumeAnalyzer`

It does not implement indicator calculations itself.

## Configuration

Momentum and Volume require an explicit `lookback`. The orchestrator receives these as separate configuration values rather than assuming that both capabilities must use the same period.

## Responsibility

The orchestrator is responsible for:

1. receiving the stock/timeframe context and ordered price bars;
2. invoking each analyzer;
3. passing the explicit lookback to Momentum and Volume;
4. composing the returned evidence into `TechnicalAnalysisResult`.

## Non-Responsibilities

The orchestrator does not:

- validate market-data quality;
- sort or repair observations;
- calculate indicators itself;
- decide BUY/SELL;
- calculate Opportunity Score;
- assign confidence or weights;
- interpret the combined evidence.

## Data Sufficiency

Each analyzer retains ownership of its own insufficient-data semantics. The orchestrator must preserve those independent evidence states rather than rejecting the complete result because one analyzer lacks sufficient history.

## Determinism

For the same observations and configuration, the orchestrator must return the same technical-analysis evidence.

## Consequence

M4 now has a complete composition path from the individual technical analyzers into a single immutable technical-analysis result, while keeping scoring and trading decisions outside the technical-analysis boundary.
