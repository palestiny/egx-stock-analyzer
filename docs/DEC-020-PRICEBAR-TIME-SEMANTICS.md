# DEC-020 — PriceBar Time Semantics and Market Observation Boundary

**Status:** Accepted
**Date:** 2026-09-11

## Context

`DEC-019` established `PriceBar` as the immutable domain representation of one OHLCV market observation, while leaving timeframe and timestamp semantics open.

The previous code still contained an older `MarketData` model with an OHLC validation rule (`High < Open`) that conflicted with the observation/data-quality boundary.

## Decision

The canonical domain model is now `PriceBar`.

`PriceBar`:

- is an immutable Value Object
- represents one OHLCV observation
- contains `stock_id`, `timeframe`, `timestamp`, `open`, `high`, `low`, `close`, and `volume`
- composes the existing `Price` and `Volume` Value Objects
- requires a timezone-aware timestamp
- does not enforce OHLC relationships such as `High >= Open`

The obsolete `MarketData` domain model is removed.

### Timeframe

The MVP supports:

```text
DAILY
```

`PriceBar` is timeframe-aware so future timeframes can be added without making the model Daily-specific.

Future intraday timeframes are not part of the current implementation scope.

### Daily Timestamp Semantics

The domain requires timezone-aware timestamps.

EGX/Cairo trading-date interpretation is a separate calendar/session concern and is not embedded in `PriceBar`.

### Live Monitoring Boundary

The following are intentionally separate concerns:

```text
Data ingestion capability
Domain bar granularity
Analysis cadence
Alert/UI cadence
```

Live observation and alerting requirements do not require introducing intraday candle analysis into the MVP.

### Aggregation

Aggregation is a separate capability/service and is not a responsibility of `PriceBar`.

## Alternatives Considered

### Keep MarketData as the canonical domain model

Rejected because the accepted domain decision already defines `PriceBar` as the canonical market observation and provides clearer boundaries.

### Put OHLC validation in PriceBar

Rejected. External observations must be preserved and assessed by Data Quality rather than rejected by the observation representation itself.

### Make PriceBar Daily-specific

Rejected because the project may later consume multiple bar granularities.

### Put trading-calendar rules inside PriceBar

Rejected because session/calendar semantics belong outside the immutable observation value object.

## Trade-offs

Benefits:

- one canonical market-observation concept
- clear separation of observation and quality
- explicit timeframe support
- timezone correctness at the domain boundary
- no premature intraday architecture

Costs:

- Data Quality still needs a dedicated design
- trading-calendar semantics remain outside the current domain object
- future timeframe expansion will require additional design

## Consequences

The next domain work should focus on Data Quality and trading-date/calendar semantics rather than adding validation to `PriceBar`.

External providers will eventually map their observations into `PriceBar` through an adapter/application boundary.

Technical analysis will consume `PriceBar` objects and will not own OHLCV representation.

## Revisit Conditions

Revisit this decision if:

- EGX calendar/session semantics require a richer time model
- live/intraday analysis becomes an MVP requirement
- provider data requires a distinct observation concept
- timeframe identity requires additional domain semantics
