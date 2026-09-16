# DEC-056 — Analysis Input Assembly

## Status

Accepted and implemented on `m12-runtime-integration`.

## Context

`DailyMarketAnalysis` intentionally receives fully assembled `StockAnalysisInput` objects. The input contains the stock identity, price bars, two financial periods, timeframe, and analysis lookbacks. The API/result-store path is already working, but nothing in the runtime currently assembles those inputs from acquisition boundaries.

## Decision

Introduce `AnalysisInputAssembler` as an application service between data acquisition and `DailyMarketAnalysis`.

The flow is:

```text
MarketDataProvider ───────┐
                          ├─> AnalysisInputAssembler ─> StockAnalysisInput ─> DailyMarketAnalysis
FundamentalDataProvider ──┘
```

The assembler:

1. receives an already-resolved `Stock` and an `as_of` date;
2. requests daily raw market observations for the configured acquisition window;
3. assesses market-data quality;
4. converts valid observations into domain `PriceBar` objects;
5. requests the current and previous financial periods;
6. creates the `StockAnalysisInput` consumed by `DailyMarketAnalysis`.

## Boundaries

- `MarketDataProvider` remains the market-data acquisition boundary.
- `FundamentalDataProvider` is introduced as the fundamental-data acquisition boundary.
- Provider implementations are infrastructure concerns and are not part of the assembler.
- `AnalysisInputAssembler` does not perform scoring, technical analysis, fundamental analysis, opportunity classification, persistence, or HTTP work.

## Data quality behavior

The assembler does not silently turn invalid raw observations into `PriceBar` objects. An observation must be `VALID` according to the existing `DataQualityAssessor` before `PriceBarFactory` can create the domain value. Empty market data and invalid observations therefore fail input assembly explicitly.

## Deferred decisions

- Stock symbol → `Stock` resolution/catalog.
- Production `FundamentalDataProvider` implementation.
- Mubasher/other financial-data acquisition strategy.
- Runtime wiring of the assembler into the daily execution path.
- Persistent acquisition cache/history.
- Per-stock retry/error reporting during input assembly.

These are intentionally separate from the first assembler slice so the application boundary stays testable and provider-agnostic.
