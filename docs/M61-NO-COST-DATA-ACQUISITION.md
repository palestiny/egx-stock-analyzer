# M61 — No-cost market-data acquisition path

**Decision:** use a no-payment discovery path first. Do not block engineering progress on a paid API or CSV order.
**Status:** exploratory tooling only; no market or financial source is accepted by this document.
**Updated:** 2026-10-09

## Constraints

- No paid subscriptions, API plans, or data purchases are required to run the exploratory probe below.
- A free endpoint is not automatically a legally reusable dataset. Source terms, retention, research use, and redistribution must be reviewed independently.
- The probe cannot supply point-in-time financial statements. Market bars and financial snapshots remain separate evidence tracks.
- Do not use a candidate response to claim a profitable strategy, accepted M61 dataset, or production-ready analytics.

## First path: Yahoo chart endpoint (diagnostic only)

The repository already depends on `yfinance`, and Yahoo chart history can be queried without a paid Yahoo Finance Gold CSV download flow. The new probe uses the public chart endpoint directly so it can preserve exact response bytes and checksums when the operator explicitly opts in.

The tool:
- checks the fixed ten-symbol cohort using `.CA` ticker candidates;
- requests daily observations from 2019-01-01 through 2025-12-31, including dividend/split event metadata;
- records source timezone and refuses to normalize dates if timezone metadata is missing or invalid;
- keeps raw close and adjusted close separate;
- validates OHLCV, duplicates, ordering, the 252-session warm-up, and 2021–2025 calendar-year coverage;
- records a response checksum and exact byte count;
- defaults to not persisting source responses; `--preserve-raw` is an explicit local opt-in that writes exact JSON bytes plus a normalized candidate CSV;
- always labels output `CANDIDATE_ONLY`, marks terms unverified, and forbids Strategy v0 eligibility.

### PowerShell

From the repository root:

```powershell
python -m tools.m61_free_market_probe --output-dir .\artifacts\m61-free-probe
```

This runs a non-persisting probe and writes only the report. To explicitly preserve the responses and candidate CSVs locally for inspection:

```powershell
python -m tools.m61_free_market_probe --output-dir .\artifacts\m61-free-probe --preserve-raw
```

The output directory must be empty or absent. The tool refuses to overwrite a non-empty evidence directory.

## Second path: EGID/EGX public feed

The public EGID Swagger UI lists date-range and symbol-history operations. That makes it a worthwhile no-cost source to test next, but the exact request/response schema, historical depth, reproducibility, and storage/use rights are still unverified. Do not write an adapter from endpoint names alone and do not infer that an endpoint is free for archival use merely because Swagger is public.

Reference: https://ticker.egidegypt.com/index.html

### EGID public API contract discovery

A bounded contract-inspection tool is available:

```powershell
python -m tools.m61_egid_contract_probe --output .\artifacts\egid-openapi-contract.json
```

It downloads only the public OpenAPI/Swagger document (maximum 5 MB) and extracts history/chart/token operation metadata, declared parameters, request schemas, security schemes, and relevant DTO fields. It does **not** authenticate, request market prices, save source data, or mark EGID as accepted. The report is intended to determine the exact request contract before attempting a single-symbol historical probe.

A successful contract report proves only that the public API description was reachable. It does not prove the history endpoint is accessible without payment, that the endpoint has 2019–2025 depth, that all M61 symbols are supported, or that long-term research storage is permitted. Those checks remain explicit gates.

## Financial evidence without a paid vendor

Use dated issuer/EGX disclosure documents and issuer investor-relations archives as candidate evidence. For each value, retain the document URL/reference, period end, public availability date, statement type, currency/unit, revision status, and source checksum when retention is permitted. A period-end date is not a substitute for `available_at`. This is a bounded manual-evidence path, not a claim that all ten stocks already have complete point-in-time coverage.

## Acceptance gate remains closed

The no-cost path is allowed to produce candidate artifacts and validation findings, but the accepted dataset still requires:
1. complete cohort and 252-session warm-up coverage;
2. no unresolved invalid bars, duplicates, identity mismatches, or unexplained gaps;
3. explicit adjustment/corporate-action semantics;
4. source and retention/use rights reviewed against the actual intended use;
5. point-in-time financial snapshots with defensible availability dates;
6. immutable artifacts, checksums, transformation manifest, and reproducible Strategy v0 evaluation.

If free sources cannot satisfy a gate, record the exact gap and exclude that claim or strategy input. Do not fabricate missing observations or silently upgrade a candidate to accepted.


## Live Yahoo probe result — 2026-10-09

A metadata-only probe completed at [GitHub Actions run #37920812142](https://github.com/palestiny/egx-stock-analyzer/actions/runs/37920812142) without preserving price rows. The endpoint returned HTTP 200 for all ten candidate tickers and broad date coverage through 2025-12-31 (FWRY began on 2019-08-14). However, this is **not a usable M61 dataset**: all ten responses reported `instrumentType=MUTUALFUND` and the OHLCV validator found hundreds of inconsistent/null rows per ticker. Terms and long-term storage rights also remain unverified.

**Decision:** reject this Yahoo response as an M61 acceptance source for now. The run proves only that the endpoint responds and returns a long series; row count/coverage must not override identity and data-quality failures. Continue with the public EGID/EGX feed contract investigation rather than accepting this candidate.


## Live no-cost source probe results — 2026-10-09

### EGID public API

The public OpenAPI document was reachable and declared POST /api/DelayedFeed/getSymbolHistory. Its HistoryReqDto includes SymbolCode, FromDate, ToDate, Skip, and Take. The API declares an Authorization header under a security scheme named Bearer; POST /api/Settings/GetToken takes Username and Password.

A single bounded COMI history request for 2025-01-01 through 2025-01-05, requesting at most 10 rows and sending **no credentials**, returned HTTP **401**. The probe did not persist or print price values.

**Conclusion:** the public documentation is reachable, but unauthenticated historical access is not. A free account/credential path and its terms are not established; do not attempt to bypass authentication.

### Yahoo chart endpoint

A live, non-persisting probe returned HTTP 200 for all ten candidate tickers. It wrote only a temporary metadata report on the CI runner; raw responses and candidate CSVs were not saved.

| Symbol | Rows | First observed date | Last observed date | OHLC consistency findings |
|---|---:|---|---|---:|
| COMI | 1,716 | 2019-01-01 | 2025-12-31 | 389 |
| EGAL | 1,716 | 2019-01-01 | 2025-12-31 | 436 |
| SWDY | 1,716 | 2019-01-01 | 2025-12-31 | 371 |
| ETEL | 1,716 | 2019-01-01 | 2025-12-31 | 319 |
| EAST | 1,716 | 2019-01-01 | 2025-12-31 | 334 |
| TMGH | 1,716 | 2019-01-01 | 2025-12-31 | 340 |
| PHDC | 1,716 | 2019-01-01 | 2025-12-31 | 374 |
| FWRY | 1,555 | 2019-08-14 | 2025-12-31 | 319 |
| EFID | 1,716 | 2019-01-01 | 2025-12-31 | 375 |
| HRHO | 1,716 | 2019-01-01 | 2025-12-31 | 376 |

A field-pair diagnostic showed that most findings are caused by the reported open falling outside the reported daily high/low range: COMI had 249 low-above-open and 140 high-below-open findings, while low/high versus close remained consistent for COMI. Several other tickers also had low/high versus close inconsistencies. This requires an independent reference to determine whether source field semantics or source values are wrong. The probe deliberately did not auto-drop, repair, or accept any row.

**Conclusion:** Yahoo is reachable and offers apparent date-range coverage, but this live candidate fails the current data-quality gate. Source terms/long-term storage rights also remain unverified, and point-in-time financial snapshots are still absent. Strategy v0 eligibility remains false.
