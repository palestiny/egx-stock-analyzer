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

## Evidence Slices

### Net Profit Margin

`Net Profit Margin = Net Income / Revenue`

Zero revenue produces `UNDEFINED`. Zero or negative net income remains a valid observation.

### Current Ratio

The second independent evidence capability is **Current Ratio**, representing a simple liquidity observation.

`Current Ratio = Current Assets / Current Liabilities`

The MVP classifies the arithmetic result relative to `1` as above, below, or equal to one. This classification is evidence, not a trading decision or a universal liquidity judgment.

Zero current liabilities produce `UNDEFINED`. Missing current-assets or current-liabilities observations produce `INSUFFICIENT_DATA`.

## Financial Period

`FinancialPeriod` remains an immutable Value Object. Revenue and net income are required for the profitability slice. Current assets and current liabilities are optional so profitability analysis does not require liquidity data.

## Fundamental Analysis Result

`FundamentalAnalysisResult` is an immutable composition object for one stock and one financial period.

It contains:

- `stock_id`
- `period_end`
- independent fundamental evidence, currently `profitability` and `liquidity`

The result does not calculate ratios or make trading decisions.

## Fundamental Analysis Orchestration

`FundamentalAnalysisOrchestrator` coordinates the existing analyzers and composes their evidence into `FundamentalAnalysisResult`.

The orchestrator does not implement financial calculations, scoring, BUY/SELL decisions, weighting, or data-quality validation.

As additional fundamental evidence areas are implemented, they can be composed into the result without changing the responsibility of individual analyzers.

## Boundaries

Fundamental evidence analyzers do **not**:

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

The second slice deliberately adds a different evidence area—liquidity—without introducing scoring or a large financial-statement abstraction. This tests whether the composition model can accommodate independent evidence from different fundamental areas.

## Next TDD Step

Add another independent fundamental evidence capability only after its design gate is defined. Do not add speculative financial metrics or scoring before that.
