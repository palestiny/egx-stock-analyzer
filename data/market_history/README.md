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
- `open_egp`, `high_egp`, `low_egp`, `close_egp`: source-reported daily OHLC prices in EGP.
- `volume_thousands_reported`: reported volume normalized to thousands of shares. For example, source-displayed `1.97M` is stored as `1970.00`. The `notes` column preserves the source's displayed unit and value. This remains rounded source data, not an exact share-level tape.
- `change_pct_reported`: source-reported daily percentage change.
- `traded_value_egp`, `executions_count`: blank when the source did not provide a verified value.
- `source_name`, `source_url`, `retrieved_at`: provenance.
- `price_type`, `delay_status`, `quality_status`, `notes`: data semantics and quality caveats.

## Initial seed

The initial seed contains 22 reported daily records for Egypt Aluminum (`EGAL`) from 2026-09-28 through 2026-10-28, migrated from the previous date-specific seed.

Source: https://ng.investing.com/equities/egypt-aluminum-historical-data  
Original retrieval date: 2026-10-28.

The source displays volume rounded in thousands. Do not reinterpret it as exact share-level volume. The seed does not include verified traded value, execution count, intraday candles, or order-level buy/sell pressure.

## Daily collection: 2026-10-29

Added 19 source-reported daily rows for the 2026-10-29 session across these symbols: `ABUK`, `BTFH`, `CANA`, `CIEB`, `COMI`, `DGTZ`, `EGAL`, `EGAS`, `EFIC`, `ELEC`, `ETEL`, `FAIT`, `FWRY`, `GRCA`, `IRON`, `MICH`, `SWDY`, `UBEE`, and `VERT`.

All new rows cite the corresponding Investing.com historical-data page. Collection timestamp recorded in the rows: `2026-10-29T19:53:01+03:00`. The historical pages did not consistently state quote latency, so `delay_status` says latency was not stated. Traded value and execution counts remain blank because verified per-symbol values were not available from the cited pages.

### Data-quality exceptions retained transparently

- `MICH` (2026-10-29): source-reported open is 40.57 while reported low is 40.60. This is internally inconsistent as an OHLC bar. The source values were preserved and the row is marked `ohlc_inconsistency_review`.
- `FAIT` (2026-10-29): source-reported open is 43.07 while reported low is 43.30. This is internally inconsistent as an OHLC bar. The source values were preserved and the row is marked `ohlc_inconsistency_review`.
- `EGAL` (2026-10-28): the archived seed reports open 303.50, high 307.00, and volume 189.55K. The current page now displays open 305.00, high 307.20, and volume 191.13K for that session. The archived numbers were not overwritten; the row is marked `source_revision_conflict` pending reconciliation.
- Provider pages can revise values and may show a current quote that differs from the historical table. Keep source-reported daily bars and retrieval timestamps; do not silently overwrite historical observations.

## Collection and validation rules

1. Append to `egx_daily_history.csv`; preserve historical records and original source values.
2. Validate dates, ticker symbols, numeric ranges, OHLC consistency, units, source attribution, and duplicate keys `(session_date, symbol)`.
3. Keep source values even when inconsistent only if the row is explicitly flagged for review; never silently repair or invent OHLC fields.
4. Keep unknown fields blank and explain why; never fabricate missing market data.
5. Keep daily bars separate from intraday data. OHLCV alone does not prove buy/sell flow or order-flow imbalance.
6. Record each source's retrieval time and delay/price type only when known; otherwise label it unverified.
7. Treat the CSV in this repository as a version-controlled archive. It is **not** proof of persistence in the application's database or proof that a scheduled collector has successfully run.
8. This is partial coverage, not a complete EGX-listed universe or a production-grade feed. Confirm coverage, licensing, and source reliability before production use.

## Current coverage status

- Total records in this archive after the 2026-10-29 collection: 41.
- Records for 2026-10-29: 19 across 19 listed symbols.
- Historical seed records through 2026-10-28: 22 for EGAL.
- Full EGX-listed universe: not included.
- Verified traded value and execution counts: not included in the daily seed rows.
- Intraday execution tape: not included.
- OHLC exceptions requiring review: MICH and FAIT for 2026-10-29.
- Historical provider revision conflict: EGAL for 2026-10-28.
- Database ingestion: not established by this archive alone.
