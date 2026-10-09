# M61 Historical Source Acceptance Matrix

Status: Working evidence matrix — not an acceptance decision.

## Current evidence

| Source | Historical OHLCV | Cohort coverage | Provenance | Adjustment semantics | Long-term storage rights | M61 role |
|---|---|---|---|---|---|---|
| Mansa Markets | Documented EGX history API | Must verify 10-symbol extraction | Provider metadata + response checksum | Official methodology says historical prices are as-published; no back-adjustment for splits/corporate actions | Professional permits caching up to 7 days; long-lived stored copies are not established as permitted | Acquisition / cross-check candidate |
| EGX.news | Daily historical CSV advertised for 276 stocks, back to 1994 | Cohort-specific artifact still required | Public product claim; artifact provenance still required | Not established from public product page | Not established from public product page | Archive candidate |
| EGX / EGI | Historical endpoints documented | Exact response contract still unverified | Primary-market provenance target | Must establish source semantics | Must establish reuse rights | Primary provenance candidate |
| Mubasher | Historical endpoint reported by third-party implementations | Must verify current access | Not accepted | Not established | Not established | Cross-check candidate |

## 2026-09-28 source/licensing refresh

### EGX.news

The current public data page advertises full daily historical OHLCV CSV data for EGX stocks, priced at $1 per stock, with stated history since IPO/back to 1994. It identifies CSV fields including Date, Time (CLT), Open, High, Low, Close, Volume, and Value (EGP).

This establishes a concrete paid artifact-acquisition path, but it does not by itself establish the delivered artifact's observation-level provenance, corporate-action semantics, or long-term retention/use terms.

**Decision:** use COMI as the first artifact-level acceptance test if an artifact can be obtained with explicit permission to retain it for M61 research. If the purchase flow does not expose retention terms, obtain those terms from the provider before treating the artifact as an immutable research source.

### Mansa

The current official methodology states that historical prices are served as published by exchanges and are not currently back-adjusted for splits or corporate actions. This is compatible with M61 D5, provided the dataset version records that convention.

The current licensing page states that Professional permits caching responses for up to 7 days and explicitly distinguishes application caching from building a stored copy of the provider dataset. Raw redistribution requires Institutional.

**Decision:** keep the merged Mansa probe ready, but do not freeze Mansa responses into the immutable M61 archive unless the project's entitlement and intended long-lived research storage/use are explicitly permitted.

### EGI / Egyptian Exchange feed

The public EGI Swagger surface currently documents POST /api/Feed/GetSymbolHistory plus date-range endpoints including GetSymbolsChartByDateRange and GetAllSymbolsChartByDateRange. This strengthens EGI as a primary-provenance acquisition path, but the exact request payload, authentication requirement, returned field semantics, and reproducible bulk extraction contract are still not validated.

**Decision:** investigate the exact EGI request/response contract before writing an EGI production acquisition adapter. Do not treat endpoint listing alone as historical-data evidence.

## Acceptance rule

No source becomes an M61 accepted historical artifact until the acquisition package contains:

1. Raw artifact or legally permissible immutable equivalent.
2. Provider/source identity.
3. Acquisition timestamp.
4. Source symbol to internal Stock mapping.
5. Exact coverage start/end and row count.
6. Duplicate/order/numeric/OHLCV validation results.
7. Missing-session and suspension findings without weekend/holiday assumptions.
8. Corporate-action convention.
9. Symbol-change evidence.
10. SHA-256 checksum.
11. Licensing/storage/use evidence.
12. Reproducible transformation manifest.

A source can be useful as a cross-check without satisfying this acceptance gate.

## Current acquisition consequence

The repository is software-ready for Mansa, while EGI and EGX.news remain artifact-acquisition candidates.

The next implementation should only be created after:
1. the first real artifact is acquired and its terms permit the intended storage/use; or
2. the EGI request/response contract is verified end-to-end.

Avoid creating provider-specific transformation logic from public marketing/schema descriptions alone.


## No-budget decision update — 2026-10-09

The project owner cannot pay for a historical-data package or professional API. Paid candidates above remain reference options only and are not required for the next step.

A free Yahoo chart probe has been added for local diagnostic use. It is explicitly `CANDIDATE_ONLY`, preserves exact response bytes only by opt-in, and does not imply long-term storage, redistribution, or commercial display rights. The public EGID/EGX feed remains a second candidate pending verification of its request/response contract and historical coverage.

No source is accepted yet. The financial point-in-time dataset remains a separate open requirement. See [M61 No-Cost Data Acquisition](M61-NO-COST-DATA-ACQUISITION.md).


## No-cost EGID contract discovery — 2026-10-09

The repository now contains `tools/m61_egid_contract_probe.py` plus deterministic contract-parser tests. It inspects the published OpenAPI document only and intentionally does not call market-data operations or save price data. A discovered schema is not evidence that a history endpoint is free, reachable, deep enough, or licensed for long-term research storage. The next provider-specific implementation remains blocked on actual contract/access evidence, not on more generic infrastructure.

## No-cost source verification — 2026-10-09

| Candidate | Observed result | Decision |
|---|---|---|
| Yahoo chart endpoint | HTTP 200 for all ten .CA tickers; MUTUALFUND metadata and hundreds of OHLCV/null findings per ticker | Reject for M61 |
| EGID public history API | Swagger declares Bearer security; one unauthenticated COMI history request returned HTTP 401 | No anonymous access; free account/retention terms unverified |
| StockAnalysis | Its terms prohibit automated scraping/bulk collection and programmatic use to build a competing database/product | Do not scrape or use as a dataset source |
| EGXAPI | Free pricing advertised, but published legal terms are explicitly marked as draft placeholders | Not accepted until binding terms/provider identity are verified |
| Existing brokerage/platform CSV export | Not yet supplied or verified | Potential no-cost intake route, conditional on source terms |

The owner cannot pay for paid feeds. The remaining no-cost path is a real, permitted CSV export already available to the owner, followed by the existing immutable candidate builder and acceptance gate. No source is currently accepted, and point-in-time financial snapshots remain a separate blocker.


## Bounded no-cost probe outcomes — 2026-10-09

- **EGID/EGX documented history routes:** unauthenticated COMI requests to both `POST /api/DelayedFeed/getSymbolHistory` and `POST /api/Feed/GetSymbolHistory` returned HTTP 401. This establishes an authentication/access boundary, not that authorized access is impossible. No credentials were sent and no price values were retained. [Probe run](https://github.com/palestiny/egx-stock-analyzer/actions/runs/37922382383).
- **Yahoo ticker variants:** `COMI.CA` returned 1,716 rows from 2019-01-01 through 2025-12-31, but metadata said `MUTUALFUND` and the validator reported 410 findings, including OHLC contradictions. `COMI.EG`, `COMI.EGX`, `COMI.EY`, and bare `COMI` returned HTTP 404. This rejects the simple ticker-suffix fix; no raw price rows were saved. [Probe run](https://github.com/palestiny/egx-stock-analyzer/actions/runs/37922610741).
- **Other public code projects reviewed:** `egx-data` uses Yahoo Finance and a browser CORS proxy; `egxpy` advertises a free downloader but does not establish an independent, licensed source in the reviewed README; `borsa` is a useful MIT-licensed quote aggregator but its documented endpoints do not provide historical bars, and its Yahoo integration is explicitly unofficial and disabled by default.
- **StockAnalysis:** its published terms prohibit automated scraping/bulk collection and programmatic use to build a competing database/product; do not scrape it as a dataset source: https://stockanalysis.com/terms-of-use/.
- **EGXAPI:** its website advertises a free API and historical bars, but its public legal page labels the terms as a draft with placeholder text; it is not accepted until provider identity and binding data-storage/use terms are verifiable: https://egxapi.com/legal/.

**Current decision:** no verified no-cost source has yet supplied the required immutable 2019–2025 daily OHLCV artifact plus 252-session warm-up for the ten-symbol cohort, and no complete point-in-time financial artifact is present in the repository. Do not accept the synthetic test fixture as market evidence or create missing observations. The next valid transition requires either (a) an owner-accessible CSV/API export whose actual terms permit local historical research/backtesting, or (b) a legitimately authorized free provider account/API key with its storage/use terms verified. The existing inspector and candidate builder are ready to validate such artifacts; they cannot manufacture the missing source evidence.
