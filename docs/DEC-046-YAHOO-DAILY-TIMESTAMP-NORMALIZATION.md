# DEC-046 — Yahoo Daily Timestamp Normalization

## Status

Accepted.

## Context

Yahoo Finance daily historical data uses a daily index. The current yfinance documentation names the non-intraday index `Date`; the adapter must therefore not depend on a `Datetime` column name. citeturn0search0turn0search2

The domain `PriceBar` requires a timezone-aware timestamp, while the raw observation boundary intentionally permits timestamps that still require quality assessment.

Yahoo also exposes numeric market values through a pandas DataFrame, so the adapter must normalize provider numeric values into the raw observation types expected by the domain boundary.

## Decision

The Yahoo adapter will:

1. map the provider's daily date field to a `datetime` representing the start of that calendar day in UTC;
2. convert OHLC values to `Decimal` using their string representation;
3. convert volume to `int`;
4. preserve the values without applying trading logic or quality rules.

This is adapter-level representation of the provider's daily observation. It does not claim that the market traded at midnight UTC.

The analytical meaning remains the trading date; session/calendar semantics remain outside `PriceBar`.

## Mapping

```text
Yahoo Date
   ↓
UTC-aware datetime
   ↓
OHLC → Decimal
Volume → int
   ↓
RawPriceBarObservation
```

## Exclusions

- no trading-session inference;
- no Cairo-session conversion;
- no market-calendar validation;
- no missing-day inference;
- no data repair;
- no OHLC validation in the adapter;
- no adjusted-price transformation.

Those concerns remain in Data Quality / future market-calendar boundaries. The adapter uses `auto_adjust=False` so the raw OHLC fields are not silently adjusted by the client. citeturn0search0
