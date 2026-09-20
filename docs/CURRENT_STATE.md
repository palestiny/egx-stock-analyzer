# EGX Stock Analyzer — Current State

**Authority:** GitHub main + current open pull requests  
**Last verified:** 2026-09-20  
**Repository:** palestiny/egx-stock-analyzer

## 1. Where We Are

The repository is **past the earlier milestone sequence and is currently at M56**.

M56 — Analysis Run & Snapshot Retention and Deletion is **complete**.

M56 design is now accepted. The accepted M56 logical-deletion MVP is merged into `main`. Physical purge and automatic retention remain out of scope.

Latest M56 design synchronization:

- **PR #145** — docs: clarify accepted M56 lifecycle engineering boundary — merged at `9c435668fad08c963bc1fab4aeb422532c16f386`.
- **PR #147** — docs(m56): sync current state after lifecycle design clarification — merged at `860ee362c2f5a0dc4847c71f99d5bcf2bd0d51ca`.
- Purpose: keep the current-state document synchronized with the proposed M56 gate without silently accepting unresolved destructive lifecycle policy.

Owner-controlled M56 lifecycle decisions have been accepted and recorded in DEC-118 and DECISION_LOG.md.

The latest verified merged main commit is:

65d70c921ed244120be612f0c14bb07178bc9948

Merge message:

Merge pull request #148 from palestiny/m56-lifecycle-implementation

feat(m56): implement analysis lifecycle deletion MVP

The implementation head `9c46cdf6371ff86f074dee5805bf34358e76a941` passed GitHub Actions Tests Run #2497 before merge.

## 2. Current M56 Boundary

M56 concerns the lifecycle of:

- AnalysisRun
- AnalysisResultRecord historical snapshots

The current design work is about retention, logical deletion, physical purge, ownership, authorization, run/snapshot correlation, auditability, transaction coordination, concurrency, and read-side behavior after lifecycle changes.

**M56 destructive lifecycle implementation is complete within the accepted logical-deletion boundary.**

The latest design gate is:

docs/DEC-118-M56-ANALYSIS-LIFECYCLE-RETENTION-DESIGN-GATE.md

Status: **Accepted**.

## 3. What Is Already Complete

The project has progressed through the earlier milestone sequence. Those milestones are historical context, not current execution state. The exact completed milestone list and sequencing are authoritative in:

docs/ROADMAP.md

Do not use old conversation summaries, old branch names, or stale milestone statements as the current project position.

## 4. Authority Order

When information conflicts, use this order:

1. GitHub main repository state
2. Open PRs and their actual heads/bases
3. docs/ROADMAP.md
4. Current design-gate documents
5. docs/DECISION_LOG.md
6. Other foundational documentation
7. Conversation history / memory

Conversation history is context, **not project state**.

## 5. Session Start Rule

Before doing project work:

1. Fetch the current main state.
2. Read the current roadmap position.
3. Inspect open PRs.
4. Identify the latest proposed/accepted design gate.
5. Verify the implementation branch before changing code.
6. State the current milestone and objective from GitHub.
7. Ignore superseded milestone context.

Do not infer the next task from an old conversation snapshot.

## 6. M56 Completion

M56 is implemented and merged through PR #148. Validated behavior includes owner-aware logical deletion, consistent read-side visibility, active-run protection, idempotent deletion, correlated run/snapshot hiding, and SQLite-transactional lifecycle mutation/audit coordination. Physical purge, undelete, and automatic retention remain outside the milestone.

## 7. Current M57 Boundary

M57 — Physical Purge is the active accepted design target.

The accepted gate is `docs/DEC-120-M57-PHYSICAL-PURGE-DESIGN-GATE.md`.

Implementation is authorized within that gate: operator-only physical purge, explicit or deterministic bounded selection, stable-ID ordering, one shared SQLite transaction per lifecycle unit, fail-stop destructive errors, restart-safe idempotency, mandatory management-audit recording, and optional dry-run. Automatic retention, archival storage, background workers, and new authorization roles remain out of scope.

## 8. Next Step

Create the M57 implementation branch from current `main`, then proceed RED → GREEN → review/refactor → CI verification.

## 9. Cleanup Rule

Historical branches and old milestone documents are part of project history. They should not be treated as current state merely because they still exist.

Old branches should only be deleted after verifying they are no longer needed.

## 10. AI Context Rule

If an AI assistant mentions a milestone that does not match this document and the current GitHub roadmap/PR state, it must stop and re-synchronize with GitHub before continuing.

**The repository must be understandable without the conversation.**
