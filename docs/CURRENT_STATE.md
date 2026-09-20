# EGX Stock Analyzer — Current State

**Authority:** GitHub main + current open pull requests  
**Last verified:** 2026-09-20  
**Repository:** palestiny/egx-stock-analyzer

## 1. Where We Are

The repository is **past the earlier milestone sequence and is currently at M56**.

The current roadmap position is **M56 — Analysis Run & Snapshot Retention and Deletion**.

M56 is currently a **design-stage milestone**. Its design gate is proposed and destructive implementation is blocked until the remaining owner-controlled lifecycle decisions are explicitly accepted.

Latest M56 design synchronization:

- **PR #145** — docs: clarify accepted M56 lifecycle engineering boundary — merged at `9c435668fad08c963bc1fab4aeb422532c16f386`.
- **PR #147** — docs(m56): sync current state after lifecycle design clarification — merged at `65d70c921ed244120be612f0c14bb07178bc9948`.
- Purpose: keep the current-state document synchronized with the proposed M56 gate without silently accepting unresolved destructive lifecycle policy.

Current owner-decision tracking issue:

- **Issue #146** — resolve owner-controlled lifecycle decisions before destructive implementation

The latest verified merged main commit is:

65d70c921ed244120be612f0c14bb07178bc9948

Merge message:

Merge pull request #147 from palestiny/m56-design-state-sync

docs(m56): sync current state after lifecycle design clarification

## 2. Current M56 Boundary

M56 concerns the lifecycle of:

- AnalysisRun
- AnalysisResultRecord historical snapshots

The current design work is about retention, logical deletion, physical purge, ownership, authorization, run/snapshot correlation, auditability, transaction coordination, concurrency, and read-side behavior after lifecycle changes.

**No destructive lifecycle implementation is currently authorized.**

The latest design gate is:

docs/DEC-118-M56-ANALYSIS-LIFECYCLE-RETENTION-DESIGN-GATE.md

Status: **Proposed**.

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

## 6. M56 Immediate Next Step

The immediate work is **M56 design cleanup and decision readiness**, not any superseded milestone.

Owner-controlled decisions must remain explicit. Architecture recommendations must not silently become product policy.

## 7. Cleanup Rule

Historical branches and old milestone documents are part of project history. They should not be treated as current state merely because they still exist.

Old branches should only be deleted after verifying they are no longer needed.

## 8. AI Context Rule

If an AI assistant mentions a milestone that does not match this document and the current GitHub roadmap/PR state, it must stop and re-synchronize with GitHub before continuing.

**The repository must be understandable without the conversation.**
