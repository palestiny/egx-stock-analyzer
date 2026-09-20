# DEC-118 — M56 Analysis Run Retention & Deletion Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M56 — Analysis Run Retention & Deletion

## 1. Problem

M20 introduced durable historical analysis snapshots. M49–M55 established durable analysis-run identity, snapshot correlation, outcome completeness, and explicit per-user snapshot ownership.

The system can now accumulate analysis runs and correlated snapshots indefinitely, but no explicit lifecycle policy defines when historical analytical data may be hidden, deleted, or physically purged.

This is a data-lifecycle concern, not an analytical concern.

Without an explicit boundary, storage growth, user cleanup expectations, operator cleanup, auditability, and historical-reference semantics remain implicit.

## 2. Desired Outcome

Define a controlled lifecycle for AnalysisRun records and their correlated historical snapshots without changing:

- analytical calculations;
- per-stock execution semantics;
- M54/M55 ownership authorization;
- existing read models except where lifecycle visibility requires it;
- scheduled-workflow lifecycle history;
- management-audit retention.

The design must make deletion and retention behavior explicit before destructive implementation is introduced.

## 3. Scope

### In scope

- retention-policy ownership;
- user-owned versus system/global lifecycle;
- manual deletion semantics;
- operator deletion semantics;
- logical deletion versus physical purge;
- correlated snapshot lifecycle;
- references from other durable records;
- historical API behavior after deletion;
- cursor behavior when records disappear;
- audit requirements for destructive actions;
- idempotency and concurrency;
- storage cleanup strategy;
- testability.

### Explicitly out of scope

- changing analytical calculations;
- changing M54/M55 authorization semantics;
- scheduled-workflow deletion;
- management-audit retention;
- notification-history retention;
- provider/raw-market-data retention;
- database technology replacement;
- distributed garbage collection;
- background-worker infrastructure;
- sharing/ACLs;
- portfolio/trading history.

## 4. Current Architectural Evidence

Current ownership is split deliberately:

```
AnalysisRunStore
    └── AnalysisRun metadata + outcomes

AnalysisResultStore
    └── Analytical snapshots

Read capabilities
    └── API / Dashboard
```

A correlated snapshot carries analysis_run_id, but the current SQLite snapshot schema does not use a database-level foreign key to the analysis-run table.

M53 outcomes already cascade with their parent run inside SQLiteAnalysisRunStore.

M54/M55 ownership is authoritative for authorization and must remain so before any lifecycle mutation.

There is currently no destructive deletion capability, so M56 is free to define a lifecycle contract without preserving an existing deletion API.

### Cross-store consequence

A naive hard-delete implementation could delete the AnalysisRun in one store and fail while deleting correlated snapshots in another store. That would create a partial lifecycle and violate the requirement that deletion produce deterministic authoritative state.

Therefore M56 must decide the lifecycle boundary before implementation rather than hiding cross-store coordination inside an API route.

## 5. Alternatives

### A — Retain forever

Advantages: simplest semantics, strongest historical reproducibility, and no destructive lifecycle logic.

Trade-offs: unbounded storage growth and no cleanup capability.

### B — Immediate hard deletion

Delete the run and its exclusively correlated snapshots.

Advantages: immediate storage reclamation and simple absence semantics after successful deletion.

Trade-offs: irreversible; requires cross-store atomicity or compensation; invalidates historical references immediately; increases audit and concurrency requirements.

### C — Soft deletion only

Mark the run deleted and retain physical data indefinitely.

Advantages: reversible and avoids cross-store destructive transactions.

Trade-offs: no storage reclamation; every read path must consistently hide deleted data; eventually still requires a physical purge strategy.

### D — Logical deletion followed by explicit purge

Introduce a logical lifecycle state first, then a separate authorized purge capability.

Advantages: separates user-facing lifecycle from irreversible storage cleanup, permits a recovery window, allows purge atomicity to be designed independently, and makes read visibility deterministic before physical deletion.

Trade-offs: adds lifecycle state and delays storage reclamation.

**Current candidate:** D.

## 6. Open Questions

1. May users delete their own AnalysisRun records?
2. May operators delete user-owned runs?
3. Who may delete system/global runs?
4. Should deletion be logical, hard, or two-stage logical-delete → purge?
5. Are correlated snapshots exclusively owned by their run, or can future durable references exist?
6. What happens to a snapshot with another durable reference?
7. Should automatic retention be enabled in M56, or should M56 establish only explicit deletion?
8. Should user-owned and system/global retention differ?
9. Must deletion emit a management-audit event?
10. Should deletion be synchronous?
11. What happens to opaque cursors after records disappear?
12. How does deletion interact with an active analysis run?
13. Are completed run metadata records immutable until deletion?
14. What recovery window is required before physical purge?
15. Should failed/incomplete runs have different lifecycle eligibility?

## 7. Proposed Invariants

1. M54/M55 authorization is checked before lifecycle mutation.
2. A regular user cannot delete another user's run.
3. System/global records cannot become user-owned as a side effect of deletion.
4. Correlated snapshots cannot become visible independently when their parent run is logically deleted.
5. Destructive requests are idempotent.
6. Active analysis cannot be partially deleted.
7. Historical snapshots remain immutable until an explicit lifecycle transition removes them from normal visibility.
8. Deleted resources have deterministic non-enumerating API semantics.
9. Destructive lifecycle actions have explicit audit semantics.
10. Retention policy is owned by application/domain lifecycle capabilities, never by React or transport code.
11. Physical purge is not an implicit side effect of a user-facing delete request unless atomicity is explicitly established.
12. Lifecycle state survives restart.

## 8. TDD Acceptance Shape

Before implementation, tests should cover at least:

- authorized self-deletion;
- unauthorized cross-user deletion;
- operator deletion policy;
- system/global deletion policy;
- repeated deletion;
- deletion of an active run;
- correlated snapshot visibility after logical deletion;
- legacy/global records;
- cursor behavior after deletion;
- retention eligibility if accepted;
- purge behavior if accepted;
- audit event behavior;
- restart/persistence behavior;
- concurrent deletion versus active analysis;
- deterministic behavior when a referenced snapshot exists.

## 9. Recommended Decision Direction

The architecture evidence currently supports a **two-stage lifecycle: logical deletion first, physical purge later**.

A reasonable MVP baseline to evaluate is:

1. regular users may delete only their own runs;
2. operators may delete user-owned and system/global runs;
3. deletion marks the AnalysisRun logically deleted;
4. normal run and snapshot reads exclude deleted runs;
5. correlated snapshots become lifecycle-hidden with their run;
6. standalone/runless snapshots remain independently governed by M55 ownership;
7. physical purge is a separate capability and is not an implicit side effect;
8. deletion emits an explicit audit event through the existing audit boundary;
9. repeated deletion by an authorized caller is a successful no-op;
10. deletion is rejected while a run is actively executing;
11. retention eligibility is deterministic but automatic background cleanup is deferred;
12. non-lifecycle metadata remains immutable.

These are **recommendations, not accepted decisions**. The gate remains Proposed until the project owner accepts or changes them.

## 10. Decision Gate

**Status: Proposed — implementation is not authorized.**

The next controlled action is to resolve the open questions and record the accepted lifecycle boundary before introducing destructive or lifecycle-mutating behavior.

## 11. Revisit Conditions

Revisit this gate if:

- storage growth creates a different operational requirement;
- compliance/data-lifecycle requirements change;
- snapshot sharing or cross-run references become concrete;
- background-worker infrastructure materially changes purge economics;
- a future design replaces historical snapshots with another durable model.