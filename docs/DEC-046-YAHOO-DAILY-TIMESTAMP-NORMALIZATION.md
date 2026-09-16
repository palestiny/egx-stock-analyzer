# DEC-046 — Yahoo Daily Timestamp Normalization

## Status

Accepted.

## Context

Yahoo Finance daily historical data uses a daily index. The current yfinance documentation names the non-intraday index `Date`; the adapter must therefore not depend on a `Datetime` column name. citeturn0search0turn0search2

The domain `PriceBar` requires a timezone-aware timestamp, while the raw observation boundary intentionally permits timestamps that still require quality assessment.

## Decision

The Yahoo adapter will map the provider's daily date field to a `datetime` representing the start of that calendar day in UTC.

This is an adapter-level representation of the provider's daily observation date. It does not claim that the market traded at midnight UTC.

The analytical meaning remains the trading date; session/calendar semantics remain outside `PriceBar`.

## Mapping

```text
Yahoo Date
   ↓
Timestamp at 00:00 UTC
   ↓
RawPriceBarObservation
```

The adapter will accept the first reset-index field as the daily date rather than requiring a provider-specific `Datetime` column name.

## Exclusions

- no trading-session inference;
- no Cairo-session conversion;
- no market-calendar validation;
- no missing-day inference;
- no data repair;
- no OHLC validation in the adapter.

Those concerns remain in Data Quality / future market-calendar boundaries.
