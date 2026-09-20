# DEC-117 — M55 Analysis Run Retention & Deletion Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M55

## 1. Problem

M20 introduced durable historical analysis snapshots and M49–M54 established durable analysis-run identity, outcome completeness, and per-user ownership.

The system can now accumulate analysis runs and correlated stock snapshots indefinitely. No explicit lifecycle policy currently defines when historical analytical data may be retained, deleted, or compacted.

This is now a data-lifecycle concern rather than an analytical concern.

Without an explicit boundary, storage growth, user expectations, operator cleanup, and historical-reference semantics remain implicit.

## 2. Desired Outcome

Define a controlled lifecycle for AnalysisRun records and their correlated historical snapshots without changing:

- analytical calculations;
- per-stock execution semantics;
- M54 ownership authorization;
- existing read-model contracts until an accepted lifecycle change is implemented;
- scheduled workflow lifecycle history;
- management audit records.

The design must make deletion and retention behavior explicit before any destructive implementation is introduced.

## 3. Scope

### In scope

- retention policy ownership;
- user-owned versus system/global retention;
- manual deletion semantics;
- operator deletion semantics;
- soft-delete versus hard-delete;
- cascading behavior from AnalysisRun to correlated snapshots;
- references from other durable records;
- historical API behavior after deletion;
- pagination/cursor behavior around deleted records;
- audit requirements for destructive actions;
- idempotency and concurrency;
- storage cleanup strategy;
- testability.

### Out of scope

- changing analytical calculations;
- changing M54 authorization semantics;
- scheduled-workflow deletion;
- management-audit retention;
- notification-history retention;
- provider/raw-market-data retention;
- database technology replacement;
- distributed garbage collection;
- background worker infrastructure;
- user sharing/ACLs;
- portfolio/trading history.

## 4. Current Boundary

```
AnalysisRun
    ↓
Correlated Analysis Snapshots
    ↓
AnalysisRunStore / Snapshot Store
    ↓
Read Capabilities
    ↓
API / Dashboard
```

M54 ownership remains authoritative for access. Retention must not bypass authorization.

## 5. Candidate Alternatives

### A. No deletion; retain forever

**Advantages**
- simplest semantics;
- strongest historical reproducibility;
- no destructive lifecycle logic.

**Trade-offs**
- unbounded storage growth;
- no user/operator cleanup capability;
- eventually unsuitable for long-running deployments.

### B. Hard deletion

Delete the AnalysisRun and all snapshots owned exclusively by that run.

**Advantages**
- simple long-term storage model;
- immediately reclaims space;
- clear absence semantics.

**Trade-offs**
- destructive and irreversible;
- requires careful reference analysis;
- historical URLs/cursors become invalid after deletion;
- stronger audit requirements.

### C. Soft deletion

Mark the AnalysisRun deleted while retaining underlying data.

**Advantages**
- reversible;
- safer operational recovery;
- preserves physical history.

**Trade-offs**
- does not immediately reclaim storage;
- every read path must consistently exclude deleted records;
- requires eventual purge semantics anyway.

### D. Retention policy plus explicit deletion

Use an explicit retention policy for automatic lifecycle management and an authorized manual deletion capability.

**Advantages**
- separates ordinary lifecycle from exceptional cleanup;
- supports both operational and user needs;
- allows policy changes without redefining deletion semantics.

**Trade-offs**
- more lifecycle states/rules;
- requires deterministic purge semantics;
- needs careful interaction with ownership and audit.

## 6. Open Questions

1. Should users be allowed to delete their own AnalysisRuns?
2. Should operators be allowed to delete user-owned runs?
3. Should system/global runs ever be user-deletable?
4. Should deletion be hard, soft, or a two-stage soft-delete → purge model?
5. Are correlated snapshots exclusively owned by one AnalysisRun, or can future capabilities reference them independently?
6. What should happen to a snapshot that has another durable reference?
7. Is there a default retention period, and who controls it?
8. Should retention differ between user-owned and system/global runs?
9. Does deletion require a management-audit record?
10. Should deletion be synchronous for the MVP?
11. What happens to opaque cursors when records disappear between requests?
12. What concurrency rule prevents deletion from racing with a read or active analysis execution?
13. Must completed AnalysisRuns be immutable until deletion, or can metadata be changed?
14. What is the recovery expectation after accidental deletion?
15. Does retention apply to failed/incomplete runs differently from completed runs?

## 7. Required Invariants

Any accepted design must preserve:

1. M54 authorization remains authoritative before deletion.
2. A user cannot delete another user's run.
3. System/global records cannot become user-owned as a side effect of deletion.
4. Deletion cannot silently alter analytical results that remain referenced elsewhere.
5. Destructive operations are idempotent.
6. Concurrent analysis execution cannot produce a partially deleted authoritative result.
7. Existing historical snapshots remain immutable until their lifecycle policy explicitly removes them.
8. API behavior after deletion is deterministic and non-enumerating where applicable.
9. Audit requirements for destructive actions are explicit.
10. Retention must not be implemented implicitly inside dashboard or transport code.

## 8. TDD Acceptance Shape

Before implementation, tests should cover at minimum:

- authorized self-deletion;
- unauthorized cross-user deletion;
- operator deletion policy;
- system/global deletion policy;
- repeated deletion;
- concurrent deletion versus read;
- concurrent deletion versus active analysis;
- correlated snapshot cascade/reference behavior;
- legacy/global M54 records;
- cursor behavior after deletion;
- retention eligibility;
- purge behavior;
- audit event behavior;
- restart/persistence behavior.

## 9. Decision Gate

**Status: Proposed — implementation is not authorized.**

The next controlled action is to resolve the open questions and record the accepted retention/deletion boundary before introducing destructive lifecycle behavior.

## 10. Revisit Conditions

Revisit this gate if:

- storage growth creates an operational requirement;
- users require self-service historical cleanup;
- compliance/data-lifecycle requirements change;
- snapshot sharing/reuse becomes a concrete requirement;
- a background job infrastructure is introduced and changes the cost of automatic retention;
- a future design explicitly replaces historical snapshots with another durable model.
