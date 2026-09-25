# M61 — EGI Egypt API Source Validation

**Status:** Candidate under validation — **not accepted as M61 evidence**
**Date:** 2026-09-24
**Related decision:** DEC-130
**Candidate:** EGI Egypt Ticker/Feed API

## Purpose

Record the result of validating the publicly documented EGI Egypt Feed API as a possible acquisition source for the bounded M61 historical market-data cohort.

## Observed public API surface

The provider's public Swagger UI documents:

- `POST /api/Feed/GetSymbolsChartByDateRange`
- `POST /api/Feed/GetAllSymbolsChartByDateRange`
- `POST /api/Feed/GetSymbolHistory`
- `GET /api/Feed/GetSymbolHistories`
- `GET /api/Feed/GetSymbolChart`

The same API surface also exposes market-watch, symbol statistics, free-float, and related endpoints.

Reference:
https://ticker.egidegypt.com/index.html

## What this proves

The public documentation establishes that the provider exposes date-range chart/history operations.

It does **not** by itself prove:

1. Complete 2021-01-01 through 2025-12-31 coverage for all ten M61 symbols.
2. The required 252-observation warm-up coverage.
3. Stable source-symbol mappings for the complete evaluation period.
4. Exact OHLCV field semantics and units for every returned observation.
5. Corporate-action/adjustment semantics.
6. Treatment of suspensions and missing observations.
7. Deterministic replay of an identical historical extraction.
8. Historical financial statements with defensible point-in-time `available_at` semantics.
9. Licensing/usage rights for preserving and using the extracted dataset for backtesting.
10. A preserved raw artifact that can be independently audited.

## M61 acceptance status

**NOT ACCEPTED.**

The API is a concrete acquisition candidate and should be tested before adopting another source, but its existence is not sufficient evidence for DEC-130 acceptance.

No production/backtest dataset may be populated from this source until the acceptance checklist is completed.

## Validation sequence

1. Execute a bounded read-only extraction for one symbol and a narrow historical range.
2. Record the exact request payload, response shape, acquisition timestamp, and source symbol.
3. Confirm whether OHLCV is present and identify each field's semantics.
4. Expand to the ten-symbol cohort.
5. Measure coverage and gaps for 2021-2025 plus 252-observation warm-up.
6. Investigate symbol changes, suspensions, and corporate actions.
7. Determine whether repeated extraction is deterministic.
8. Obtain and record applicable usage/licensing terms.
9. Validate market observations against an independent source.
10. Validate financial point-in-time data separately; do not infer it from market-history endpoints.
11. Preserve raw artifacts and calculate SHA-256 checksums.
12. Only then consider an immutable M61 dataset manifest.

## Current blocker

The remaining blocker is **evidence**, not software implementation.

The repository already has the dataset contract, integrity validation, loader, and deterministic fixtures. The next useful execution step is a controlled source probe that produces evidence without silently promoting the provider into the accepted dataset boundary.

## Guardrail

Do not manufacture missing rows, forward-fill suspensions, silently adjust prices, or substitute later-known financial values merely to make the backtest executable.


## Follow-up verification — 2026-09-25

A fresh web verification still shows the EGI Swagger UI exposing the same historical-data surface, including:

- `POST /api/Feed/GetSymbolsChartByDateRange`
- `POST /api/Feed/GetAllSymbolsChartByDateRange`
- `POST /api/Feed/GetSymbolHistory`
- `GET /api/Feed/GetSymbolHistories`

The Swagger index also lists the schemas `Period`, `DateInterval`, `HistoryReqDto`, `SymbolChartRequest`, and `SymbolChartByDateRequest`. This confirms that request/response models exist in the published OpenAPI surface, but the crawler-accessible Swagger page did not expose the individual schema properties. The direct `/swagger/v1/swagger.json` resource was also not retrievable through the available web access path.

Therefore, the exact POST payload and returned JSON contract remain **UNVERIFIED**. No claim is made that an EGAL extraction has succeeded.

An independent recent codebase was also found using a different Mubasher historical endpoint (`/api/symbol/a/EGX-{symbol}/history?type=full`) and mapping OHLCV fields, but that evidence concerns Mubasher rather than EGI and does not establish EGI compatibility.

**Decision unchanged: EGI remains a candidate, not an accepted M61 historical dataset source.**

References:
- EGI public Swagger index: https://ticker.egidegypt.com/index.html
- EGID describes itself as a wholly owned EGX subsidiary and authorized EGX market-data provider: https://www.linkedin.com/company/egid
