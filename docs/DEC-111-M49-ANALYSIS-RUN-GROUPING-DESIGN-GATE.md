# DEC-111 — M49 Analysis Run Grouping Design Gate

**Status:** Proposed  
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

## 7. Open Questions

1. Should an analysis run be modeled as an application result object only, or become a persisted domain/application record?
2. Should successful snapshots only carry the run ID, or should failed stock outcomes also be persisted as run members?
3. Should an empty market-wide run create a persisted analysis-run record?
4. Should a partially completed run remain queryable as one run?
5. How should a repeated idempotent scheduled occurrence map to analysis-run identity?
6. How should legacy snapshots created before M49 be represented when no run ID exists?
7. Is one run allowed to contain multiple snapshots for the same symbol?
8. Should manual single-stock analysis create an analysis-run identity, or is the new identity restricted to market-wide runs?
9. What is the minimum persistence/indexing contract required for future bounded run queries?
10. Does the first M49 implementation need an API/read model, or should it stop at application + persistence capability?

---

## 8. Required Invariants

If the design is accepted, implementation must preserve:

1. An analysis-run identity is immutable.
2. Workflow execution identity and analysis-run identity remain conceptually distinct.
3. Existing snapshot contents remain unchanged except for explicit correlation metadata.
4. Existing latest-result reads remain compatible.
5. Historical snapshots are not rewritten merely to manufacture correlation.
6. Partial market-wide analysis must not lose successful snapshots.
7. Correlation must be deterministic and testable.
8. No analytical scoring or classification logic moves into persistence or orchestration.
9. Existing ownership/authentication boundaries remain authoritative for future reads.
10. Provider-specific data remains outside the analysis-run model.

---

## 9. TDD Acceptance Shape

Before implementation is considered complete, tests should cover at minimum:

- a market-wide run receives one stable analysis-run identity;
- successful stock snapshots are associated with that identity;
- partial completion preserves successful associations;
- all-failed runs follow the accepted persistence semantics;
- empty-run behavior follows the accepted persistence semantics;
- repeated scheduled occurrence behavior is deterministic;
- legacy snapshots remain readable;
- latest-result reads remain unchanged;
- manual and scheduled trigger semantics follow the accepted identity boundary;
- persistence/restart preserves correlation.

---

## 10. Design Gate Status

**Proposed — implementation is not authorized by this document.**

The next step is to resolve the open questions and record the accepted decision before changing the analysis-result persistence contract.

---

## 11. Revisit Conditions

Revisit this gate if:

- analysis snapshots gain a different execution/grouping model;
- distributed analysis introduces a separate execution identity;
- historical result storage is replaced;
- scheduled workflow and analysis execution are intentionally unified by a later architecture decision.
