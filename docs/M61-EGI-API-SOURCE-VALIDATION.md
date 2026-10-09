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


## Live OpenAPI verification — 2026-10-09

The public OpenAPI document was retrieved successfully from GitHub Actions run [#37967688648](https://github.com/palestiny/egx-stock-analyzer/actions/runs/37967688648). It declares OpenAPI 3.0.1 and confirms the following request contracts:

- `POST /api/Settings/GetToken` accepts an `AuthenticationParameterReqDto` with `Username` and `Password`.
- `POST /api/Feed/GetSymbolHistory` and `POST /api/DelayedFeed/getSymbolHistory` accept `HistoryReqDto` with `SymbolCode`, `FromDate`, `ToDate`, `Skip`, and `Take`.
- `GET /api/Feed/GetSymbolHistories` and `GET /api/DelayedFeed/GetSymbolHistories` expose corresponding query parameters.
- `POST /api/Feed/GetSymbolsChartByDateRange` and `POST /api/Feed/GetAllSymbolsChartByDateRange` accept `SymbolChartByDateRequest` with `SYMBOLS_CODE`, `StartTime`, `EndTime`, and `period`.

Important limitations discovered in the live contract:

1. The OpenAPI security metadata declares a Bearer scheme on the history and token operations. The token endpoint's own unauthenticated behavior is therefore not established by the schema alone.
2. The history operations declare HTTP 200 but do not describe response DTO schemas. We cannot safely map returned fields or infer daily-vs-intraday semantics from the contract.
3. The earlier unauthenticated COMI history request returned HTTP 401. No credential guessing or authentication bypass was attempted.
4. The contract-only workflow fetched metadata only. It did not request or preserve price rows, and it does not verify source licensing, historical depth, completeness, or point-in-time financial availability.

**Decision remains NOT ACCEPTED.** The next live step requires an authorized EGID account/credential issued by the provider or a real provider-delivered CSV whose terms permit local historical research. With authorized access, perform a bounded COMI-only response-shape/coverage probe first, without persisting prices until storage/use rights are verified. Do not build a production adapter against guessed response fields.
