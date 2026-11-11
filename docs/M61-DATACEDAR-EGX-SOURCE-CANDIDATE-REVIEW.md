# M61 — DataCedar EGX Source Candidate Review

**Status:** Candidate under validation — **not accepted as M61 evidence**  
**Reviewed:** 2026-11-11  
**Related gates:** DEC-130, DEC-128, M61 Historical Source Acceptance Matrix  
**Candidate:** DataCedar v3 API — EGX venue

## Executive finding

DataCedar is a newly identified, technically concrete candidate for a **bounded, no-cost recent-history diagnostic**. Its current public documentation describes an EGX symbol registry, daily OHLCV bars, raw and adjusted series, symbol/range endpoints, and a free Explorer plan.

It is **not an accepted source** and cannot currently satisfy the existing M61 target of 2021–2025 market history plus the required 252-observation warm-up:

- Explorer currently exposes one year of daily history, seven days of minute history, and up to three symbols per request.
- The EGX coverage page claims 260 listings, but also reports that zero of the 260 EGX pages currently carry enough traded history to be included in the sitemap. This is a coverage/maturity warning, not proof that every API series is empty.
- The provider's terms permit reasonable query results for internal research, analysis, model development, and backtesting, but prohibit systematic acquisition or mirroring of a substantial portion of its archive and do not grant bulk/offline/full-archive delivery rights.
- DataCedar states that it is independent and not affiliated with or endorsed by an exchange; underlying third-party source rights continue to apply.

No API key was available during this review. No authenticated request was made, no price rows were downloaded or persisted, and no source has been selected.

## Public contract observed

### EGX coverage and identity

The EGX market page states:

- 260 EGX listings (260 stocks, zero ETFs) are represented in its registry.
- Daily bars are claimed back to each symbol's first sourced session.
- Minute history begins when capture started and is not backfilled.
- EGX symbols use the venue's own ticker, with exchange-qualified IDs in the API.
- The page reports **0 of 260** symbol pages as having enough traded history to qualify for the sitemap.

References:
- https://datacedar.com/markets/egx
- https://datacedar.com/docs

The listing count and marketing coverage statement must not be treated as verified per-symbol history. The sitemap qualification count is an explicit reason to measure actual returned coverage before any research use.

### API contract

The current v3 documentation describes:

- `GET /v3/exchanges`, `GET /v3/exchanges/{code}/symbols`, `GET /v3/stocks/assets`, and `GET /v3/search` for exchange and symbol discovery.
- `GET /v3/stocks/{sid}/bars/range` for first bar, last bar, and count by timeframe.
- `GET /v3/stocks/{sid}/bars` and `GET /v3/stocks/bars` for single-symbol and bounded multi-symbol history.
- Daily adjustment values `raw`, `split`, `dividend`, and `all`.
- Cursor pagination, with a documented maximum of 50,000 daily bars per page.
- Response metadata including request timestamp, symbol identity, exchange, currency, timezone, and attribution.
- API-key authentication using Bearer or X-API-Key.

The documentation says daily bars are fetched separately from upstream and may differ in prices and volume. It describes the data as source-attributed research bars, not a consolidated exchange feed and not suitable for best-execution reporting or regulatory record keeping.

References:
- https://datacedar.com/docs
- https://datacedar.com/markets/egx

## Current plan limits

The current pricing page and API reference agree on these Explorer limits:

| Capability | Explorer |
|---|---:|
| Price | Free; no payment card |
| Daily history | 1 year |
| Minute history | 7 days |
| Symbols per request | 3 |
| General REST admission | 1 request/second |
| Corporate-action/adjusted-series feature | Pricing matrix says raw close only |

Reference: https://datacedar.com/pricing

A previous search-index snapshot exposed an older seven-day daily-history description. The current pricing page and current API reference both state **one year of daily bars**, so this review uses the live page content rather than that stale index result.

The one-year daily window remains insufficient for M61's 2021–2025 evaluation period plus warm-up. Do not purchase a paid plan or assume paid history is available.

## Usage rights and restrictions

The DataCedar Terms of Service, last updated 2026-09-01, state that:

- The service is a query-access subscription; access is licensed, not sold.
- Section 4 permits internal research, analysis, model development, backtesting, and trading, and allows retention of reasonable query results and derived analytics needed for those activities.
- Section 5 prohibits systematically acquiring, mirroring, reconstructing, or maintaining a substitute for a substantial portion of the archive or live feed.
- The terms do not grant bulk, offline, object-storage, database-replication, or full-archive delivery rights unless separately agreed in writing.
- Third-party source rights and conditions continue to apply.

Reference: https://datacedar.com/terms

**Interpretation boundary:** a narrowly scoped research query may fit the stated internal-use grant, but the exact proposed ten-symbol dataset, retention duration, and any intended product/commercial use have not been confirmed with the provider or underlying rights holders. Do not use the API to build a broad local mirror or substitute archive. Obtain written clarification before retaining any substantial dataset or using it in a distributed/commercial product.

## M61 acceptance assessment

| Requirement | Current evidence | Status |
|---|---|---|
| EGX instrument identity | Exchange-qualified symbol IDs and EGX registry documented | Candidate only |
| Actual ten-symbol coverage | No authenticated requests or per-symbol range reports | Not verified |
| 2021–2025 plus 252-session warm-up | Explorer daily history is limited to one year | Not satisfied on free plan |
| Raw OHLCV semantics and units | API schema documents OHLC, volume, currency and adjustment field; EGX-specific source semantics not independently verified | Partial |
| Corporate-action treatment | Raw/split/dividend/all modes documented; free-plan feature matrix says raw close only | Clarification required |
| Source lineage and correction policy | Source attribution is described generally; EGX-specific upstream lineage and correction behavior not established | Not verified |
| Session calendar and missing bars | EGX page states Sunday–Thursday and Africa/Cairo; actual completeness and suspension semantics not verified | Not verified |
| Retention and research rights | Internal research/backtesting and reasonable query retention are described, subject to restrictions and upstream rights | Partial; clarify scope |
| Immutable artifact and checksum | No data artifact acquired | Not started |
| Point-in-time financial snapshots | Not provided by this market-bars API contract | Separate blocker |

**Decision: NOT ACCEPTED.** DataCedar may be considered for a bounded recent-history diagnostic only after an API key is deliberately provisioned and the query/retention scope is confirmed. It must not replace EGID as the preferred authorized-source contact or be promoted to the M61 accepted dataset.

## Safe next diagnostic — gated on an owner-provided API key

If a free key is made available, perform only this bounded sequence:

1. Store the key as a GitHub Actions secret or local environment variable; never commit it, print it, or place it in a report.
2. Query the EGX exchange registry and resolve COMI to its canonical exchange-qualified symbol ID.
3. Call the symbol's daily `bars/range` endpoint first. Record only response metadata, first/last timestamps, and count.
4. If the range is within Explorer limits and the permitted scope is confirmed, request at most one bounded recent-history COMI sample. Preserve exact response bytes only if the applicable terms and source rights permit it.
5. Validate schema, ordering, duplicates, finite numeric values, OHLC geometry, volume type, timezone/session-date mapping, adjustment mode, and pagination.
6. Compare a small set of overlapping dates with independent evidence where permitted. A matching close alone is not enough.
7. Record all gaps and failures. Do not infer missing sessions, forward-fill, repair values, or change the canonical daily-history CSV.
8. Stop after the bounded diagnostic. Do not fan out across the ten-symbol cohort or expand pagination into an archive collection without a separate rights and scope review.

A successful HTTP response, range count, or structurally valid OHLC row is not source authentication and does not satisfy DEC-130.

## Outstanding questions for DataCedar

Before a larger research extraction, obtain written answers to:

1. Which upstream source(s) supply EGX daily bars, and can source lineage be identified per symbol/observation?
2. What exactly does the Explorer feature label **raw close only** permit or omit for OHLC and corporate-action fields?
3. Are the displayed EGX OHLC and volume values raw, split-adjusted, dividend-adjusted, or mixed? What are volume units?
4. What correction/revision policy applies, and can prior versions or as-of snapshots be reproduced?
5. Does the current 260-listing EGX registry have actual daily bars for each M61 symbol, and what are the first/last dates and counts?
6. Does the internal research/backtesting permission explicitly cover retaining the bounded ten-symbol sample and derived research outputs for the project's intended use?
7. Do any underlying EGX/source-provider terms impose additional restrictions beyond DataCedar's own terms?

## Guardrails

- No provider selection, production adapter, scheduled ingestion, canonical CSV modification, or M61 eligibility promotion is authorized by this review.
- No paid plan or paid data package is authorized.
- Do not treat public website pages as a license to scrape them; use only the documented API under its access and use terms.
- Keep M61 paused until the complete DEC-130 evidence package, including market and point-in-time financial data, passes review.
