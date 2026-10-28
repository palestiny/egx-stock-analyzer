# EGX historical market-data archive

## Canonical storage

- **Single historical dataset:** `egx_daily_history.csv`
- **This documentation file:** `README.md`
- Add new daily records to the canonical CSV; do not create a separate CSV for each trading session or ticker.
- Natural uniqueness key: `(session_date, symbol)`. Reject duplicates or reconcile them explicitly before adding records.

## Schema

The canonical CSV uses one row per ticker per trading session:

- `session_date`: exchange session date, ISO `YYYY-MM-DD`.
- `symbol`: EGX ticker symbol.
- `open_egp`, `high_egp`, `low_egp`, `close_egp`: reported daily OHLC prices in EGP.
- `volume_thousands_reported`: source-displayed volume in thousands, preserving the provider's displayed precision; **not** an exact share count.
- `change_pct_reported`: source-reported daily percentage change.
- `traded_value_egp`, `executions_count`: blank when the source did not provide a verified value.
- `source_name`, `source_url`, `retrieved_at`: provenance.
- `price_type`, `delay_status`, `quality_status`, `notes`: data semantics and quality caveats.

## Seed data and provenance

The initial seed contains 22 reported daily records for Egypt Aluminum (`EGAL`) from 2026-09-28 through 2026-10-28, migrated from the previous single-stock seed file.

Source: https://ng.investing.com/equities/egypt-aluminum-historical-data  
Retrieved: 2026-10-28.

The source displays volume rounded in thousands. Do not reinterpret it as exact share-level volume. The seed does not include verified traded value, execution count, intraday candles, or order-level buy/sell pressure. Cross-source reconciliation remains pending, including reported differences for some sessions. No conflicting values should be silently averaged or overwritten.

## Collection and validation rules

1. Append to `egx_daily_history.csv`; preserve historical records and original source values.
2. Validate dates, ticker symbols, numeric ranges, OHLC consistency, units, source attribution, and duplicate keys `(session_date, symbol)`.
3. Keep unknown fields blank and explain why; never fabricate missing market data.
4. Keep daily bars separate from intraday data. OHLCV alone does not prove buy/sell flow or order-flow imbalance.
5. Record each source's retrieval time and delay/price type only when known; otherwise label it unverified.
6. Treat the CSV in this repository as a version-controlled archive. It is **not** proof of persistence in the application's database or proof that a scheduled collector has successfully run.
7. This seed is not complete EGX-wide coverage and is not accepted as a production feed. Confirm data rights, coverage, and source reliability before production use.

## Current coverage status

- Historical records: 22.
- Symbols represented: EGAL only.
- Full EGX-listed universe: not included.
- Verified traded value and execution counts: not included in the seed.
- Intraday execution tape: not included.
- Cross-source reconciliation: pending.
- Database ingestion: not established by this archive alone.
