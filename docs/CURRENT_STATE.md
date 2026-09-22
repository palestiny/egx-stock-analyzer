# EGX Stock Analyzer — Current State

**Authority:** GitHub `main` + current open pull requests  
**Last verified:** 2026-09-22  
**Repository:** palestiny/egx-stock-analyzer

## 1. Where We Are

The repository is at **M61 — Backtesting & Strategy Validation implementation**, following acceptance of DEC-126.

M56 — Analysis Run & Snapshot Retention and Deletion is complete.

M57 — Physical Purge is complete and hardened through PR #155.

M58 — Automatic Analysis Retention is complete through PR #157 at `f2294c34a10c994545e24175c956ee8524170142`.

M59 — Controlled Maintenance Trigger is complete through PR #159, merged at `c5c6c258508a60ac5872f4f4504fe55d440af30c`. The implementation head `9029a942c2705080f400b1b6ba7e993bd32c9ee9` passed GitHub Actions Tests Run #2687.

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

## 5. M58 Completion

M58 — Automatic Analysis Retention is **complete — implementation merged and verified**.

Design document:

`docs/DEC-122-M58-AUTOMATIC-RETENTION-DESIGN-GATE.md`

Status: **Accepted — implementation merged**.

M58 evaluates retention policy and triggering while reusing the existing M57 purge boundary rather than creating another destructive deletion path.

Accepted policy decisions:

1. Automatic retention is required.
2. Retention clock starts at logical deletion time (`deleted_at`).
3. Scope covers deleted runs/correlated lifecycle data and runless deleted snapshots, subject to M57 eligibility.
4. Preservation duration is configurable and system/operator-owned; the accepted duration is **30 days** from `deleted_at`.
5. Policy changes apply to current persisted state when retention executes.
6. Execution is controlled maintenance/scheduler-driven, not application-startup-driven; concrete trigger mapping remains an implementation-mapping task.
7. Every invocation is hard-bounded.
8. Dry-run/preview is non-destructive.
9. Automatic retention has a distinct audit operation identity.
10. Automatic retention is disabled by default and requires explicit enablement.
11. Invalid/unavailable configuration fails safe with no deletion.

Retention eligibility boundary:

- `deleted_at + 30 days <= now`.

Implementation mapping is composed in the application/infrastructure runtime, disabled by default, and not invoked from application startup. Controlled maintenance/scheduler invocation remains the trigger boundary. PR #157 is merged; no startup hook or background worker was introduced. M57 explicit privileged purge remains independently usable and authoritative for physical-reclamation semantics; M58 automatic retention reuses it.

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


## 7. M59 Completion

M59 — Controlled Maintenance Trigger is **complete — implementation merged and CI validated**.

Design document:

`docs/DEC-123-M59-CONTROLLED-MAINTENANCE-TRIGGER-DESIGN-GATE.md`

Accepted boundary:

```
External scheduler
      ↓
Maintenance command
      ↓
AutomaticAnalysisRetention
      ↓
PurgeAnalysisLifecycle
      ↓
SQLite lifecycle transaction
```

The repository now provides a controlled maintenance command with explicit disabled/completed/failed outcomes, dry-run support, bounded execution through M58/M57, operator identity, and process exit semantics. No OS/container scheduler or application background worker was added.

PR #159 was merged into `main` as `c5c6c258508a60ac5872f4f4504fe55d440af30c`. GitHub Actions Tests Run #2687 passed on implementation head `9029a942c2705080f400b1b6ba7e993bd32c9ee9`.

## 8. M60 Completion

M60 — Production Maintenance Scheduling is **complete — deployment mapping merged**.

DEC-124 is accepted. PR #162 was merged into `main` at `4fbf799f6262c4179946835ef4eae47cf8ecb6f1` after implementation-head CI passed in Tests Run #2709.

The repository provides the Windows Task Scheduler wrapper, registration script, and removal script under `deploy/windows/`. The accepted contract is daily at 03:30 local host time, IgnoreNew overlap handling, a 30-minute execution ceiling, and up to 3 scheduler restarts with 10-minute spacing.

The Windows scripts were not executed on a Windows host by this session, so host-level registration/runtime verification is not claimed. This is an explicit operational verification boundary, not an application correctness failure.

No application scheduler, background worker, second destructive path, or change to M57/M58/M59 semantics was introduced.

## 9. M61 Design Gate

DEC-126 proposes M61 as the next analytical milestone. Repository review found the core analysis pipeline already implemented, including technical/fundamental analysis, scoring, stock quality, entry context, entry quality, and opportunity classification. The next unresolved boundary is historical strategy validation.

Design gate: `docs/DEC-126-M61-BACKTESTING-DESIGN-GATE.md`.

Status: **Accepted — implementation in progress**. The accepted baseline is event-driven, leakage-safe, signal-after-close, next-bar-open, single long-only simulation with strategy invalidation as the primary exit, configured maximum-holding-period safety exit, and explicit cost/slippage semantics.
