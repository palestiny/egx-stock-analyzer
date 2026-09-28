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
