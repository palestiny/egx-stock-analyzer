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

The canonical archive contains 22 reported daily records for Egypt Aluminum (`EGAL`) from 2026-09-28 through 2026-10-28. The recorded source attribution and numeric precision are retained in the archive.

Source: https://ng.investing.com/equities/egypt-aluminum-historical-data  
Original retrieval date: 2026-10-28.

The seed does not include verified traded value, execution count, intraday candles, or order-level buy/sell pressure.

**Migration verification caveat (2026-11-06):** The specifically named source file `data/market_history/egal_daily_2026-09-28_to_2026-10-28.csv` is absent from both the current `main` tree and the collection branch tree. GitHub also returns no commit history for that exact path on the collection branch. The 22 EGAL rows are present in the canonical CSV, but row-for-row equivalence with the named legacy file cannot be independently verified from the repository. PR #447 does not delete that file; it is not present in either checked tree. Recover the original from its prior working copy or backup and compare all fields before treating the migration audit as closed. No missing values have been reconstructed.


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
4. `quality_status` carries one primary label. When OHLC geometry is inconsistent, use exactly `ohlc_inconsistency_review`; record any concurrent provider/source conflict details in `notes` rather than concatenating multiple labels.
5. Keep unknown fields blank and explain why; never fabricate missing market data.
6. Keep daily bars separate from intraday data. OHLCV alone does not prove buy/sell flow or order-flow imbalance.
7. Record each source's retrieval time and delay/price type only when known; otherwise label it unverified.
8. Treat the CSV in this repository as a version-controlled archive. It is **not** proof of persistence in the application's database or proof that a scheduled collector has successfully run.
9. This is partial coverage, not a complete EGX-listed universe or a production-grade feed. Confirm coverage, licensing, and source reliability before production use.

## Daily collection: 2026-11-04

Added 27 source-reported daily rows for the 2026-11-04 session: 19 equities (`ABUK`, `ALUM`, `CANA`, `EGAL`, `EGAS`, `EGCH`, `EFIC`, `ELEC`, `ETEL`, `FWRY`, `JUFO`, `MBSC`, `MFPC`, `MHOT`, `ORAS`, `ORHD`, `PHAR`, `SCEM`, `SWDY`) and eight indices (`EGX30`, `EGX33`, `EGX70EWI`, `EGX100EWI`, `EGHLTH`, `EGIMCS`, `EGREAL`, `EGTRVL`).

Source pages are the per-instrument Investing.com Philippines historical-data pages linked in each CSV row. Collection timestamp recorded: `2026-11-04T19:04:48+02:00`. Volume values shown in K/M/B were normalized to thousands in `volume_thousands_reported`; the source-displayed unit/value is retained in each row's notes. The provider does not supply verified traded value or execution counts in these retrieved rows, and exact quote latency is not consistently stated.

### Data-quality exceptions retained transparently

- Fifteen equity rows (`EGAL`, `ALUM`, `FWRY`, `ABUK`, `EFIC`, `EGCH`, `MBSC`, `PHAR`, `MFPC`, `SWDY`, `CANA`, `ELEC`, `ORHD`, `JUFO`, `ORAS`) report an opening price below the reported daily low. The source values are preserved and marked `ohlc_inconsistency_review`; do not use these bars in trusted OHLC analysis until reconciled.
- `ETEL`, `FWRY`, `PHAR`, and `MFPC` have discrepancies between page-header quote/change and historical-table row. The notes preserve the issue.
- Four indices (`EGX30`, `EGX70EWI`, `EGX100EWI`, `EGX33`) have reported open/low inconsistencies; some also have page-header or regional-result discrepancies. Their source values remain flagged for review.
- Index-page volume values are recorded as displayed but their interpretation as comparable trading volume has not been independently verified.
- No daily row was added for symbols where a reliable session row was not found. Missing values were not estimated.

## Current coverage status

- Total records after the 2026-11-05 collection: 186.
- Records for 2026-11-05: 23 (17 equities and 6 indices).
- Records for 2026-11-04: 27 (19 equities and 8 indices).
- Prior records through 2026-11-03: 136.
- Full EGX-listed universe: not included.
- Verified traded value and execution counts: not included in the new rows.
- Intraday execution tape: not included.
- 2026-11-04 rows requiring OHLC review: 19; 2026-11-05 rows requiring OHLC review: 11.
- Database ingestion: not established by this archive alone.

## Daily collection: 2026-11-05

Added 23 source-reported daily rows for the 2026-11-05 session to the canonical CSV: 17 equities (`ABUK`, `ADIB`, `ACAP`, `CCAP`, `COMI`, `EGAL`, `EFID`, `ELEC`, `ETEL`, `FWRY`, `HDBK`, `HELI`, `ORAS`, `PHDC`, `RACC`, `RAYA`, `TMGH`) and six indices (`EGX30`, `EGX30CAP`, `SHARIAH`, `EGREAL`, `EGX70EWI`, `EGX100EWI`).

Collection timestamp recorded in the rows: `2026-11-05T19:52:01+02:00`. All observations are daily historical table rows, not intraday candles. Volume displayed in K/M/B was normalized to thousands in `volume_thousands_reported`; the source-displayed unit is recorded in the notes. Traded value and execution counts are blank because verified per-instrument values were not available from the historical pages. Exact quote latency is not stated consistently by the provider.

### Data-quality exceptions retained transparently

- `ABUK`, `ETEL`, `COMI`, `RAYA`, `FWRY`, and `ADIB` have differing values across localized Investing.com historical pages for the same date. The CSV preserves the selected page's values and marks each row `source_conflict_review`; do not silently average or overwrite them.
- `EGX30` is stored from a localized daily historical row with internally consistent OHLC. Its close and +0.99% change agree with same-day Egyptian market reporting; other localized provider pages disagree on the opening value and/or volume. The row remains marked `source_conflict_review`.
- `EGX30CAP` has a localized-page disagreement on close/open/volume and is marked `source_conflict_review`.
- `ABUK`, `ETEL`, `COMI`, `RAYA`, `ACAP`, `RACC`, `TMGH`, `ORAS`, and `HELI` have source-reported opens below their reported lows. Their source values are retained and each row is marked `ohlc_inconsistency_review`; source-conflicting rows also retain `source_conflict_review`.
- `EGX70EWI` has a provider-reported open below its reported low and conflicting localized-page closes. The source values are retained and the row is marked `source_conflict_review;ohlc_inconsistency_review`.
- `EGX100EWI` has a provider-reported open below its reported low; the selected close also differs from same-day Egyptian market reporting. The source values are retained and the row is marked `source_conflict_review;ohlc_inconsistency_review`.
- `EGAL`, `ELEC`, `PHDC`, `ACAP`, `RACC`, `CCAP`, `HDBK`, `EFID`, `SHARIAH`, and `EGREAL` are recorded from the retrieved historical page rows without a second full historical OHLCV source reconciliation. This is not equivalent to exchange-certified data.

Same-day market context: Egyptian market reporting described EGX30 closing at 51,152.73 (+0.99%), EGX70 EWI at 17,567.23 (+2.42%), and EGX100 EWI at 23,461.29 (+1.96%). Enterprise reported total market turnover of EGP 10.2 billion. These are market-level/index context figures, not per-security traded values, and are therefore not written into any individual security's `traded_value_egp` field. References: https://ar.belbalady.net/7704543 and https://enterpriseam.com/egypt/2026/11/05/what-the-markets-are-doing-on-5-november/.

## Daily collection: 2026-11-08

Added 23 source-reported daily historical rows for the Sunday 2026-11-08 EGX session to the canonical CSV: 17 equities (`ABUK`, `ACAP`, `ADIB`, `CCAP`, `COMI`, `EGAL`, `EFID`, `ELEC`, `ETEL`, `FWRY`, `HDBK`, `HELI`, `ORAS`, `PHDC`, `RACC`, `RAYA`, `TMGH`) and six indices (`EGX30`, `EGX30CAP`, `EGREAL`, `EGX70EWI`, `EGX100EWI`, `SHARIAH`).

Collection timestamp recorded in the rows: `2026-11-08T19:45:44+02:00`. All observations are daily historical table rows, not intraday candles. The selected provider pages are linked row-by-row in `source_url`; exact quote latency is not consistently stated, so `delay_status` explicitly says it is not stated. Values displayed in K/M/B were normalized to thousands in `volume_thousands_reported`, retaining the original displayed unit and value in `notes`. `traded_value_egp` and `executions_count` remain blank because verified per-security values were not available from the selected historical rows.

### Session-level context (not assigned to individual securities)

Enterprise reported that the EGX30 fell about 0.7% and total market turnover was EGP 8.3 billion on 2026-11-08. Almasdar's same-day market recap reported rounded closes of about 50,812 for EGX30 (-0.67%), 62,781 for EGX30 Capped (-0.69%), 17,687 for EGX70 (+0.68%), and 23,526 for EGX100 (+0.28%). These are market/index-level figures; aggregate turnover is not a per-security traded value and was not written into any individual row. References: https://enterpriseam.com/egypt/2026/11/08/what-the-markets-are-doing-on-8-november-2026/ and https://www.almasdar.com/175839.

### Data-quality exceptions retained transparently

- `EGX30` (2026-11-08): the selected Dutch localized historical row reports open=51,152.73 above high=51,030.09. The English localized result reports a different close (50,834.30 versus 50,812.07) and volume (156.35M versus 189.91M); same-day Egyptian reporting supports a rounded close near 50,812 and -0.67%. Source values were preserved and the row is marked `ohlc_inconsistency_review`; do not use it as a clean OHLC bar until reconciled.
- `EGX30CAP` (2026-11-08): source-reported open=63,219.99 exceeds high=63,034.92. Same-day Egyptian reporting corroborates the rounded close near 62,781 and -0.69%. Source values were preserved and the row is marked `ohlc_inconsistency_review`.
- `ORAS` (2026-11-08): the selected Philippines localized historical row reports close=801.00 and volume=124.43K, while an Italian localized page reports close=811.00 and volume=1.94K (+0.12%). The selected row is preserved and marked `source_conflict_review`; do not silently average or overwrite it.
- `HELI` (2026-11-08): the selected Canada localized historical row reports close=6.90 and volume=5.68M (-0.58%), while a Dutch localized page reports close=6.88 and volume=5.47M (-0.86%). The selected row is preserved and marked `source_conflict_review`.
- Index-page volume values are preserved as displayed and normalized to thousands, but their interpretation as comparable trading volume has not been independently validated.
- No verified per-security traded value or execution count was available in the retrieved rows. The EGP 8.3bn turnover is market-wide only.
- Coverage remains partial; no row was invented for any instrument without a sufficiently attributable daily historical row.

### Legacy EGAL source-file recheck — 2026-11-08

The exact requested path `data/market_history/egal_daily_2026-09-28_to_2026-10-28.csv` remains absent from the current `main` tree, and the GitHub path-specific commit-history query returned no commits. The canonical CSV's existing 22 EGAL seed rows were left byte-for-byte unchanged; no source file was deleted and no row-for-row equivalence claim is made. The original file must be recovered from its prior working copy or backup before the migration audit can be closed.

## Current coverage status (as of 2026-11-08)

- Total records after the 2026-11-08 collection: 209.
- Records for 2026-11-08: 23 (17 equities and 6 indices).
- Records through 2026-11-05: 186.
- New 2026-11-08 rows requiring OHLC review: 2 (`EGX30`, `EGX30CAP`).
- New 2026-11-08 rows with localized-source conflicts: 2 (`ORAS`, `HELI`).
- Verified per-security traded value and execution counts: not available in this collection.
- Application database ingestion: not established by this archive alone.
- M61 and backtesting: not performed.
