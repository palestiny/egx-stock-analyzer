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

### Revenue Growth

The third independent evidence capability is **Revenue Growth**, representing a growth observation across two financial periods.

`Revenue Growth = (Current Revenue - Previous Revenue) / Previous Revenue`

The analyzer receives the current and previous `FinancialPeriod` explicitly. It classifies the calculated result as positive, negative, or neutral.

A previous-period revenue of zero produces `UNDEFINED` because the growth rate cannot be calculated deterministically.

The MVP does not interpret a positive growth rate as automatically good or a negative rate as automatically bad. Interpretation, thresholds, comparison, weighting, and scoring remain outside the evidence analyzer.

## Financial Period

`FinancialPeriod` remains an immutable Value Object. It contains the financial observations required by the current evidence slices:

- `period_end`
- `revenue`
- `net_income`
- optional `current_assets`
- optional `current_liabilities`

Liquidity observations are optional so profitability analysis does not require them.

Revenue growth uses two `FinancialPeriod` instances rather than embedding historical periods into a single period object. This keeps period identity simple and makes historical comparison explicit at the analyzer boundary.

## Fundamental Analysis Result

`FundamentalAnalysisResult` is an immutable composition object for one stock and one current financial period.

It contains:

- `stock_id`
- `period_end`
- independent fundamental evidence, currently `profitability`, `liquidity`, and `growth`

The result does not calculate ratios or make trading decisions.

## Fundamental Analysis Orchestration

`FundamentalAnalysisOrchestrator` coordinates the existing analyzers and composes their evidence into `FundamentalAnalysisResult`.

The orchestrator receives the current period and previous period because revenue growth requires historical context.

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

The evidence slices deliberately cover three different fundamental areas—profitability, liquidity, and growth—without introducing scoring or a large financial-statement abstraction.

Revenue growth also verifies that the composition model can handle evidence requiring more than one financial period while keeping historical context explicit.

## Next TDD Step

After the current tests are green, review whether another independent fundamental evidence area is needed before M6 Scoring. Do not add speculative financial metrics or scoring before that decision.
