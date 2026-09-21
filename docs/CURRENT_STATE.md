# EGX Stock Analyzer — Current State

**Authority:** GitHub `main` + current open pull requests  
**Last verified:** 2026-09-21  
**Repository:** palestiny/egx-stock-analyzer

## 1. Where We Are

The repository is currently at **M57 completion / M58 design**.

M56 — Analysis Run & Snapshot Retention and Deletion is complete.

M57 — Physical Purge is complete and hardened through PR #155.

M58 — Automatic Analysis Retention has an accepted policy direction. Implementation is not yet authorized because the preservation duration remains open.

## 2. Authority Order

When information conflicts, use this order:

1. GitHub `main`
2. Open pull requests and their actual heads/bases
3. `docs/ROADMAP.md`
4. Current design-gate documents
5. `docs/DECISION_LOG.md`
6. Other foundational documentation
7. Conversation history / memory

Conversation history is context, not project state.

## 3. M56 Completion

M56 established the accepted logical-deletion lifecycle for AnalysisRun and AnalysisResultRecord historical snapshots.

Validated behavior includes owner-aware logical deletion, consistent read-side visibility, active-run protection, idempotency, correlated run/snapshot hiding, and SQLite-transactional lifecycle mutation/audit coordination.

Physical purge and automatic retention were intentionally separated from M56.

## 4. M57 Completion

M57 — Physical Purge is complete within the accepted design boundary.

Design gate:

`docs/DEC-120-M57-PHYSICAL-PURGE-DESIGN-GATE.md`

Status: **Accepted**.

Implementation was merged through PR #151 at `3b20199581e2a6f313e3f83ca4c65780d5a9dbba`.

The implementation provides operator-only physical purge, explicit or deterministic bounded selection, stable-ID ordering, one SQLite transaction per lifecycle unit, fail-stop handling, restart-safe idempotency, management-audit recording, dry-run support, correlated lifecycle cleanup, runless snapshot purge, and visible/active protection.

The implementation head `95abdc209e779f184cc67da49f60c97a535f109a` passed GitHub Actions Tests Run #2536.

### M57 Hardening

PR #155 was merged as `ad10be12990abdfac56ec1459b163929b23c83c6`.

It synchronized the M57 completion state and hardened:

- operation identity propagation;
- dry-run audit recording;
- global deterministic candidate ordering;
- destructive row-count checks;
- current-state / README / engineering documentation.

GitHub Actions Tests Run #2571 passed for the hardening head.

## 5. M58 Current Boundary

M58 — Automatic Analysis Retention is a **proposed design gate**.

Design document:

`docs/DEC-122-M58-AUTOMATIC-RETENTION-DESIGN-GATE.md`

Status: **Accepted with one remaining policy value — implementation not authorized**.

M58 is intended to evaluate policy and triggering only and should reuse the existing M57 purge boundary rather than create another destructive deletion path.

Accepted policy decisions:

1. Automatic retention is required.
2. Retention clock starts at logical deletion time (`deleted_at`).
3. Scope covers deleted runs/correlated lifecycle data and runless deleted snapshots, subject to M57 eligibility.
4. Preservation duration is configurable and system/operator-owned; the actual duration remains open.
5. Policy changes apply to current persisted state when retention executes.
6. Execution is controlled maintenance/scheduler-driven, not application-startup-driven; concrete trigger mapping remains an implementation-mapping task.
7. Every invocation is hard-bounded.
8. Dry-run/preview is non-destructive.
9. Automatic retention has a distinct audit operation identity.
10. Automatic retention is disabled by default and requires explicit enablement.
11. Invalid/unavailable configuration fails safe with no deletion.

Remaining open policy value:

- the actual preservation duration.

Until the preservation duration is selected, M57 explicit privileged purge remains the authoritative physical-reclamation mechanism.

## 6. Session Start Rule

Before project work:

1. Fetch current `main`.
2. Read the current roadmap.
3. Inspect open PRs.
4. Identify the latest proposed/accepted design gate.
5. Verify the implementation branch before changing code.
6. State the current milestone and objective from GitHub.
7. Ignore superseded milestone context.

## 7. Cleanup Rule

Historical branches and old milestone documents are history, not current execution state. Old branches should only be deleted after verifying they are no longer needed.

The repository must remain understandable without the conversation.
