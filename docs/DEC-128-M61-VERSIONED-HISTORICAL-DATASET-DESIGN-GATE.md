# DEC-128 — M61 Versioned Historical Dataset Design Gate

**Status:** Accepted
**Milestone:** M61 — Backtesting
**Date:** 2026-09-22
**Decision:** A2 — Versioned External Historical Dataset, with A1 repository-owned deterministic fixtures for tests

## Context

M61 requires deterministic, leakage-safe historical evaluation of the production Opportunity Classification Strategy v0.

DEC-127 established that financial-period end dates are not sufficient evidence of point-in-time availability. A historical fundamental fact is eligible only when its explicit availability date is on or before the decision date.

The existing Yahoo Finance fundamental adapter filters by period_end, so it is not an acceptable evidence source for leakage-safe Strategy v0 performance claims.

The simulator already enforces event-driven execution and uses production analytical rules through the historical strategy adapter. The remaining boundary is a reproducible historical dataset containing the market and point-in-time fundamental inputs required by that production analysis.

## Decision

Use **A2 — Versioned External Historical Dataset** as the production/backtesting dataset boundary.

The repository will own the dataset **contract, schema, manifest format, version identity, integrity metadata, and loading rules**, while the potentially large historical data artifact will live outside Git and be referenced by an immutable dataset version.

A small **A1 repository-owned fixture dataset** will be maintained for deterministic automated tests and vertical-slice verification. It is test evidence, not the production historical universe.

The dataset consumed by a backtest must be pinned to an immutable version and integrity identifier. A moving/latest dataset reference is not sufficient for a reproducibility claim.

## Dataset contents

The first dataset version must be capable of supplying:

1. Daily market observations required to construct production PriceBar history: stock identity, timeframe, timestamp/date, open, high, low, close, volume, and source metadata sufficient for provenance.
2. Historical financial snapshots: stock identity, financial period end, revenue, net income, current assets when available, current liabilities when available, explicit available_at, and revision/source metadata sufficient to distinguish revisions.
3. Dataset manifest: dataset identifier, immutable version, schema version, source/provenance metadata, coverage boundaries, integrity checksum/hash, and creation/export metadata.

## Point-in-time rules

For financial snapshots:
- available_at <= decision_date is required for eligibility.
- When multiple revisions for the same financial period are available by the decision date, the latest eligible revision is selected.
- A future revision must never be visible to an earlier decision date.
- A missing point-in-time snapshot is an unavailable input, not a reason to substitute current provider data.

For market observations:
- A completed bar may be used only after its timestamp/bar boundary has been reached.
- The backtest simulator remains responsible for execution timing.
- The dataset provider does not create trading signals and does not duplicate analytical rules.

## Reproducibility contract

A historical run is reproducible only when all of the following are fixed:
- dataset ID and immutable version
- dataset integrity hash
- dataset schema version
- strategy ID/version
- backtest configuration
- production analysis rules/code version
- requested stock/date range

The loader must reject an artifact whose integrity does not match the pinned manifest.

## Ownership boundaries

### Dataset layer owns
- historical artifact loading
- schema validation
- dataset/version identity
- provenance and integrity validation
- point-in-time financial snapshot retrieval
- historical market observation retrieval

### Existing application analysis owns
- AnalysisInputAssembler semantics
- data-quality assessment
- technical/fundamental analysis
- scoring
- opportunity classification

### Backtest simulator owns
- event ordering
- signal timing
- next-boundary execution
- position lifecycle
- transaction costs/slippage
- deterministic trade results

No duplicate Opportunity Classification thresholds or simplified analytical implementation will be introduced.

## Format decision

The physical artifact format is intentionally **not fixed by this decision**.

A follow-up implementation design must compare at least:
- transparent text/row-oriented format for the first vertical slice;
- columnar format for larger historical datasets.

The chosen format must preserve deterministic ordering, decimal/numeric fidelity, schema validation, and efficient date/stock filtering. The format choice must not change the domain/application contracts.

## Rejected alternatives

### A1 — Repository-owned production dataset
Rejected as the primary production boundary because a meaningful EGX historical universe can become too large for a maintainable Git repository. It remains appropriate for small deterministic fixtures.

### A3 — Application-owned persisted historical dataset
Deferred. It would provide strong long-term ownership, but introduces database/storage lifecycle concerns that are not required to establish M61's first reproducible backtest boundary.

### Live-provider replay
Rejected for the reproducible Strategy v0 performance boundary because provider responses can change and the current financial adapter does not expose sufficient point-in-time availability evidence.

### Period-end proxy
Rejected for leakage-safe performance claims. period_end does not establish when information became public.

## Consequences

### Positive
- Reproducible historical evidence is explicit and versioned.
- Point-in-time fundamental availability remains enforceable.
- Large datasets do not need to live in Git.
- Test fixtures remain small, reviewable, and deterministic.
- Existing production analysis and simulator remain the single analytical/trading-rule paths.

### Costs
- A dataset artifact distribution mechanism is required.
- Dataset ingestion/export and integrity tooling must be implemented.
- Historical coverage cannot be claimed until an actual dataset version exists.
- External dataset lifecycle must be governed and documented.

## M61 completion impact

This decision does **not** complete M61.

M61 remains in progress until:
1. an actual versioned historical dataset/source exists;
2. production-compatible historical market and financial providers consume it;
3. the existing data-quality boundary is verified for historical inputs;
4. deterministic Strategy v0 evaluation runs against real historical coverage;
5. aggregate and trade-level results are reviewed;
6. leakage and reproducibility invariants are re-verified;
7. implementation, documentation, and CI verification are complete.

## Implementation sequence

1. Define dataset schema and manifest contract.
2. Add deterministic repository fixture dataset.
3. Implement versioned dataset manifest/integrity validation.
4. Implement historical market-data provider.
5. Wire point-in-time financial provider to the dataset source.
6. Integrate the production AnalysisInputAssembler without duplicating analysis rules.
7. Run a small end-to-end historical vertical slice.
8. Verify leakage, determinism, and data-quality behavior.
9. Add real historical coverage and execute Strategy v0.
10. Review results and close M61 only after all completion criteria pass.

## Verification requirements

Every implementation PR must include tests for:
- immutable dataset version identity;
- manifest/schema validation;
- checksum/integrity mismatch rejection;
- deterministic loading;
- historical date-range filtering;
- stock filtering;
- point-in-time financial eligibility;
- revision selection;
- missing historical input behavior;
- compatibility with the existing data-quality boundary;
- deterministic end-to-end backtest reruns.