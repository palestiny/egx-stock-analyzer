# M61 — DataCedar Live Documentation Recheck

**Reviewed:** 2026-11-11  
**Related PR:** #502  
**Status:** Clarification addendum; candidate remains **NOT ACCEPTED**.

This recheck was performed against the live DataCedar API reference, EGX market page, pricing page, and Terms of Service. It records two important public-documentation ambiguities so they are not silently treated as evidence.

## 1. EGX listing count is not verified history coverage

The EGX market page simultaneously claims:

- 260 EGX symbol pages/listings;
- daily bars for every listing back to the first session DataCedar can source;
- 0 of 260 pages carrying enough traded history to qualify for sitemap inclusion.

The third statement is a sitemap/indexation qualification, not a statement that the API has zero rows for all 260 symbols. The same page explicitly says the other pages exist and are reachable through the A-to-Z listing. It is therefore incorrect to translate "0 sitemap-qualified pages" into "0 symbols have history" or to infer missing/empty API series from it.

**Evidence status:** provider marketing/documentation claim only. Actual EGX coverage remains unverified until the authenticated /v3/exchanges/{code}/symbols registry and per-symbol /bars/range results are examined. Do not treat the 260 count as 260 usable, complete, independently sourced series.

References:
- https://datacedar.com/markets/egx
- https://datacedar.com/docs

## 2. Explorer adjustment entitlement is internally ambiguous

The current API reference documents daily adjustment values raw, split, dividend, and all, and says daily bars are stored raw and adjusted. However, the current pricing feature matrix labels Explorer's corporate-action/adjusted-series entitlement **"Raw close only"**, while the EGX market page and general API reference describe raw and adjusted series.

These statements are not sufficient to establish which fields and adjustment modes an Explorer account can actually retrieve for EGX. The plan matrix may restrict corporate-action/adjusted-series functionality even though the endpoint schema accepts the parameter.

**Decision:** do not assume Explorer provides adjusted OHLCV or corporate-action history. A future authenticated diagnostic must record the exact response and entitlement behavior, and DataCedar should clarify in writing whether raw, split, dividend, and all are available on Explorer for EGX, and what "Raw close only" means for open/high/low/volume.

References:
- https://datacedar.com/docs
- https://datacedar.com/pricing
- https://datacedar.com/markets/egx

## 3. Reconfirmed Explorer limits and use terms

The live API reference and pricing page currently agree on:

- one year of daily history;
- seven days of minute history;
- three symbols per request;
- one general REST request per second.

The API reference documents daily pagination and the range endpoint. The Terms permit normal cursor pagination for a bounded research query and reasonable retention for internal research/backtesting, but prohibit systematic acquisition or archive replication. They also state that third-party source rights remain applicable and that data can be incomplete, duplicated, corrected, or unavailable.

References:
- https://datacedar.com/docs
- https://datacedar.com/pricing
- https://datacedar.com/terms

## 4. Updated M61 decision

**No change: DataCedar is NOT ACCEPTED as an M61 source.**

The safe next step, only after the owner deliberately provisions a free API key, is a bounded metadata-only coverage check for COMI:

1. Resolve the canonical EGX symbol ID from the authenticated exchange/symbol registry.
2. Request /bars/range for daily bars and record only first/last timestamps, count, response metadata, and errors.
3. Do not download a broad range or retain OHLCV in this first check.
4. Confirm the Explorer adjustment entitlement and EGX source lineage with the provider.
5. Stop if the symbol is not live, the range is empty, entitlement is unclear, or query scope/retention is not confirmed.

This check would establish only what the account endpoint reports, not source authenticity, completeness, independent corroboration, or DEC-130 acceptance. No paid plan, provider selection, adapter, ingestion, canonical CSV edit, or M61 activation is authorized.
