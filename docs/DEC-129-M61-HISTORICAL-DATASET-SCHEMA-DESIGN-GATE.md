# DEC-129 — M61 Historical Dataset Schema & Manifest Design Gate

**Status:** Accepted
**Milestone:** M61 — Backtesting
**Date:** 2026-09-22

## Decision

The first M61 historical dataset implementation uses **UTF-8 CSV artifacts with canonical decimal text**, protected by an immutable manifest and SHA-256 checksums.

The dataset is externally stored for production-sized history. A small repository-owned fixture uses the same schemas and loader contracts.

This is deliberately a transparent first implementation. A future columnar format may be introduced behind the same application boundary if actual dataset size/performance requires it; that would require a new design decision.

## Artifact layout

A dataset version is represented by a manifest plus data artifacts:

```text
dataset/
  manifest.json
  market_observations.csv
  financial_snapshots.csv
```

The manifest pins each artifact by SHA-256 hash and records the dataset identity/version and schema version.

No loader may resolve an unpinned `latest` artifact.

## Manifest contract

Required fields:

- `dataset_id`
- `dataset_version`
- `schema_version`
- `market_observations_artifact`
- `financial_snapshots_artifact`

Each artifact entry contains:

- relative artifact path
- SHA-256 checksum
- row count
- coverage metadata

The manifest itself is immutable once published.

## Market observation schema

CSV columns:

```text
stock_id
timeframe
timestamp
open
high
low
close
volume
source
```

Rules:

- `stock_id` is the existing Stock UUID.
- `timeframe` uses the existing domain enum value.
- `timestamp` is ISO-8601 and timezone-aware.
- OHLCV values are serialized as canonical decimal strings.
- Rows are unique by `stock_id + timeframe + timestamp`.
- Rows are deterministically ordered by stock ID, timeframe, timestamp.
- `source` is provenance metadata and is not analytical input.

## Financial snapshot schema

CSV columns:

```text
stock_id
period_end
available_at
revenue
net_income
current_assets
current_liabilities
source
revision
```

Rules:

- `stock_id` is the existing Stock UUID.
- `period_end` and `available_at` use ISO dates for the daily Strategy v0 decision boundary.
- `available_at < period_end` is invalid.
- Monetary values are canonical decimal strings.
- Nullable balance-sheet fields are represented by an empty field.
- `revision` identifies source revisions; it is metadata, not a ranking signal.
- Rows are deterministically ordered by stock ID, period end, available-at date, revision.

## Daily availability precision

The first M61 implementation uses a **date** for financial `available_at`, not an intraday timestamp.

Reason: Strategy v0 currently evaluates daily bars and the production fundamental contract is date-based. This makes the point-in-time rule explicit without pretending to have intraday disclosure precision that the dataset does not provide.

If future strategies require intraday financial-event timing, the schema must evolve through a new decision gate.

## Numeric representation

CSV stores Decimal values as text rather than binary floating-point values.

The loader reconstructs Python `Decimal` values before constructing domain objects.

This avoids introducing floating-point rounding as a dataset transformation and preserves deterministic serialization.

## Integrity

Before loading:

1. read the pinned manifest;
2. verify the manifest schema;
3. verify every artifact path is the expected relative path;
4. compute SHA-256 for every artifact;
5. reject any checksum mismatch;
6. validate row counts;
7. validate schema and domain-level constraints.

An integrity failure is a hard failure. The loader must never continue with partially trusted historical evidence.

## Filtering contract

The historical provider exposes the existing application contracts:

- market observations can be requested by stock and date range;
- financial snapshots can be requested by stock;
- point-in-time selection remains owned by `PointInTimeFundamentalDataProvider`.

The dataset loader must not implement opportunity classification, scoring, technical analysis, or backtest execution.

## Determinism

Given identical:

- dataset version,
- artifact bytes,
- manifest,
- stock/date query,

the loader returns identical logical observations in deterministic order.

The fixture dataset must be byte-stable and use the same validation rules as external datasets.

## Alternatives and trade-offs

### CSV — accepted

**Advantages**
- no new runtime dependency;
- human-readable and easy to inspect;
- deterministic serialization is straightforward;
- suitable for the first vertical slice.

**Costs**
- full-file scanning can become expensive at large scale;
- storage is less compact than columnar formats.

### JSON/JSONL — rejected for the first implementation

It is readable, but repeats field names and provides less convenient tabular interchange for the dataset shape without adding a benefit over CSV.

### Parquet — deferred

It is better suited to large analytical datasets and selective filtering, but introducing a columnar runtime dependency before measuring actual M61 dataset requirements adds complexity. It can be introduced later behind the same provider contract.

## Implementation sequence

1. Add manifest/domain validation models.
2. Add deterministic fixture CSV artifacts.
3. Add checksum and schema validation.
4. Add dataset loader.
5. Add historical market-data provider adapter.
6. Reuse `PointInTimeFundamentalDataProvider` over dataset snapshots.
7. Integrate with `AnalysisInputAssembler`.
8. Run end-to-end deterministic vertical-slice tests.

## Verification requirements

Tests must prove:

- malformed manifest rejection;
- unknown schema rejection;
- checksum mismatch rejection;
- row-count mismatch rejection;
- malformed market row rejection;
- duplicate market observation rejection;
- malformed financial row rejection;
- invalid availability/period relationship rejection;
- deterministic ordering;
- stock/date filtering;
- Decimal preservation;
- point-in-time revision behavior;
- identical input produces identical loaded data.
