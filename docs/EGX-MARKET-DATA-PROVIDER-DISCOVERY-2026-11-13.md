# EGX Market-Data Provider Discovery — 2026-11-13

**Status:** Preliminary desk research — no provider approved; no credentials or contractual evidence received.
**Owner decision:** Begin provider discovery from zero.
**Related gate:** `docs/MARKET-DATA-PROVIDER-RELIABILITY-DESIGN-GATE.md`
**Scope:** Daily EGX OHLCV source eligibility for opportunity lifecycle monitoring, plus commercial use in a potentially subscriber-facing product.

## 1. Executive result

**Primary provider to contact: Egypt for Information Dissemination (EGID).**

EGID's own website states that it is a wholly owned subsidiary of the Egyptian Exchange (EGX) and the sole authorized EGX market-data provider. Its Market Data page describes real-time Level 1/Level 2 feeds, 15-minute delayed data, historical prices, and end-of-day reports. EGID is therefore the strongest source candidate discovered so far, but it is **not yet accepted**: the public material does not establish the precise daily-bar finality signal, correction/revision contract, or our intended commercial rights.

Official references:
- EGID home / ownership and authorized-provider statement: https://egidegypt.com/index.html
- EGID Market Data product description: https://egidegypt.com/market-data.html
- EGID company background: https://egidegypt.com/who-we-are.html
- EGID public feed API documentation UI: https://ticker.egidegypt.com/index.html
- EGID contact page: https://egidegypt.com/contact-us.html

EGID's public API documentation lists endpoints under both `Feed` and `DelayedFeed`, including `GetSymbolHistory`, `GetSymbolHistories`, `GetSymbolGraphData`, `GetMarketStatus`, and `GetEGXMarketWatch`. This demonstrates a documented API surface, not the required provider guarantee. The public documentation currently does not establish a machine-verifiable EOD finality attestation or a stable correction/revision identifier.

## 2. Candidate comparison

| Candidate | Verified public evidence | Lifecycle finality / corrections | Commercial boundary | Current disposition |
|---|---|---|---|---|
| **EGID** | EGX-owned subsidiary; says it is the sole authorized EGX data provider; offers historical prices, EOD reports, real-time Level 1/2, and 15-minute delayed feed. Public API UI lists symbol-history and market-status endpoints. | Not proven from public pages/API UI. Must obtain EOD publication/finality semantics, revision/correction process, stable candle identity, timestamps and sample payloads. | Need written permission for non-display algorithmic use, persistent storage, derived analytics, subscriber-facing display and/or redistribution. | **Priority 1 — contact and request a technical/commercial pack. Not approved yet.** |
| **ICE Data Services** | ICE's EGX catalog explicitly lists real-time, delayed, end-of-day and historical data, equities/indices, and delivery through ICE Data API, Files, Consolidated Feed and Consolidated History. | Strong enterprise candidate, but exact EGX daily-bar finality and correction SLA must be confirmed contractually. | Enterprise licensing and any derived-data/display/redistribution rights need a quote and written agreement. | **Priority 2 — request quote/specification if EGID cannot meet the contract.** |
| **DataCedar** | EGX market page advertises 260 listings and daily/intraday bars through REST API. Docs describe daily bars as fetched separately from upstream and say data is for research/screening/backtesting, not a consolidated exchange feed or suitable for best-execution/regulatory records. | Public API schema documents OHLCV and timestamps but does not document an explicit provider-finality attestation or stable correction/revision contract. | Terms grant internal research, analysis, model development, backtesting and trading use; prohibit raw/substantially similar redistribution and third-party access absent separate written agreement. | **Research-only fallback; not acceptable for subscriber-facing raw-data distribution under published default terms. Not approved for lifecycle transitions.** |
| **EGXAPI** | Public site markets real-time/historical EGX data and REST/WebSocket trading APIs, but labels itself a developer preview. | Public claims are not a finality/correction contract. | Its legal page explicitly labels the Terms of Service a design draft with placeholder body text awaiting counsel. | **Do not rely on it until legal terms, operator identity, exchange data authorization and technical contract are verifiable.** |
| **EGX.news** | Public site markets EGX daily historical and 1-minute datasets and a RapidAPI live feed. | Public marketing does not establish authoritative source lineage, finality, correction/revision behavior or operational SLA. | Must verify data source authorization and commercial reuse/redistribution rights in writing. | **Unverified alternative; not shortlisted ahead of EGID/ICE.** |

Additional references:
- ICE EGX catalog: https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx
- DataCedar EGX coverage: https://datacedar.com/markets/egx
- DataCedar API docs: https://datacedar.com/docs
- DataCedar Terms: https://datacedar.com/terms
- EGXAPI pricing/product claims: https://www.egxapi.com/pricing/
- EGXAPI legal page: https://www.egxapi.com/legal/
- EGX.news data offer: https://egx.news/en/our-data

## 3. EGID due-diligence request

Contact:
- Market Data Department: marketdata@egidegypt.com
- Commercial Department: commercial@egidegypt.com
- Telephone: +20 2 2614 5000

Request the following in writing before implementation or payment:

### Technical contract
1. A daily EOD OHLCV API/feed product for all EGX equities and required indices; clarify raw versus adjusted prices and corporate-action handling.
2. Exact definition of a completed/final daily bar: when it becomes final, what exchange/provider event establishes finality, and whether the API exposes a finality/status field or signed/traceable publication event.
3. Whether a published EOD bar can later be corrected; correction windows, notification mechanism, revision IDs/version numbers, historical restatement policy, and audit availability.
4. Timestamp semantics: session date, native timezone (expected EGX local time), source publication timestamp, and retrieval timestamp.
5. Sample payloads for a normal session, holiday/closure, halted security, no-trade security, corrected bar, and delayed publication.
6. API authentication, rate limits, service availability/SLA, maintenance notices, historical depth, symbol master and instrument lifecycle mapping.
7. Whether historical EOD reports and API bars are generated from the same authoritative source and whether they reconcile.

### Written licensing terms
1. Non-display use by our server-side analysis and automated lifecycle-monitoring engine.
2. Storage and retention of raw OHLCV, provider metadata, and audit evidence.
3. Display of prices/charts to authenticated subscribers in a paid product.
4. Redistribution restrictions, derived-data rules, and whether scores/alerts/technical levels are permitted derived outputs.
5. Any per-user, per-device, per-display, per-symbol, per-request or redistribution fees.
6. Whether EGID can provide a written authorization covering the exact intended EGX Stock Analyzer use case.

## 4. Acceptance gate — no shortcuts

EGID (or another vendor) is accepted for lifecycle automation only after all of these are evidenced:

- [ ] Written confirmation of the data source's authority and the vendor's right to supply this dataset.
- [ ] Contractual permission for our intended internal/non-display use and any subscriber-facing use actually planned.
- [ ] Documented daily EOD completion/finality semantics; local waiting time alone is not evidence.
- [ ] Documented correction/revision process and stable identity, or an owner-approved weaker reconciliation policy with explicit limitations.
- [ ] Correct EGX instrument mapping, session date and timezone semantics.
- [ ] Representative payloads and successful contract tests against a test credential.
- [ ] Historical and current bars reconcile against EGID EOD reports or another authoritative reference sample.
- [ ] Failure, late publication, correction, holiday, halt and no-trade scenarios tested fail-closed.
- [ ] Provider contract/version and provenance persisted with every eligible observation.

Until then:
- Keep automatic lifecycle monitoring disabled.
- Do not mark `is_final=True` based only on elapsed time or a local buffer.
- Do not wire a provider merely because an endpoint returns OHLC values.
- Keep the PR Draft and unmerged; provider discovery is not provider approval.

## 5. Next action

The next external dependency is a response from EGID Market Data / Commercial with the technical pack, sample EOD payloads, and a written licensing proposal. If EGID cannot provide the required guarantees or rights, request an ICE quote/specification and compare the written contracts. No provider-specific adapter should be implemented before that evidence is received.
