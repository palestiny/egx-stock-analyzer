# M61 — EGI Historical Feed Contract Verification

**Status:** PARTIALLY VERIFIED — endpoint inventory confirmed; request/response contract not yet proven.
**Decision boundary:** DEC-130 / Issue #186
**Updated:** 2026-09-28

## Purpose

Record exactly what has been verified about the public EGI historical market-data feed without treating endpoint existence as proof of an acquisition contract.

M61 requires a reproducible historical OHLCV artifact for:

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

Evaluation window: 2021-01-01 through 2025-12-31, with at least 252 prior trading observations for warm-up.

## Verified endpoint inventory

The public EGI Swagger UI currently documents the following historical/chart endpoints:

- `POST /api/Feed/GetSymbolHistory`
- `POST /api/Feed/GetSymbolsChartByDateRange`
- `POST /api/Feed/GetAllSymbolsChartByDateRange`
- `GET /api/Feed/GetSymbolHistories`
- `GET /api/DelayedFeed/getSymbolGraphData`
- `GET /api/DelayedFeed/getSymbolTrades`
- `GET /api/DelayedFeed/getTodaySymbolTrades`

The same feed documentation also exposes market-watch and market-status endpoints that may be useful for symbol identity and session-state cross-checking.

**Source:** EGI public Swagger UI: https://ticker.egidegypt.com/index.html

## What is proven

1. A public Swagger UI exists for the EGI feed.
2. The feed exposes explicit historical-symbol and date-range endpoint names.
3. The documented endpoint family is technically aligned with the M61 need for historical market data.
4. Endpoint existence is independently visible without assuming a provider-specific adapter implementation.

## What is NOT proven

The following remain unverified and therefore must not be encoded as production assumptions:

1. Request body schema for `GetSymbolHistory`.
2. Request body schema for date-range endpoints.
3. Authentication/token requirements for the historical endpoints.
4. Exact response JSON schema and field names.
5. Date/time format and timezone semantics.
6. OHLCV numeric types and unit/scale semantics.
7. Maximum date range, pagination, or truncation behavior.
8. Symbol identity format and historical symbol changes.
9. Split/corporate-action adjustment semantics.
10. Reproducible ten-symbol extraction behavior.
11. Permission to preserve raw responses as a long-lived immutable research artifact.

## Acceptance rule

**Endpoint existence is not an acquisition contract.**

No EGI-specific transformation or production adapter may be promoted into the M61 dataset pipeline until the request/response contract is verified from the actual OpenAPI schema or a permitted live request.

## Current acquisition consequence

EGI remains the primary provenance candidate because it is directly associated with the Egyptian market feed, but M61 remains blocked on contract verification.

The correct next action is not to guess the request payload or scrape undocumented response fields. Instead:

1. obtain the OpenAPI document or an authorized live request;
2. capture the exact request and response schema;
3. probe one symbol first;
4. verify date coverage and field semantics;
5. expand to the ten-symbol cohort only after the single-symbol contract is deterministic;
6. record licensing/storage constraints before freezing raw artifacts.

## Source-selection boundary

This checkpoint does not reject alternative market-data candidates.

Current candidates remain:

- EGI public feed — provenance-first candidate; contract verification pending.
- Mansa Markets — documented historical API candidate; authenticated extraction and storage rights pending.
- EGX.news — paid historical CSV candidate; licensing and exact cohort validation pending.
- ICE — institutional historical/EOD/API candidate; access, licensing and cost validation pending.

The M61 acceptance gate requires evidence, not merely a technically plausible API.

## Non-goals

This checkpoint does not:

- implement a provider adapter;
- alter the canonical M61 market schema;
- alter Strategy v0;
- infer adjustment semantics;
- create or accept synthetic historical data;
- claim that EGI can already supply the frozen M61 dataset.
