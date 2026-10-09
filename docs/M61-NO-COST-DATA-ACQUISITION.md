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

## No-cost source decision — live verification, 2026-10-09

### Yahoo Finance chart endpoint: rejected for M61

The no-cost probe returned HTTP 200 for all ten .CA candidates, with daily-looking history spanning 2019–2025. The returned metadata classified all ten as MUTUALFUND, and the existing OHLCV validator found hundreds of inconsistent/null observations per symbol. Do not use this response for Strategy v0. Details: [live probe run #37920812142](https://github.com/palestiny/egx-stock-analyzer/actions/runs/37920812142).

### EGID/EGX history endpoint: not anonymously accessible

The public Swagger document describes history/chart endpoints and declares a Bearer security scheme. A single COMI GetSymbolHistory request with no credentials returned HTTP 401. No authentication was attempted after that response. This means the public Swagger page is not an anonymous data feed; free account availability and storage terms are still unverified.

### Other advertised free sites are not accepted by assumption

- StockAnalysis says it has no programmatic API, prohibits automated scraping/bulk collection, and does not license data for building competing databases/products. Do not scrape it: https://stockanalysis.com/help/faq/api-access/ and https://stockanalysis.com/terms-of-use/
- EGXAPI advertises a free API, but its published legal center labels the Terms of Service as a design draft with placeholder wording. It is not an acceptable research-data source until binding terms, provider identity, historical coverage, and data rights can be verified: https://egxapi.com/legal/
- Paid sources remain out of scope because the project owner cannot pay.

### Current no-cost execution path

Do not fabricate data or quietly weaken M61. Use a real CSV that the owner can already export from an existing brokerage/account/platform only if that platform's terms permit the intended local research/storage. Run the existing evidence inspector and candidate-package builder, starting with COMI; preserve the original file and its checksum, and keep the candidate unaccepted until source rights, corporate-action semantics, warm-up, and financial availability gates pass. If no such export is available, the market-data portion remains blocked by source access, not by code.

The point-in-time financial dataset remains a separate open blocker; market bars alone cannot satisfy the full M61 Strategy v0 acceptance gate.


## TradingView-backed diagnostic — not an eligible data source

A one-time, non-persisting diagnostic using a TradingView-backed client returned 1,556–1,700 daily bars for the ten-symbol cohort over 2019–2025, with no basic OHLC relationship or numeric-missingness findings. This result is useful only as a technical comparison; no price rows were written to disk or committed.

Do **not** use TradeGlob/TradingView extraction to build or refresh the M61 dataset. TradingView's current Terms of Use restrict market data to display-only use and prohibit automated data collection and non-display processing, including algorithmic decision-making. That conflicts with this project's automated research/backtesting purpose unless explicit written authorization and applicable data-provider rights are obtained.

References:
- https://www.tradingview.com/policies/
- https://www.tradingview.com/support/solutions/43000674726-why-is-my-account-banned-due-to-suspicious-activity/

**Decision:** technically consistent data does not equal legally usable data. This route is rejected for automated dataset acquisition; do not repeat automated collection or persist the diagnostic results.


## Bounded Yahoo chart probe — 2026-10-09

The metadata-only live probe reached the Yahoo chart endpoint for all ten configured .CA symbols (HTTP 200), with Cairo timezone metadata and history through 2025-12-31. Nine symbols returned 1,716 daily observations; FWRY returned 1,555 from 2019-08-14. The probe surfaced 340–457 validation findings per symbol, including repeated high/low versus OHLC inconsistencies and null/invalid values. Raw responses and price rows were not retained.

**Result:** Yahoo is not accepted for Strategy v0 evaluation. Quality findings need root-cause investigation, source terms/long-term storage rights are unverified, and the endpoint supplies no point-in-time financial snapshots. The workflow is diagnostic only and must not be treated as approval to archive or redistribute provider data.
