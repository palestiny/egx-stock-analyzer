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

## Insufficient / Undefined Data

- Missing required observations → `INSUFFICIENT_DATA`.
- Revenue equal to zero → `UNDEFINED`.
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

## Rationale

Financial analysis commonly considers profitability, liquidity, solvency, efficiency, cash flow, and valuation together rather than relying on one ratio. citeturn0search1turn0search0

Starting with one deterministic profitability evidence keeps the MVP small while preserving the composition model needed for the broader Fundamental Analysis result.

## Next TDD Step

Create RED tests for the smallest financial input needed by Net Profit Margin, then implement the analyzer.
