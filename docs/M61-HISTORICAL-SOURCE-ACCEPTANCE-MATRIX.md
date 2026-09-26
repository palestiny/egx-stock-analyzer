# M61 Historical Source Acceptance Matrix

Status: Working evidence matrix — not an acceptance decision.

## Current evidence

| Source | Historical OHLCV | Cohort coverage | Provenance | Adjustment semantics | Long-term storage rights | M61 role |
|---|---|---|---|---|---|---|
| Mansa Markets | Documented EGX history API | Must verify 10-symbol extraction | Provider metadata + response checksum | Documented as-published methodology; must preserve evidence | Must obtain tier-specific confirmation | Acquisition / cross-check candidate |
| EGX.news | Daily historical CSV advertised for 276 stocks, back to 1994 | Cohort-specific artifact still required | Public product claim; artifact provenance still required | Not established from public product page | Not established from public product page | Archive candidate |
| EGX / EGI | Historical endpoints documented | Exact response contract still unverified | Primary-market provenance target | Must establish source semantics | Must establish reuse rights | Primary provenance candidate |
| Mubasher | Historical endpoint reported by third-party implementations | Must verify current access | Not accepted | Not established | Not established | Cross-check candidate |

## EGX.news evidence captured on 2026-09-26

The public data page advertises:
- daily historical OHLCV for 276 stocks;
- history since IPO / dating back to 1994;
- CSV delivery;
- fields including Date, Time, Open, High, Low, Close, Volume, and Value.

This establishes product availability claims only. It does **not** establish:
- corporate-action adjustment rules;
- treatment of suspended sessions;
- symbol-change continuity;
- exact coverage for the M61 ten-symbol cohort;
- provenance for each observation;
- permission to retain an immutable research archive;
- permission to transform and redistribute derived datasets.

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

## Next executable evidence

For EGX.news, obtain a real COMI sample artifact first and verify:
- exact columns and timestamp semantics;
- date coverage through the M61 evaluation window;
- corporate-action treatment;
- symbol identity;
- artifact retention/use terms.

For Mansa, run the existing probe with valid credentials and preserve raw responses only when the licensing decision permits it.

Neither source is accepted by this document alone.
