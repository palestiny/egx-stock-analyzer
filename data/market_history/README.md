# Historical market-data seed

## Scope

This is an initial, source-attributed seed dataset for Egypt Aluminum (EGAL), covering 22 reported daily sessions from 2026-09-28 through 2026-10-28. It is **not** a complete historical dataset for all EGX-listed securities.

## File

- `egal_daily_2026-09-28_to_2026-10-28.csv`
- Fields: session date, close/open/high/low in EGP, reported volume in thousands of shares, and reported daily change percent.
- Rows: 22.
- Source data retrieved: 2026-10-28.

## Source and limitations

Primary source page: https://ng.investing.com/equities/egypt-aluminum-historical-data

The source page displays daily volume rounded in thousands (for example, 189.55K). The CSV deliberately preserves that displayed precision in `volume_thousands_reported`; it must not be treated as exact share-level volume. The source does not provide per-session traded value, execution-level buy/sell pressure, or intraday candles in this dataset.

Independent sources may disagree on some fields, including the 2026-10-28 open/high/volume. For that reason this file preserves one identifiable source's reported values and does not silently average conflicting reports. The source URL and retrieval date should be retained with any derived analytics.

This seed is useful for pipeline and basic daily-chart validation only. It is not sufficient to claim intraday liquidity, order-flow imbalance, or current live signals. Obtain and verify a licensed/authorized complete feed before using the dataset as a production market-data source.

## Quality status

- Source attribution: recorded.
- Reported row count: 22.
- Precision limitation: documented.
- Cross-source reconciliation: pending.
- Full-market EGX history: not included.
- Intraday execution tape: not included.
- Persistent daily ingestion job wired to the application's database: not established by this seed alone.
