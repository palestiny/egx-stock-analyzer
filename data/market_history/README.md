# EGX historical market-data archive

## Canonical storage

- **Single historical dataset:** `egx_daily_history.csv`
- **This documentation file:** `README.md`
- Add new daily records to the canonical CSV; do not create a separate CSV for each trading session or ticker.
- Natural uniqueness key: `(session_date, symbol)`. Reject duplicates or reconcile them explicitly before adding records.

## Schema

The canonical CSV uses one row per instrument per trading session. Equity and index bars share the same file while retaining their instrument type and unit:

- `session_date`: exchange session date, ISO `YYYY-MM-DD`.
- `instrument_type`: `equity` or `index`.
- `symbol`: equity ticker or index symbol.
- `price_unit`: `EGP` for equity prices and `points` for index levels.
- `open_value`, `high_value`, `low_value`, `close_value`: source-reported daily OHLC values in the unit identified by `price_unit`.
- `volume_thousands_reported`: reported volume normalized to thousands where a volume value is supplied. For example, source-displayed `1.97M` is stored as `1970.00`. The `notes` column preserves the source's displayed unit and value. Rounded provider volume is not an exact share-level tape.
- `change_pct_reported`: source-reported daily percentage change.
- `traded_value_egp`, `executions_count`: blank when the source did not provide a verified value.
- `source_name`, `source_url`, `retrieved_at`: provenance.
- `price_type`, `delay_status`, `quality_status`, `notes`: data semantics and quality caveats.

## Initial seed

The initial seed contains 22 reported daily records for Egypt Aluminum (`EGAL`) from 2026-09-28 through 2026-10-28, migrated from the previous date-specific seed.

Source: https://ng.investing.com/equities/egypt-aluminum-historical-data  
Original retrieval date: 2026-10-28.

The seed does not include verified traded value, execution count, intraday candles, or order-level buy/sell pressure.

## Daily collection: 2026-10-29

Added 19 source-reported equity rows for the 2026-10-29 session across these symbols: `ABUK`, `BTFH`, `CANA`, `CIEB`, `COMI`, `DGTZ`, `EGAL`, `EGAS`, `EFIC`, `ELEC`, `ETEL`, `FAIT`, `FWRY`, `GRCA`, `IRON`, `MICH`, `SWDY`, `UBEE`, and `VERT`.

Added four index rows in the same archive: `EGX30`, `EGX30CAP`, `EGX33`, and `EGXNBFINTECH`. Index values are explicitly labeled in points rather than EGP. Where an index page displayed volume, the source value was preserved in notes and normalized in the volume column; the interpretation of index-page volume has not been independently verified.

All new rows cite the corresponding Investing.com historical-data page. Collection timestamp recorded in the rows: `2026-10-29T19:53:01+03:00`. The historical pages did not consistently state quote latency, so `delay_status` says latency was not stated. Traded value and execution counts remain blank because verified per-instrument values were not available from the cited pages.

### Data-quality exceptions retained transparently

- `MICH` (2026-10-29): source-reported open is 40.57 while reported low is 40.60. This is internally inconsistent as an OHLC bar. The source values were preserved and the row is marked `ohlc_inconsistency_review`.
- `FAIT` (2026-10-29): source-reported open is 43.07 while reported low is 43.30. This is internally inconsistent as an OHLC bar. The source values were preserved and the row is marked `ohlc_inconsistency_review`.
- `EGAL` (2026-10-28): the archived seed reports open 303.50, high 307.00, and volume 189.55K. The current page now displays open 305.00, high 307.20, and volume 191.13K for that session. The archived numbers were not overwritten; the row is marked `source_revision_conflict` pending reconciliation.
- Provider pages can revise values and may show a current quote that differs from the historical table. Keep source-reported daily bars and retrieval timestamps; do not silently overwrite historical observations.

## Collection and validation rules

1. Append to `egx_daily_history.csv`; preserve historical records and original source values.
2. Validate dates, instrument types, symbols, price units, numeric ranges, OHLC consistency, volume units, source attribution, and duplicate keys `(session_date, symbol)`.
3. Keep source values even when inconsistent only if the row is explicitly flagged for review; never silently repair or invent OHLC fields.
4. Keep unknown fields blank and explain why; never fabricate missing market data.
5. Keep daily bars separate from intraday data. OHLCV alone does not prove buy/sell flow or order-flow imbalance.
6. Record each source's retrieval time and delay/price type only when known; otherwise label it unverified.
7. Treat the CSV in this repository as a version-controlled archive. It is **not** proof of persistence in the application's database or proof that a scheduled collector has successfully run.
8. This is partial coverage, not a complete EGX-listed universe or a production-grade feed. Confirm coverage, licensing, and source reliability before production use.

## Current coverage status

- Total records in the current collection branch after the 2026-11-02 update: 107.
- Records for 2026-11-02: 32 across 21 equity symbols and 11 index symbols.
- Records for 2026-11-01: 30 across 20 equity symbols and 10 index symbols.
- Records for 2026-10-29: 23 across 19 equity symbols and 4 index symbols.
- Historical seed records through 2026-10-28: 22 for EGAL.
- Full EGX-listed universe: not included.
- Verified traded value and execution counts: not included in the daily seed rows.
- Intraday execution tape: not included.
- OHLC exceptions requiring review: MICH and FAIT for 2026-10-29.
- Historical provider revision conflict: EGAL for 2026-10-28.
- Database ingestion: not established by this archive alone.


## Daily collection: 2026-11-01

Added **30 source-reported daily rows** to the canonical CSV for the 2026-11-01 session: 20 equities (`ABUK`, `BTFH`, `CANA`, `CIEB`, `COMI`, `DGTZ`, `EGAL`, `EGAS`, `EFIC`, `EFIH`, `ELEC`, `ETEL`, `FAIT`, `FWRY`, `GRCA`, `IRON`, `MICH`, `SWDY`, `UBEE`, `VERT`) and 10 indices (`EGX30`, `EGX30CAP`, `EGX33`, `EGBANK`, `EGHLTH`, `EGBASC`, `EGX35LV`, `EGSHTS`, `EGX100EWI`, `EGX70EWI`). This expands index coverage while keeping all rows in the same canonical CSV.

Collection timestamp recorded in these rows: `2026-11-01T19:40:41+02:00`. Source: the corresponding Investing.com historical-data page recorded on each row. All volume values are normalized to thousands while `notes` preserves the provider-displayed unit. Volume displayed for indices is retained only as source-reported metadata; its interpretation as an index-level volume measure is not independently verified. `traded_value_egp` and `executions_count` remain blank because verified per-instrument values were not available.

### Data-quality exceptions retained transparently

- `VERT` (2026-11-01): the historical-data table reports close 4.050 and volume 224.90K, while another Investing.com quote result reported 4.130 and 177.65K. The historical-table values were retained and the row is marked `source_conflict_review`.
- `EGX30`, `EGX30CAP`, and `EGX33` (2026-11-01): Investing.com result variants disagree on one or more OHLC/volume fields. The values from the selected NG historical-data result are preserved, marked `source_conflict_review`, and must be reconciled before using these rows for high-confidence index analytics.
- `EGXNBFINTECH`: no verifiable 2026-11-01 historical bar was available from the retrieved page/search results, so no row was fabricated. This symbol remains unupdated for this session.
- The archive remains partial-market coverage, not the complete EGX-listed universe. The new `EFIH` row and additional index rows extend coverage but do not establish full-market completeness.
- No intraday data, execution tape, or buy/sell order-flow inference was added.


## Daily collection: 2026-11-02

Added **32 source-reported daily rows** for the 2026-11-02 session to the same canonical CSV: 21 equities (`ABUK`, `ALUM`, `AMER`, `ATQA`, `BTFH`, `CIEB`, `COMI`, `DSCW`, `EGAL`, `EGAS`, `EFIC`, `EFIH`, `ELEC`, `ETEL`, `FAIT`, `FWRY`, `MFPC`, `MICH`, `OIH`, `SWDY`, `VERT`) and 11 indices (`EGX30`, `EGX30CAP`, `EGX33`, `EGBANK`, `EGHLTH`, `EGBASC`, `EGX35LV`, `EGX70EWI`, `EGX100EWI`, `FTWIEGY`, `EGBULM`). This is partial-market coverage, not a complete EGX universe.

Collection timestamp recorded in these rows: `2026-11-02T19:08:12+02:00`. Every row contains the individual historical-data source URL, retrieval timestamp, daily data type, and an explicit delay-status note. Source-displayed volume was normalized to thousands in `volume_thousands_reported`; the notes retain the provider-displayed unit. For index rows, source-displayed volume is retained as reported metadata only; its interpretation as an index-level volume measure is not independently verified. Where the source did not display volume, the field remains blank. `traded_value_egp` and `executions_count` remain blank because verified per-instrument values were not available.

### Data-quality exceptions retained transparently

- `ABUK` (2026-11-02): source-reported open=84.55 is below source-reported low=84.60. Values were preserved and the row is marked `ohlc_inconsistency_review`.
- `ETEL` (2026-11-02): source-reported open=117.82 is below source-reported low=118.00. Values were preserved and the row is marked `ohlc_inconsistency_review`.
- `EGX100EWI` (2026-11-02): source-reported open=22,410.52 is below source-reported low=22,426.26. Values were preserved and the row is marked `ohlc_inconsistency_review`.
- `CIEB` (2026-11-02): the selected global Investing.com historical result reports close=22.50 and volume=220.37K; another regional Investing.com result reports close=22.48 and volume=315.61K. The selected row is marked `source_conflict_review`.
- `ELEC` (2026-11-02): Investing.com regional results disagree materially on close and volume (including 1.490/21.89M, 1.500/27.67M, and 1.520/4.06M). The selected global result is retained and marked `source_conflict_review`.
- `FAIT` (2026-11-02): Investing.com regional results disagree (including 43.60/3.66K and 42.50/16.13K). The selected Polish result is retained and marked `source_conflict_review`.
- `EGX30` (2026-11-02): two retrieved Investing.com result variants disagree on close and volume. The selected NG historical result is retained and marked `source_conflict_review`; do not use it as a reconciled benchmark observation.
- The retrieved results did not provide a verifiable 2026-11-02 daily row for some previously tracked symbols, including `DGTZ`, `GRCA`, `IRON`, `UBEE`, and `EGXNBFINTECH`. No row was fabricated for them. Absence from this collection does not imply zero trading or suspension.
- The dataset still does not cover every EGX-listed security. No intraday bars, trade tape, executions, or order-level buy/sell-flow inference were added.

## Daily collection: 2026-11-03

Added **29 source-reported daily rows** for the 2026-11-03 session to the canonical CSV: 18 equities (`ABUK`, `ALUM`, `AMER`, `ATQA`, `BTFH`, `COMI`, `DSCW`, `EGAL`, `EGAS`, `EGCH`, `EFIH`, `ETEL`, `FWRY`, `MBSC`, `MFPC`, `MICH`, `OIH`, `VERT`) and 11 indices (`EGX30`, `EGX30CAP`, `EGX33`, `EGBANK`, `EGHLTH`, `EGBASC`, `EGX35LV`, `EGX70EWI`, `EGX100EWI`, `FTWIEGY`, `EGBULM`). This remains partial coverage, not the complete EGX-listed universe.

Collection timestamp recorded in the new rows: `2026-11-03T19:11:18+02:00`. Each row contains its individual Investing.com historical-data URL, retrieval timestamp, daily-bar type, price unit, delay-status note, and quality status. The source displayed volume was normalized to thousands in `volume_thousands_reported`; `notes` preserves the source-displayed volume and unit. For index rows, any displayed volume is retained as source-reported metadata only; interpretation as index-level volume is not independently verified. Where a source did not show volume, the field remains blank. `traded_value_egp` and `executions_count` remain blank because verified per-instrument values were not available.

### Data-quality exceptions and omissions

- `EGBASC` (2026-11-03): the selected source table reports open=4623.49 and high=4585.49, an internally inconsistent OHLC bar. These source values were preserved and the row is marked `ohlc_inconsistency_review`; no field was silently corrected.
- `COMI` (2026-11-03): the source reports open=121.40 and low=121.51, an internally inconsistent OHLC bar. Values were preserved and the row is marked `ohlc_inconsistency_review`.
- `EGX30` (2026-11-03): retrieved Investing.com regional result variants disagree on close and/or volume (including closes 49,255.66 and 49,160.37). The selected NG historical-table values were retained and the row is marked `source_conflict_review`; reconcile before treating it as a high-confidence benchmark observation.
- `EFIC` was not added for 2026-11-03 because retrieved results for the same historical page conflicted materially (including close 136.40 / volume 55.65K versus close 133.04 / volume 36.25K). A source value was not selected by guesswork.
- A verifiable 2026-11-03 row was not obtained during this run for `CIEB`, `ELEC`, and `SWDY`; no rows were fabricated. This does not imply zero trading or suspension.
- The collection includes daily historical bars only. No intraday bars, execution tape, traded-value estimates, execution counts, or order-level buy/sell-flow inference were added.
- The archive now contains **136 data rows** across the seeded EGAL history and collected sessions through 2026-11-03. This is a version-controlled GitHub archive; it does not prove that data has been loaded into the application database.

