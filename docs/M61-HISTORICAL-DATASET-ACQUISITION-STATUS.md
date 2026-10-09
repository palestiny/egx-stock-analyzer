# M61 — Historical Dataset Acquisition Status

**Status:** Acquisition boundary accepted; real dataset not yet accepted for evaluation.  
**Decision:** DEC-130  
**Updated:** 2026-10-09 — strict canonical CSV parsing, annual evaluation-window coverage, and recent 252-session warm-up validation are being hardened; CI verification pending

## Purpose

This document records the concrete acquisition state after DEC-130. It is an operational checkpoint, not a substitute for the immutable dataset manifest.

## Evaluation cohort

The first bounded cohort is:

- COMI
- EGAL
- SWDY
- ETEL
- EAST
- TMGH
- PHDC
- FWRY
- EFID
- HRHO

Evaluation window: **2021-01-01 through 2025-12-31**.

Warm-up requirement: **252 prior trading observations** before the first evaluated decision date.

## Required evidence package

An accepted dataset version must contain, or point to preserved immutable artifacts containing:

1. Daily market OHLCV for the cohort and required warm-up period.
2. Point-in-time financial snapshots required by the production fundamental-analysis boundary.
3. Source/provider identity for every artifact.
4. Acquisition timestamp.
5. Source symbol to internal Stock identity mapping.
6. Coverage start/end and row counts.
7. Declared corporate-action convention.
8. Missing/suspension findings.
9. Symbol-change findings and evidence.
10. Exclusions and explicit reasons.
11. SHA-256 checksums.
12. Licensing/usage notes.

## Source status

### Primary market provenance — EGX

The Egyptian Exchange public site exposes market-watch data, listed-company information, disclosures, financial-statements areas, and index information. The site is therefore the designated primary provenance source where the required historical artifact can be obtained and preserved.

Current verification does **not** establish that the complete 2021–2025 daily OHLCV artifact for all ten symbols is publicly downloadable in a reproducible bulk form. This remains an acquisition task, not an assumption.

Reference: https://beta.egx.com.eg/en/market/market-watch

### Secondary market cross-check — Yahoo Finance

Yahoo Finance documents historical price data and supports custom historical ranges. Its current help documentation states that CSV download requires Yahoo Finance Gold and that some instruments do not expose downloads because of licensing restrictions. Yahoo also states that information supplied through the service must not be redistributed.

Therefore Yahoo is retained as a **secondary validation/cross-check source**, not as an automatically redistributed dataset source.

References:
- https://help.yahoo.com/kb/sln2311.html
- https://help.yahoo.com/kb/SLN2310.html

### Primary financial provenance — EGX disclosures / financial statements

Historical financial evidence must come from EGX-published disclosures or financial-statement publications where the publication/availability date can be established. A later-known value without a defensible point-in-time availability date is not eligible for Strategy v0 evaluation.



### Additional source research — 2026-09-24

A fresh external-source review was performed before treating any provider as an acquisition solution.

#### EGX.news — concrete paid historical-data candidate

EGX.news publicly advertises complete daily historical OHLCV records for EGX-listed stocks, with CSV delivery and history extending back to IPO. The service currently prices the full historical daily record per stock and therefore represents a concrete acquisition candidate rather than a free public evidence source.

This source is **not yet accepted** for the M61 dataset because provenance/licensing terms, exact ten-symbol coverage for 2021–2025, adjustment convention, and the corresponding point-in-time financial dataset still require validation.

Reference: https://www.egx.news/en/our-data

#### StockAnalysis — independent market cross-check candidate

StockAnalysis exposes EGX historical-price pages and identifies S&P Global Market Intelligence as the data source. The reviewed pages state that historical prices are adjusted for stock splits and are updated daily.

This is useful for independent market-data cross-checking, but the publicly surfaced pages are not sufficient evidence for the complete 2021–2025 ten-symbol dataset or for point-in-time financial availability. It is therefore **not accepted as the primary historical evidence source**.

Reference examples:
- https://stockanalysis.com/quote/egx/EGAL/history/
- https://stockanalysis.com/quote/egx/EAST/history/

#### Additional source research — 2026-09-25

##### Mansa Markets — API candidate

Mansa Markets currently documents an API with an EGX exchange history endpoint providing deep daily OHLCV history and states Egypt coverage back to 1995. The documentation describes the historical endpoint as a professional/API-key service.

This is a **strong technical acquisition candidate for market OHLCV**, because it explicitly exposes a programmatic history endpoint and a stated historical depth. It is **not accepted yet**: we still need to verify the actual EGX-10 cohort, exact response schema, symbol mapping, corporate-action convention, reproducibility, pricing/usage rights, and whether the service can provide or be paired with the required point-in-time financial snapshots.

Reference: https://mansamarkets.com/developers

##### ICE — institutional market-data candidate

ICE documents EGX historical and end-of-day data, including API/data-file delivery, with stated history from February 2012. It also documents normalized symbology and instrument status fields such as halted/suspended state.

This is a **credible institutional fallback/cross-check candidate**, but it is not yet evaluated for M61 because access, licensing, exact cohort coverage, delivery format, and acquisition cost have not been verified.

Reference: https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx

##### TradeGlob / TradingView route — technical candidate

A public TradeGlob project documents historical OHLCV retrieval for EGX symbols through TradingView, including date-range retrieval and multi-symbol support.

This is useful as a **technical cross-check candidate**, but it is not accepted as primary evidence because the documented route depends on TradingView access/authentication and the project itself does not establish redistribution rights, immutable raw-artifact provenance, or the required point-in-time financial dataset.

Reference: https://github.com/ibrasonic/TradeGlob

##### Research conclusion

The source landscape now contains multiple concrete acquisition paths rather than only website scraping candidates:

1. EGI public Feed API — documented historical endpoints; exact request/response contract still unverified.
2. Mubasher historical endpoint — historical implementation evidence exists, but current public availability is unresolved.
3. EGX.news — paid CSV historical dataset candidate.
4. Mansa Markets — programmatic historical OHLCV API candidate with stated Egypt depth.
5. ICE — institutional historical/EOD/API candidate.
6. TradeGlob/TradingView — technical cross-check candidate.

**None is accepted as the M61 dataset yet.** The next source-validation target is Mansa Markets because its published API contract most directly matches the production acquisition requirement; if access/terms fail, continue to EGX.news/ICE rather than weakening DEC-130.

## Acquisition acceptance procedure

For each source artifact:

1. Preserve the original source artifact without modification.
2. Record source URL/reference, acquisition timestamp, provider, and source symbol.
3. Record the mapping to the internal stock identity.
4. Record the artifact's raw checksum.
5. Transform only into the accepted M61 CSV schema.
6. Record transformation rules and corporate-action convention.
7. Compute the transformed artifact checksum.
8. Validate row count, ordering, duplicates, timestamps, decimal representation, and coverage.
9. Validate missing/suspension periods without forward-filling.
10. Validate financial available_at against every historical decision date.
11. Freeze the manifest and artifact checksums.
12. Only then authorize Strategy v0 evaluation against that dataset version.

## Verified software-side progress — 2026-10-09

The current `main` branch includes the following dataset-readiness improvements, with the latest main CI run passing:

- Candidate package builder preserves the source CSV bytes, records raw and normalized SHA-256 hashes, emits a manifest, and refuses to overwrite an existing candidate package.
- PR #284 — merged source-symbol integrity protection: when a vendor CSV contains a ticker/symbol column, every row must match the declared provider symbol; explicit aliases such as `COMI.CA` are recorded alongside the canonical COMI identity. CI passed.
- PR #285 — deduplicate case-insensitive source-symbol aliases so a canonical `COMI` mapping cannot be emitted twice; CI passed.
- PR #286 and #288 — fail closed on incomplete/inconsistent provider response metadata, including missing success/count/coverage fields, empty history, non-integer counts, and mismatched first/last dates; CI passed.
- PR #287 — date-only financial availability is conservatively eligible only from the following calendar date, avoiding same-day look-ahead when exact publication time is unknown; CI passed.
- PR #224 — closed without merge: the TradeGlob/TradingView probe would upload externally sourced raw price files as CI artifacts without verified retention/use rights. It is not an accepted acquisition path.
- Vendor CSV intake rejects malformed rows rather than silently skipping them into a package.
- Stable development stock identities exist for the bounded cohort; these are identity fixtures and do not imply that real market data has been acquired.
- The acceptance path checks internal COMI identity mapping, market/financial identity consistency, warm-up and evaluation coverage, corporate-action declaration, and explicit licensing attestation.
- PR #290 — merged strict CSV parsing at both the external evidence inspector and canonical dataset loader: duplicate headers, malformed quoting, non-canonical headers, and rows with missing/extra fields are rejected/reported rather than collapsed or allowed to crash the intake path. CI passed.
- PR #292 — aligned the pre-ingestion inspector with the annual acceptance rule: it reports missing evaluation years and does not reject a valid final trading session merely because it falls before December 31. CI passed.
- PR #293 — the COMI acceptance gate now requires daily (1d) observations and rejects intraday-only or mixed-timeframe artifacts. CI passed.
- PR #294 — the COMI vertical-slice gate now rejects extra market/financial stock identities rather than filtering COMI rows and silently ignoring other identities. CI passed.
- PR #295 — financial CSV candidate intake now rejects malformed quoting, duplicate/incorrect headers, and rows with missing/extra fields before writing a candidate package. CI passed.
- PR #296 — the M61 validator now rejects stale warm-up history and gaps over 31 calendar days inside the most recent 252 pre-evaluation observations. CI passed.
- PR #297 — the backtest runner separates loaded warm-up history from `evaluation_start_date`, prevents pre-evaluation signals, and uses Cairo-local session dates for point-in-time financial lookups. CI passed.
- PR #291 — merged a minimum annual evaluation-coverage gate: the COMI acceptance report now names missing years in 2021–2025 and does not require a market observation on the exact calendar date 2025-12-31. CI passed. This remains a minimum gate, not a substitute for an EGX session-calendar gap audit.
- The candidate packaging workflow and commands are documented in `docs/M61-EXTERNAL-CSV-EVIDENCE-INTAKE.md`.

These are software and workflow checks. They do **not** constitute a real dataset or demonstrate strategy profitability.

## Current blocker

The software-side dataset contract, manifest/integrity checks, loader, CSV inspector, candidate packager, source-symbol integrity checks, and deterministic fixtures are implemented. The remaining blocker is **real historical evidence acquisition with acceptable provenance and usage rights**. No accepted real COMI artifact or complete ten-symbol dataset has been verified in the repository as of 2026-10-09. The TradeGlob/TradingView CI probe was closed without merge because its source rights and raw-artifact retention were not established. Date-only financial `available_at` values are treated conservatively as eligible from the following calendar date; same-day use cannot be proven safe without an exact publication timestamp.

We cannot honestly close the dataset issue using generated fixtures, Yahoo data with unresolved retention rights, or unverified API schema assumptions. At least one real market-data artifact and point-in-time financial snapshots must be acquired under terms that permit the intended local storage and backtesting, then pass the acceptance gate.

We must not manufacture or silently substitute historical data merely to unblock the backtest. A dataset version becomes evaluable only after the evidence package above passes validation.

## Next executable step

Acquire the first real market and financial source artifacts for the ten-symbol cohort, preserve them outside Git when their size or licensing requires it, and produce the immutable M61 manifest. Then run the repository's existing historical-dataset validation before any Strategy v0 evaluation.

## Non-goals

This checkpoint does not:

- change Strategy v0;
- change backtest semantics;
- add ranking or optimization;
- add live trading;
- silently normalize corporate actions;
- create a new persistence model;
- claim full-EGX historical validity.


### Mansa Markets validation — 2026-09-25

The current Mansa API documentation materially strengthens this candidate:

- Exchange code is `EGX`.
- Historical endpoint is `GET /api/v1/markets/exchanges/{exchange_code}/stocks/{ticker}/history`.
- It accepts explicit `from` and `to` dates, plus ordering and a row limit.
- The documented response contains `date`, `open`, `high`, `low`, `close`, `adj_close`, and `volume`, with metadata including count and first/last dates.
- The documentation states Egypt history can reach back to 1995 and identifies EGX live/history sourcing as official EGX data.
- The documentation states historical access is on the Pro tier and that the Pro plan uses the `professional` tier token. We do not hard-code a price here because pricing/plan details can change.

This makes Mansa the first candidate with a documented API contract that maps directly onto the M61 market-data fields and bounded date-window requirement.

However, **Mansa is still NOT ACCEPTED**. The critical missing evidence is an authenticated extraction for the exact ten-symbol cohort, including row counts and gaps, symbol mappings, corporate-action/adjustment semantics, raw response preservation, deterministic replay, and confirmation that the purchased usage rights cover our intended backtest storage/use.

A direct unauthenticated API request from the available web access path was not retrievable, so no live EGAL response has been treated as evidence.

Reference: https://mansaapi.com/docs


### Mansa Markets follow-up — 2026-09-25

Official Mansa documentation adds two important acceptance constraints:

- The history endpoint is explicitly documented as **Pro plan and above**, even though the pricing page describes the Free tier more broadly as including “real-time + historical quotes.” For M61 we therefore treat the endpoint-level documentation as the authoritative capability boundary until Mansa confirms otherwise.
- Mansa's methodology states that historical prices are **as-published** and are not currently back-adjusted for splits or corporate actions. This is compatible with the M61 requirement to preserve source semantics, but it means the dataset must not be silently treated as split-adjusted. Any adjustment/total-return interpretation must be a separate, explicit transformation with its own provenance.
- Mansa's licensing page allows caching for application use only within tier-specific windows (up to 24 hours on Free/Starter, up to 7 days on Professional). It explicitly distinguishes this from building a stored copy of the dataset. Institutional licensing is the documented tier for raw-data redistribution. M61 therefore cannot assume that a long-lived immutable raw archive of API responses is permitted under ordinary application-tier terms.
- The terms also require API keys to remain confidential and prohibit circumventing authentication or tier restrictions.

**Acceptance consequence:** Mansa remains a strong **acquisition/provenance candidate**, but a production M61 dataset cannot be frozen from Mansa until we have both (a) authenticated extraction evidence for the exact cohort and (b) explicit confirmation that the selected license permits the required immutable archival/backtest use. If archival rights are not included, Mansa may still be useful as a transient acquisition/cross-check source while another source supplies the legally storable historical artifact.

References:
- https://mansaapi.com/docs
- https://mansaapi.com/methodology
- https://mansaapi.com/licensing
- https://mansaapi.com/terms


### Mansa documentation follow-up — 2026-09-25

The current official API docs clarify the access boundary:

- A free Standard API key can be issued instantly, but per-stock historical history is explicitly listed as Pro and above. Therefore creating a free key is useful for validating authentication and exchange/symbol discovery, but it is not evidence that the required historical endpoint is accessible.
- The history endpoint remains explicitly documented with from/to, order, and limit (maximum 20,000), and returns daily OHLCV plus `adj_close`, `price_unit`, and metadata such as count and first/last dates.
- Mansa also documents a separate Fundamentals Suite with fiscal-period financial figures and source-document URLs, but the documented coverage/example is not evidence that the required Egyptian point-in-time financial snapshots are available. We therefore keep financial acquisition as a separate acceptance gate.
- The licensing page explicitly says application caching is time-limited (up to 7 days on Professional) and distinguishes caching from building a stored copy of the provider dataset. Raw redistribution requires Institutional licensing. This does not automatically prohibit an internal research/backtest artifact, but the intended long-lived immutable M61 archive must be confirmed with Mansa rather than inferred from the API subscription.

**Updated execution decision:** first use the free key only for non-history discovery/authentication if available; do not purchase or integrate production history until Mansa confirms the historical tier and the permitted storage/use for an immutable research dataset. If that confirmation is not available, keep Mansa as a live/cross-check provider and acquire the frozen M61 artifact from a source whose storage rights are explicit.

References:
- https://mansaapi.com/docs
- https://mansaapi.com/licensing


### Mansa acquisition probe — 2026-09-28

The non-production Mansa acquisition probe has now been merged through PR #184 at `08c2fd14af5ce7144c85edbcbecd84f4cc9fd822`. Its implementation-head GitHub Actions run #2982 completed successfully. The probe remains deliberately non-accepting: it records provider/status/provenance metadata and can preserve raw responses only when explicitly requested.

Current official Mansa documentation now states that:
- the EGX history endpoint provides daily OHLCV deep history and Egypt coverage back to 1995;
- per-stock history is a Pro/Professional-tier capability;
- the current public Pro price is $50/month;
- historical prices are served as-published and are not back-adjusted for splits/corporate actions;
- Professional-tier caching is limited to 7 days, while raw redistribution requires Institutional licensing.

Accordingly, **the remaining Mansa blocker is no longer software support**. It is project entitlement + legally permissible archival/use of the required historical artifact, followed by authenticated extraction of the exact ten-symbol cohort. The repository must not freeze a long-lived Mansa raw archive merely from the API endpoint's availability.

References:
- https://mansaapi.com/docs
- https://mansaapi.com/licensing
- https://mansaapi.com/methodology
- https://mansaapi.com/terms


## No-budget execution update — 2026-10-09

**Owner constraint:** no payment or paid subscription is available. Do not block M61 progress on EGX.news, Mansa Pro, ICE, or any other paid source.

The paid-source candidates above are retained as historical research notes only; they are not the next action. The active path is now documented in [M61 No-Cost Data Acquisition](M61-NO-COST-DATA-ACQUISITION.md).

1. Probe the ten Yahoo `.CA` ticker candidates using `tools/m61_free_market_probe.py`. This is a no-cost diagnostic path only. It must record actual response status, source timezone, coverage, raw-response checksum, adjustment fields, and validation findings; it must never auto-accept the source.
2. Investigate the public EGID/EGX feed as the next no-cost alternative only after its exact request/response contract and historical range can be verified.
3. Build point-in-time financial evidence from dated issuer/EGX disclosure documents without inventing availability dates. The current financial source gate remains separate and open.
4. If the free market probe returns incomplete coverage or is blocked, record that result and continue testing a different free candidate. Do not silently substitute fixtures or synthesize bars.

**Current status remains NOT ACCEPTED.** This update changes the acquisition strategy to respect the no-payment constraint; it does not claim that the free probe has already run successfully, that Yahoo terms permit long-term storage, or that the ten-symbol market-plus-financial dataset is complete.


## EGID contract probe implementation — 2026-10-09

A contract-only diagnostic, `tools/m61_egid_contract_probe.py`, now inspects the public Swagger/OpenAPI document and reports history/chart/token operations, declared request parameters, DTO schemas, and security schemes. It does not call data endpoints, authenticate, or download price data. It supports OpenAPI 3 and Swagger 2 metadata.

This is a preparation step, not a verified EGID acquisition. The tool must be run in an environment with network access; the actual history request, response semantics, free-access boundary, historical depth, and retention rights remain unverified. No EGID market data has been accepted.


## No-cost probe outcome — 2026-10-09

The first live no-cost probe returned HTTP 200 for all ten Yahoo `.CA` candidates and showed historical date ranges spanning 2019–2025. It did **not** produce acceptable evidence: every symbol response reported `instrumentType=MUTUALFUND` rather than `EQUITY`, and OHLCV validation found hundreds of row-level integrity/null findings per ticker. FWRY's returned history began on 2019-08-14; the others reported 2019-01-01. The run was metadata-only and did not preserve raw price data.

Reference: [M61 live probe run #37920812142](https://github.com/palestiny/egx-stock-analyzer/actions/runs/37920812142).

**Decision:** do not use these Yahoo results for Strategy v0 or mark the dataset accepted. The next no-cost target is to verify the public EGID/EGX history contract and then test one symbol. Point-in-time financial evidence remains independently open.

## No-cost source decision — live verification, 2026-10-09

- Yahoo .CA endpoints responded, but all ten reported MUTUALFUND metadata and each produced hundreds of OHLCV integrity/null findings. Rejected for M61; see [run #37920812142](https://github.com/palestiny/egx-stock-analyzer/actions/runs/37920812142).
- EGID's public Swagger declares Bearer security for history endpoints. A single unauthenticated COMI history request returned HTTP 401. No authentication bypass was attempted; no free account or archival entitlement is verified.
- StockAnalysis explicitly prohibits automated scraping/bulk collection and says its display licenses do not grant programmatic redistribution or competing-database rights: https://stockanalysis.com/terms-of-use/
- EGXAPI advertises a free service, but its public legal page identifies the terms as a design draft with placeholder text: https://egxapi.com/legal/. It is not accepted until binding terms and data rights are verifiable.
- Paid sources remain excluded because no payment is possible.

Operational next step: intake a real market CSV from a source already accessible to the owner only if its terms permit local historical research/storage. Use tools/m61_vendor_csv_evidence_inspector.py and tools/m61_build_candidate_dataset.py for immutable evidence packaging. If no eligible CSV is available, record the dataset blocker rather than generating synthetic rows. Point-in-time financial coverage remains independently unresolved.


## TradingView-backed cross-check — 2026-10-09

A one-time non-persisting check returned 1,556–1,700 daily bars per M61 symbol for 2019–2025 with no basic OHLC consistency failures or missing/non-numeric OHLC values. However, TradingView's current terms prohibit automated data collection and non-display/algorithmic use absent separate permission. No raw data was retained. Do not treat this as an accepted or repeatable source for M61.


## Test-only unblocker — 2026-10-09

A deterministic synthetic dataset generator is available at `tools/m61_generate_test_dataset.py`, documented in [M61 Test Dataset Bootstrap](M61-TEST-DATASET-BOOTSTRAP.md). It generates schema-v3 artifacts for the ten-symbol cohort and lets engineering exercise dataset loading, analysis, and backtesting plumbing without waiting for source acquisition.

This does **not** change the status above: the generated prices and financial values are synthetic placeholders, not accepted EGX market data, and must not be used for strategy evaluation or investment decisions.


## Bounded Yahoo chart probe — 2026-10-09

A metadata-only GitHub Actions probe completed for the fixed ten-symbol cohort. All ten .CA chart requests returned HTTP 200 with Africa/Cairo timezone metadata and observations extending through 2025-12-31. Nine symbols returned 1,716 daily rows each; FWRY returned 1,555 rows and began on 2019-08-14. The probe reported 340–457 validation findings per symbol, including repeated OHLC high/low relationship violations and null/invalid values. It did not preserve or publish source price rows.

This confirms technical endpoint reachability only. The candidate is **rejected for Strategy v0 evaluation at this stage**: the observed validation findings are unresolved, source terms and long-term storage rights are unverified, and the probe contains no point-in-time financial snapshots. Do not silently repair these observations or infer that a successful HTTP response establishes dataset quality.

The end-to-end engineering path was also exercised using the explicitly synthetic generator: schema-v3 manifest/checksums and both artifacts were loaded, and the production HistoricalDatasetBacktestRunner completed two deterministic COMI runs with 2019–2020 warm-up and 2021 evaluation isolation. CI passed. This validates software plumbing only; it is not real-EGX backtest evidence.
