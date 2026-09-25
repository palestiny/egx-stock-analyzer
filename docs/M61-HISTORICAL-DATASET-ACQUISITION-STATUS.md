# M61 — Historical Dataset Acquisition Status

**Status:** Acquisition boundary accepted; real dataset not yet accepted for evaluation.  
**Decision:** DEC-130  
**Updated:** 2026-09-24 — source research refreshed

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

## Current blocker

The software-side dataset contract, manifest/integrity checks, loader, and deterministic fixtures are already implemented. The remaining blocker is **real historical evidence acquisition with acceptable provenance and usage rights**.

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
- The documentation states historical access is on the Pro tier; current pricing documentation lists Pro at $50/month.
- The service states commercial redistribution requires the Professional tier.

This makes Mansa the first candidate with a documented API contract that maps directly onto the M61 market-data fields and bounded date-window requirement.

However, **Mansa is still NOT ACCEPTED**. The critical missing evidence is an authenticated extraction for the exact ten-symbol cohort, including row counts and gaps, symbol mappings, corporate-action/adjustment semantics, raw response preservation, deterministic replay, and confirmation that the purchased usage rights cover our intended backtest storage/use.

A direct unauthenticated API request from the available web access path was not retrievable, so no live EGAL response has been treated as evidence.

Reference: https://mansaapi.com/docs


### Mansa Markets follow-up — 2026-09-25

Official Mansa documentation adds two important acceptance constraints:

- The history endpoint is explicitly documented as **Pro plan and above**, even though the pricing page describes the Free tier more broadly as including “real-time + historical quotes.” For M61 we therefore treat the endpoint-level documentation as the authoritative capability boundary until Mansa confirms otherwise.
- Mansa's methodology states that historical prices are **as-published** and are not currently back-adjusted for splits or corporate actions. This is compatible with the M61 requirement to preserve source semantics, but it means the dataset must not be silently treated as split-adjusted. Any adjustment/total-return interpretation must be a separate, explicit transformation with its own provenance.
- Mansa's licensing page allows caching for application use only within tier-specific windows (up to 24 hours on Free/Starter, up to 7 days on Professional). It distinguishes this from building a stored copy of the dataset. Institutional licensing is the documented tier for raw-data redistribution. M61 therefore cannot assume that a long-lived immutable raw archive of API responses is permitted under ordinary application-tier terms.
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
- The history endpoint remains explicitly documented with from/to, order, and limit (maximum 20,000), and returns daily OHLCV plus price_unit and metadata such as count and first/last dates.
- Mansa also documents a separate Fundamentals Suite with fiscal-period financial figures and source-document URLs, but the documented coverage is not evidence that the required Egyptian point-in-time financial snapshots are available. We therefore keep financial acquisition as a separate acceptance gate.
- The licensing page explicitly says application caching is time-limited (up to 7 days on Professional) and distinguishes caching from building a stored copy of the provider dataset. Raw redistribution requires Institutional licensing. This does not automatically prohibit an internal research/backtest artifact, but the intended long-lived immutable M61 archive must be confirmed with Mansa rather than inferred from the API subscription.

**Updated execution decision:** first use the free key only for non-history discovery/authentication if available; do not purchase or integrate production history until Mansa confirms the historical tier and the permitted storage/use for an immutable research dataset. If that confirmation is not available, keep Mansa as a live/cross-check provider and acquire the frozen M61 artifact from a source whose storage rights are explicit.

References:
- https://mansaapi.com/docs
- https://mansaapi.com/licensing
