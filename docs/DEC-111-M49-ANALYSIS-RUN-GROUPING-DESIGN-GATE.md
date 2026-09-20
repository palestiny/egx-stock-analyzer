# DEC-111 — M49 Analysis Run Grouping Design Gate

**Status:** Accepted  
**Date:** 2026-09-20  
**Milestone:** M49 — Analysis Run Grouping & Snapshot Correlation

---

## 1. Context

The project now has two related but distinct histories:

- historical analysis snapshots, identified by `AnalysisResultRecord.snapshot_id`;
- scheduled workflow lifecycle history, identified by scheduled-workflow execution ID and persisted lifecycle sequence.

M14 market-wide analysis can execute multiple stocks as one application operation, while M20+ historical analysis persists each stock snapshot independently.

The current persistence model therefore answers:

> “What analytical snapshot exists for this stock?”

but does not directly answer:

> “Which snapshots were produced by the same market-wide analysis run?”

This becomes important as the system executes the configured market repeatedly. A future operator/read-side capability may need to correlate the set of stock results belonging to one completed market-wide run without inferring membership from dates alone.

This gate is intended to define that correlation boundary before changing persistence or API contracts.

---

## 2. Problem Statement

We need a stable, explicit correlation identity for one logical analysis run when that run produces multiple stock snapshots.

The design must preserve:

- existing latest-result compatibility;
- existing per-stock historical snapshots;
- existing market-wide execution semantics;
- existing scheduled-workflow ownership and idempotency boundaries;
- provider-neutral application architecture.

The design must not silently turn workflow execution identity into analysis identity: a scheduled workflow execution is an operational lifecycle object, while an analysis run is an analytical application operation.

---

## 3. Desired Outcome

After M49, the system should be able to represent:

```
Analysis Run
    ├── Stock Snapshot A
    ├── Stock Snapshot B
    ├── Stock Snapshot C
    └── ...
```

with an explicit correlation identity owned by the analysis application boundary.

A later read-side capability could then retrieve or summarize one analysis run without guessing membership from timestamps or symbols.

---

## 4. Scope

### In Scope

- definition of an analysis-run identity;
- ownership of that identity;
- correlation between one market-wide execution and its successful stock snapshots;
- behavior for partial and failed market-wide runs;
- persistence semantics;
- restart/idempotency implications;
- migration compatibility with existing snapshots;
- testability.

### Out of Scope

- ranking changes;
- new analytical calculations;
- trading decisions;
- dashboard UI;
- notification delivery;
- new authentication/authorization rules;
- distributed execution;
- changing scheduled-workflow lifecycle semantics;
- deleting or rewriting existing historical snapshots;
- portfolio allocation.

---

## 5. Alternatives

### A — Reuse Scheduled Workflow Execution ID

Use the scheduled workflow execution ID as the analysis-run correlation key.

**Advantage**
- no new identifier.

**Trade-off**
- couples analytical history to one operational trigger;
- manual analysis has no scheduled workflow execution;
- retries/recovery become difficult to distinguish from analytical identity;
- violates the conceptual distinction between workflow lifecycle and analysis execution.

### B — Add an Analysis Run ID

Create a dedicated immutable analysis-run UUID and associate produced snapshots with it.

**Advantage**
- explicit analytical identity;
- works for manual, scheduled, and future trigger types;
- preserves separation between operational workflow and analytical execution.

**Trade-off**
- requires persistence/schema evolution;
- every snapshot write path must carry correlation context.

### C — Infer Runs from Analysis Date / Timestamp

Treat snapshots with the same date/time window as one run.

**Advantage**
- no schema change.

**Trade-off**
- ambiguous for repeated/manual runs;
- cannot reliably distinguish partial retries;
- correlation becomes heuristic instead of domain/application data.

---

## 6. Current Candidate

**Candidate:** B — dedicated `AnalysisRunId`.

This is a design candidate only. It is not accepted by this document until the open questions below are resolved.

The candidate boundary is:

```
Analysis Run
    ↓
RunMarketAnalysis
    ↓
RunStockAnalysis
    ↓
AnalysisResultStore
    ↓
Analysis Snapshot
```

The scheduled workflow may trigger an analysis run, but it does not own the analysis-run identity.

---

## 7. Accepted Decisions

### 7.1 Analysis-run identity

M49 introduces a dedicated immutable AnalysisRunId for each market-wide analysis invocation. The identity is an application-level analytical correlation key and is distinct from scheduled-workflow execution identity.

The analysis run is persisted because the correlation must survive process restart and support future read-side queries. The persistence record is minimal: run ID, run date/time metadata needed for deterministic identification, aggregate execution state, and ownership context where applicable.

### 7.2 Snapshot correlation

Each successfully persisted historical analysis snapshot produced by the market-wide run carries the AnalysisRunId.

Failed stock outcomes are represented by the persisted analysis-run aggregate outcome rather than by creating fake analysis snapshots for failed stocks.

### 7.3 Partial and failed runs

A partially completed market-wide run remains a valid persisted analysis run and retains its successful snapshot associations.

An all-failed run is also persisted as a run record so that an attempted market-wide operation is not silently lost. It has no successful snapshot associations.

An empty market-wide run is persisted as a completed run with zero snapshot associations.

### 7.4 Idempotent scheduled occurrences

A scheduled workflow occurrence may trigger an analysis run, but the scheduled workflow execution ID is not the analysis-run ID.

For an idempotent repeated occurrence, the existing workflow idempotency boundary remains authoritative. A successful first execution reuses its already-established analysis-run correlation rather than creating a second analytical run for the same idempotent occurrence.

### 7.5 Multiple snapshots for one symbol

One analysis run may contain at most one successful snapshot per normalized symbol.

### 7.6 Manual analysis semantics

M49 correlation is introduced for market-wide analysis runs. Existing single-stock manual analysis does not gain a synthetic run identity in this milestone.

### 7.7 Legacy snapshots

Snapshots created before M49 have no analysis-run identity. They remain readable and are not rewritten merely to manufacture historical grouping.

### 7.8 Persistence boundary

The application-facing analysis-result boundary is extended explicitly rather than leaking SQLite details into orchestration or API code.

The first implementation may evolve the existing historical snapshot schema and add a dedicated analysis-run table, but the domain/application contract remains provider- and database-neutral.

No API/read model is required for the first M49 implementation. The first slice establishes application + persistence correlation with tests.

### 7.9 Indexing

M49 adds only indexes required by the accepted persistence access patterns. No speculative index is introduced.

## 8. Alternatives and Trade-offs

### Reusing scheduled workflow execution identity

Rejected for the M49 analytical boundary because it couples analysis history to one trigger type and does not cover manual or future triggers.

### Dedicated persisted analysis-run record

Accepted because durable correlation, partial/all-failed run visibility, empty-run representation, and future read-side queries require an explicit authoritative analytical grouping object.

### Inferring grouping from timestamps or dates

Rejected because repeated runs, retries, and partial completion make time-based membership ambiguous.

### Persisting only a run ID on snapshots

Insufficient for this MVP because an empty or all-failed run would have no snapshot row from which the run could be recovered.

## 9. Required Invariants

1. AnalysisRunId is immutable.
2. Workflow execution identity and analysis-run identity remain distinct.
3. Successful snapshots reference exactly one analysis run when produced by market-wide execution.
4. A failed stock never produces a fake snapshot.
5. Partial, all-failed, and empty runs remain explicitly represented according to the accepted persistence semantics.
6. Existing latest-result reads remain compatible.
7. Legacy snapshots remain readable without synthetic historical grouping.
8. At most one successful snapshot per symbol belongs to one analysis run.
9. Persistence remains behind application-facing contracts.
10. No analytical scoring/classification logic moves into persistence or correlation handling.
11. Ownership remains governed by the existing authenticated identity/ownership boundary.
12. Provider-specific behavior remains outside the analysis-run model.

## 10. TDD Acceptance Shape

- one market-wide run creates one stable analysis-run identity;
- successful snapshots reference that identity;
- partial completion preserves successful associations;
- all-failed runs persist a run with no successful snapshot associations;
- empty runs persist a completed run with zero associations;
- repeated idempotent scheduled occurrence behavior does not create a second analytical run;
- legacy snapshots remain readable with no run ID;
- latest-result reads remain unchanged;
- single-stock manual analysis remains unchanged;
- one successful snapshot per symbol per run is enforced;
- restart preserves analysis-run and snapshot correlation;
- persistence errors do not silently create partial correlation state.

## 11. Design Gate Decision

**Status: Accepted — implementation is authorized for the M49 scope defined here.**

Implementation must establish the application/persistence contract before any API/dashboard exposure. The scheduled workflow remains an operational trigger; the analysis run remains the analytical correlation boundary.
## 11. Revisit Conditions

Revisit this gate if:

- analysis snapshots gain a different execution/grouping model;
- distributed analysis introduces a separate execution identity;
- historical result storage is replaced;
- scheduled workflow and analysis execution are intentionally unified by a later architecture decision.
