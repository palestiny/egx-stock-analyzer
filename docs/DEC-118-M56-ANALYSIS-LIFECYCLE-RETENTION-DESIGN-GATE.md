# DEC-118 — M56 Analysis Run & Snapshot Retention and Deletion Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M56 — Analysis Run & Snapshot Retention and Deletion

## 1. Problem

M20 introduced durable historical analysis snapshots. M49–M55 established durable analysis-run identity, snapshot correlation, outcome completeness, and explicit per-user snapshot ownership.

The system can now accumulate AnalysisRun records and correlated analytical snapshots indefinitely, but no explicit lifecycle policy defines when historical analytical data may be hidden, deleted, or physically purged.

This is a data-lifecycle concern, not an analytical concern. Without an explicit boundary, storage growth, user cleanup expectations, operator cleanup, auditability, historical-reference semantics, and cross-store consistency remain implicit.

## 2. Desired Outcome

Define one controlled lifecycle boundary for AnalysisRun metadata and AnalysisResultRecord snapshots that:

1. preserves M54/M55 ownership and authorization integrity;
2. keeps run/snapshot correlation consistent;
3. distinguishes retention policy from explicit deletion;
4. makes deletion deterministic and testable;
5. prevents partial lifecycle state across durable stores;
6. preserves latest-result and historical-read compatibility where records remain visible;
7. defines operator versus user lifecycle authority;
8. remains independent of analytical calculations, trading, notifications, and provider behavior.

## 3. Scope

### In Scope

- retention-policy semantics for AnalysisRun and AnalysisResultRecord;
- user-owned versus system/global lifecycle;
- explicit deletion authorization;
- logical deletion versus physical purge;
- correlated run/snapshot lifecycle;
- runless snapshot lifecycle under M55 ownership;
- references from other durable records;
- latest-result, history, comparison, performance, and run-detail behavior after deletion;
- opaque cursor behavior when records disappear;
- audit requirements for destructive actions;
- idempotency and concurrency;
- SQLite transactional behavior;
- restart behavior;
- testability.

### Explicitly Out of Scope

- changing analytical calculations or scoring;
- changing M54/M55 ownership rules;
- scheduled-workflow deletion;
- management-audit retention;
- notification-history retention;
- provider/raw-market-data retention;
- database technology replacement;
- distributed garbage collection;
- archival to object storage;
- sharing/ACLs;
- portfolio/trading lifecycle;
- background-worker infrastructure as part of the lifecycle MVP.

## 4. Current Architectural Boundary

    Authenticated Identity
            ↓
    Lifecycle Application Capability
            ↓
       ┌───────────────┬──────────────────┐
       ↓               ↓                  ↓
    AnalysisRunStore  AnalysisResultStore  Management Audit
       ↓               ↓
    AnalysisRun     AnalysisResultRecord
           ↘       ↙
           analysis_run_id

The current stores are separate durable boundaries. A naive hard-delete implementation could remove the run successfully and fail while removing correlated snapshots, producing partial lifecycle state.

Therefore M56 must define the lifecycle coordination contract before destructive implementation.

## 5. Lifecycle Alternatives

### A — Retain Forever

Advantages: simplest semantics; strongest historical reproducibility; no destructive lifecycle logic.

Trade-offs: unbounded storage growth and no cleanup capability.

### B — Immediate Physical Deletion

Advantages: immediate storage reclamation and simple absence semantics.

Trade-offs: irreversible; requires strong cross-store atomicity or compensation; historical references disappear immediately; increases audit and concurrency requirements.

### C — Logical Deletion Only

Advantages: reversible and avoids immediate destructive storage coordination.

Trade-offs: no storage reclamation; every read path must consistently hide deleted records; eventually still requires a purge strategy.

### D — Logical Deletion Followed by Explicit Purge

Advantages: separates user-facing lifecycle from irreversible cleanup, allows a recovery window, and lets purge atomicity be designed independently.

Trade-offs: adds lifecycle state, delays storage reclamation, and requires two lifecycle capabilities.

### E — Automatic Retention Plus Explicit Deletion

Advantages: bounds long-term storage while supporting intentional cleanup.

Trade-offs: highest policy complexity; automatic destructive behavior needs strong observability and protection rules.

**Current design candidate:** D, potentially combined with E after the retention policy is justified. This is a recommendation for discussion, not an accepted decision.

## 6A. Verified Current-State Constraints

The current repository implementation was inspected before lifecycle implementation.

### Shared durable database

create_infrastructure_runtime constructs SQLiteAnalysisResultStore and SQLiteAnalysisRunStore with the same config.analysis_database_path. The management-audit store, user store, credentials, scheduled-workflow store, and alert-delivery store also use that same configured SQLite database path.

This means the M56 lifecycle problem is not inherently a distributed-database problem in the current deployment. A coordinated lifecycle capability can potentially establish one SQLite transaction boundary if the stores expose a shared connection/transaction mechanism. The existing store APIs do not expose such a mechanism today.

### Run/snapshot dependency

analysis_results.analysis_run_id is currently a nullable correlation field without a database foreign key to analysis_runs. Conversely, analysis_run_outcomes has a foreign key to analysis_runs(run_id) with ON DELETE CASCADE.

Therefore deleting an AnalysisRun currently cannot rely on SQLite to cascade correlated analysis snapshots. Snapshot lifecycle coordination must be explicit.

### Read-side blast radius

The durable snapshot store is consumed by latest-result reads, stock history, snapshot-by-ID reads, run detail, comparison/performance capabilities, and market-opportunity read paths. The durable run store is consumed by run detail and run discovery.

A lifecycle implementation must therefore change the authoritative persistence/read predicates rather than patching one API endpoint.

### Ownership state

M54/M55 already persist nullable owner_user_id on runs and snapshots. The current read capabilities use owner-aware store queries plus application authorization. Lifecycle state must not replace or weaken this ownership boundary.

### Audit boundary

SQLiteManagementAuditStore is already composed against the same database path and is available in the application runtime. M56 can reuse this existing audit boundary, but whether destructive lifecycle requests are required to emit audit events remains an owner-controlled product/security decision.

### Technical consequence

The strongest technical implementation candidate is a dedicated lifecycle coordinator that operates over the existing application store abstractions and, for the current SQLite deployment, can be backed by an explicit shared-connection transaction adapter. The coordinator should not assume that two independently opened SQLite connections constitute one atomic transaction.

This is an engineering recommendation only. It does not decide user deletion authority, cascade policy, purge policy, or audit requirements.
## 6. Open Questions

1. May regular users delete their own AnalysisRun records?
2. May users delete their own runless snapshots?
3. May operators delete user-owned runs and snapshots?
4. Who may delete system/global records?
5. Does logical deletion preserve the existing owner?
6. Are correlated snapshots exclusively lifecycle-owned by their AnalysisRun?
7. Can a future durable record reference a snapshot independently?
8. What happens to a snapshot with another durable reference?
9. Does deleting a run delete, hide, or detach its correlated snapshots?
10. Do runless snapshots remain independently governed by M55?
11. Should M56 enable automatic retention or establish only explicit deletion?
12. What is the authoritative retention clock?
13. Should retention be global, per user, or operator-configurable?
14. What minimum historical window must be preserved?
15. Should the latest visible snapshot for each symbol be protected?
16. Should snapshots referenced by an AnalysisRun be protected?
17. Should completed, failed, and interrupted runs have different eligibility?
18. Should deletion be soft, hard, or two-stage logical-delete to purge?
19. Should deletion be synchronous?
20. What recovery window is required before physical purge?
21. Are repeated authorized deletion requests successful no-ops?
22. What happens when deletion races with an active analysis run?
23. What should latest-result, history, comparison, performance, and run-detail reads return after deletion?
24. How should opaque cursors behave when records disappear?
25. Must every destructive lifecycle action emit a management-audit event?
26. What transaction guarantee is required across AnalysisRunStore and AnalysisResultStore?
27. How should partial failure be recovered?
28. Must lifecycle state survive restart exactly?
29. Should physical purge be a separate maintenance use case?

## 7. Proposed Invariants

1. M54/M55 authorization is checked before lifecycle mutation.
2. A regular user cannot delete another user's run or snapshot.
3. System/global records cannot become user-owned as a side effect of deletion.
4. Snapshot/run ownership mismatch is never repaired by lifecycle operations.
5. Correlated snapshots cannot remain normally visible through another read path when their parent lifecycle is hidden, if the accepted policy makes the run authoritative.
6. Runless snapshots remain governed by their own M55 ownership state.
7. Destructive requests are idempotent.
8. Active analysis cannot be partially deleted.
9. Historical analytical results remain immutable until an explicit lifecycle transition removes them from normal visibility.
10. Deleted resources have deterministic non-enumerating API semantics.
11. Lifecycle policy is owned by application/domain capabilities, never React or transport code.
12. Physical purge is not an implicit side effect of a user-facing delete request unless atomicity is explicitly established.
13. Lifecycle state survives restart.
14. Retention eligibility is deterministic and testable without wall-clock sleeps.
15. A lifecycle mutation cannot silently create, alter, or reassign an AnalysisRun.
16. Destructive persistence is transactional within each durable boundary, with explicit cross-store coordination semantics.

## 8. TDD Acceptance Shape

Before implementation, tests should cover at least:

- authorized self-deletion;
- unauthorized cross-user deletion;
- operator deletion policy;
- system/global lifecycle policy;
- repeated deletion;
- active-run deletion;
- correlated snapshot behavior after run deletion;
- runless snapshot deletion;
- legacy/global records;
- latest-result behavior after deletion;
- history behavior after deletion;
- comparison/performance behavior after deletion;
- cursor behavior after deletion;
- retention eligibility and boundary timestamps if automatic retention is accepted;
- purge behavior if accepted;
- audit event behavior if required;
- restart/persistence behavior;
- concurrent deletion versus active analysis;
- deterministic behavior when a referenced snapshot exists;
- transaction rollback/compensation behavior for partial cross-store failure.

## 9. Recommended Decision Direction

The current architecture evidence supports evaluating a two-stage lifecycle first:

1. regular users may delete only resources they own;
2. operators may manage user-owned and system/global lifecycle where authorized;
3. logical deletion establishes visibility semantics;
4. normal run/snapshot reads exclude logically deleted resources;
5. correlated snapshots follow an explicitly accepted run-lifecycle rule;
6. runless snapshots remain independently governed by M55 ownership;
7. physical purge is a separate capability rather than an implicit side effect;
8. destructive actions use the existing management-audit boundary;
9. repeated authorized deletion is an idempotent no-op;
10. active executions are protected from partial deletion;
11. automatic retention remains disabled until its policy and storage rationale are explicitly accepted.

These are recommendations, not accepted decisions.

## 10. Engineering Decision Matrix (Not Yet Accepted)

The following defaults are the current engineering recommendations derived from the existing M54/M55 ownership model and the two-store persistence boundary. They are deliberately recorded as **recommendations**, not decisions, because several items change user-visible data lifecycle and destructive authority.

| Area | Recommended default | Rationale / trade-off |
|---|---|---|
| User deletion | Users may delete only resources they own | Preserves M55 ownership boundary; avoids cross-user authority. |
| Operator deletion | Operators may delete user-owned and global records only through an explicit privileged lifecycle capability | Centralizes destructive authority; increases audit responsibility. |
| Run deletion | A run deletion logically hides the run and its correlated snapshots together | Prevents orphaned visible history; couples the lifecycle intentionally. |
| Runless snapshots | Govern independently by their owner | They have no parent run to inherit lifecycle from. |
| Physical purge | Separate privileged maintenance capability | Avoids making an irreversible operation part of normal user-facing deletion. |
| Logical deletion | Hidden from all normal read paths, including latest/history/comparison/performance/run detail | Prevents contradictory visibility across projections. |
| Recovery | No user-facing undelete in the MVP | Simpler authorization and audit semantics; recovery can be an operator maintenance concern later. |
| Active run | Deletion is rejected while execution is active | Prevents partially deleted analysis state. |
| Idempotency | Repeating an already-authorized delete is a successful no-op | Makes retries safe and deterministic. |
| Retention | Disabled in the first lifecycle MVP | Avoids inventing a time policy before storage/usage evidence exists. |
| Retention clock | If later enabled, use persisted analysis/run creation time rather than process time | Deterministic and restart-safe. |
| Latest result | Deleted snapshots are never eligible for latest-result selection | Keeps latest reads consistent with lifecycle visibility. |
| Historical reads | Deleted snapshots are excluded without exposing whether another user's hidden record exists | Preserves ownership/non-enumeration semantics. |
| Cross-store atomicity | Introduce an application lifecycle coordinator; do not pretend two SQLite stores are one transaction unless they share a proven transaction boundary | Honest failure semantics; avoids false atomicity guarantees. |
| Partial failure | Prefer a coordinated transaction when both stores can share one SQLite connection; otherwise use a durable lifecycle operation state/reconciliation mechanism | A single-process best-effort sequence is insufficient for destructive lifecycle correctness. |
| Audit | Every successful or rejected destructive request emits a management-audit event when the existing audit boundary supports it | Provides accountability for irreversible lifecycle actions. |
| Cursor behavior | Cursors pointing past deleted records advance to the next visible record; no deleted record is returned | Keeps pagination stable without leaking lifecycle state. |
| References | A future durable reference to a snapshot blocks physical purge until an explicit reference policy exists | Prevents destroying data still required by another capability. |

### Decisions that remain owner-controlled

The following cannot safely be inferred from architecture alone and remain explicit approval points:

1. whether regular users may delete their own runs/snapshots;
2. whether operators may delete global records;
3. whether run deletion cascades to correlated snapshots;
4. whether any recovery/undelete capability is required;
5. whether M56 MVP should include physical purge;
6. whether destructive operations must always be audit-recorded;
7. the transaction/coordination guarantee required across the two durable stores.

No implementation should silently convert these recommendations into product policy.

## 11. Design Gate Decision

**Status: Proposed — implementation is not authorized.**

M56 implementation must not begin until the lifecycle policy, ownership authority, run/snapshot correlation behavior, read semantics, transaction strategy, and destructive-operation audit requirements are explicitly accepted.

## 12. Revisit Conditions

Revisit this gate if storage architecture changes, legal/compliance retention requirements appear, snapshot sharing or organizations are introduced, cross-run snapshot references become concrete, background-worker infrastructure materially changes purge economics, or the historical-analysis model is replaced.
