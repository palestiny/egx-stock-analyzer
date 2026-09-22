# DEC-129 — M61 Historical Dataset Physical Format Design Gate

**Status:** Proposed — awaiting Project Owner decision
**Milestone:** M61 — Backtesting
**Date:** 2026-09-22

## Decision required

Select the physical artifact format for the production versioned historical dataset introduced by DEC-128.

The repository-owned fixture remains JSON and is test-only. It must not constrain the production artifact format.

## Candidates

### A — JSON Lines / row-oriented text

Each market observation or financial snapshot is stored as one deterministic JSON object per line.

**Strengths**
- Human-readable and easy to inspect/review.
- Native support for decimal values when represented as strings.
- Simple standard-library parsing for early tooling.
- Easy to generate deterministic artifacts.

**Costs**
- Larger artifacts and slower scanning as historical coverage grows.
- Date/stock filtering requires more application-side scanning unless an additional index is introduced.
- Schema evolution and validation require explicit application conventions.
- Less efficient for repeated analytical scans.

**Best fit:** transparent small-to-medium fixtures and debugging.

### B — Apache Parquet / columnar

Historical market and financial records are stored as typed columnar data with an explicit schema.

**Strengths**
- Efficient column/date/stock filtering for analytical workloads.
- Strong typed schema support, including decimal logical types.
- Compression materially reduces storage for repeated historical columns.
- Mature Python analytical ecosystem.
- Suitable for growing external immutable dataset artifacts.

**Costs**
- Less directly human-readable.
- Adds a production dependency and serialization tooling.
- Requires explicit schema/version governance.
- Raw artifact inspection is less convenient than text.

**Best fit:** production historical backtesting datasets at meaningful scale.

## Evaluation against DEC-128 requirements

| Requirement | JSON Lines | Parquet |
|---|---|---|
| Deterministic ordering | Strong, application-controlled | Strong, application-controlled |
| Decimal/numeric fidelity | Strong if decimals are serialized as strings | Strong with explicit Decimal schema |
| Schema validation | Application/schema layer required | Schema + application validation |
| Date filtering | Linear scan unless indexed | Strong |
| Stock filtering | Linear scan unless indexed | Strong |
| Large historical coverage | Increasingly inefficient | Designed for this workload |
| Human inspectability | Excellent | Moderate |
| External immutable artifact | Good | Good |
| Python ecosystem | Excellent | Excellent |
| Production analytical workload | Acceptable but costly | Strong |

## Recommendation

**Proposed choice: B — Parquet for the production historical artifact.**

Keep the repository-owned JSON fixture because its purpose is deterministic, reviewable test evidence rather than production-scale storage.

This preserves the architectural boundary:

- VersionedDatasetManifest remains format-neutral.
- Production loader implementation targets Parquet behind the existing application/provider contracts.
- The test fixture loader remains JSON-specific and test-only.
- No analysis or simulator logic depends on the physical storage format.

## Non-negotiable invariants regardless of format

1. Dataset ID and version are immutable identifiers.
2. Manifest SHA-256 must match the exact artifact bytes before loading.
3. Schema version is explicit and validated.
4. Date-range and stock filtering are deterministic and inclusive according to the dataset contract.
5. Decimal financial values must not be silently converted through binary floating-point representations.
6. Financial revision selection remains point-in-time: available_at <= decision_date.
7. Missing historical input remains unavailable; no fallback to current/live provider data.
8. Physical format changes must not change application/domain contracts or analytical rules.

## Consequence

Once approved, the next implementation slice is:

1. Add the production Parquet schema contract.
2. Implement the versioned artifact loader with manifest-first integrity verification.
3. Implement historical market provider over the loader.
4. Implement dataset-backed point-in-time financial provider.
5. Run the existing production AnalysisInputAssembler and Strategy v0 through a deterministic vertical slice.
6. Verify leakage, missing-input behavior, and repeatability.

No real historical coverage is claimed by this design gate.
