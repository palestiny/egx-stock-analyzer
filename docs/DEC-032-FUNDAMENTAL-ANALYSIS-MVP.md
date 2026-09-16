# DEC-032 — Fundamental Analysis MVP

**Status:** Accepted  
**Milestone:** M5 — Fundamental Analysis

## Decision

Fundamental Analysis is a composition of independent financial evidence, similar to Technical Analysis.

No single metric decides whether a stock is attractive. Fundamental evidence will be composed first; scoring, BUY/SELL decisions, weighting, and opportunity ranking remain outside M5.

## Fundamental Evidence Areas

The model must remain extensible to consider, where relevant:

- Growth
- Profitability
- Financial health / liquidity
- Leverage / solvency
- Cash flow
- Efficiency / returns
- Valuation
- Industry-specific metrics
- Business/qualitative factors later

These are analytical areas, not a commitment to implement all of them immediately.

## First Vertical Slice

The first implementation will be **Net Profit Margin evidence**.

Formula:

`Net Profit Margin = Net Income / Revenue`

The purpose is to establish the fundamental-analysis pattern with a small deterministic calculation before introducing a larger financial-statement model or many ratios.

## Evidence Shape

Initial evidence will contain:

- status
- net profit margin when calculable

It will be immutable and deterministic.

## Fundamental Analysis Result

`FundamentalAnalysisResult` is an immutable composition object for one stock and one financial period.

It contains:

- `stock_id`
- `period_end`
- independent fundamental evidence, initially `profitability`

The result does not calculate ratios or make trading decisions.

## Fundamental Analysis Orchestration

`FundamentalAnalysisOrchestrator` coordinates the existing analyzers and composes their evidence into `FundamentalAnalysisResult`.

The orchestrator does not implement financial calculations, scoring, BUY/SELL decisions, weighting, or data-quality validation.

As additional fundamental evidence areas are implemented, they can be composed into the result without changing the responsibility of individual analyzers.

## Insufficient / Undefined Data

- Missing required observations → `INSUFFICIENT_DATA` when an analyzer requires them.
- Revenue equal to zero → `UNDEFINED` for Net Profit Margin.
- A zero or negative net income is a valid observation; it is not automatically invalid data.

## Boundaries

The first profitability analyzer does **not**:

- score stocks
- decide BUY/SELL
- compare stocks
- assign confidence
- apply industry thresholds
- validate provider data
- fetch real financial data
- perform valuation
- interpret business quality

The Fundamental Analysis Result and Orchestrator also do **not** add those responsibilities.

## Rationale

Fundamental analysis normally combines multiple areas such as profitability, liquidity, solvency, cash flow, efficiency, and valuation rather than relying on one ratio.

Starting with one deterministic profitability evidence keeps the MVP small while preserving the composition model needed for the broader Fundamental Analysis result.

## Next TDD Step

Add the next independent fundamental evidence capability only after its design gate is defined. Do not add speculative financial metrics or scoring before that.
