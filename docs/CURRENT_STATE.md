# EGX Stock Analyzer — Current State

**Authority:** GitHub `main` + current open pull requests  
**Last verified:** 2026-09-24  
**Repository:** palestiny/egx-stock-analyzer

## 1. Where We Are

The repository is at **M61 — Backtesting & Strategy Validation**, with the first deterministic simulator slice merged and verified.

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

Status: **Accepted — simulator + point-in-time historical input boundary + Strategy v0 integration merged and verified**. The accepted baseline is event-driven, leakage-safe, signal-after-close, next-bar-open, single long-only simulation with strategy invalidation as the primary exit, configured maximum-holding-period safety exit, and explicit cost/slippage semantics.

### M61 Historical Input Boundary

DEC-127 is accepted and its implementation is now on `main`. Historical financial facts are consumed only through the provider-neutral `HistoricalFinancialSnapshot` boundary, where a snapshot is eligible only when its explicit `available_at` is not later than the decision date. The point-in-time provider also selects the latest revision available for each financial period end before choosing the two latest eligible periods.

Current Yahoo statement selection by period_end remains unsuitable as evidence for leakage-safe historical performance claims because it does not prove public availability at the decision time.

PR #168 integrated Strategy v0 with the production `StockAnalysisPipeline` and the point-in-time fundamental provider. PR #169 repaired the dependency-ordering mistake by restoring the accepted DEC-127 prerequisite boundary on `main`; its head `b3a5e0bcaf8015307268c0d66df351c0cca21c32` passed GitHub Actions Tests Run #2782 and PR #169 was merged at `87b121964bc782fbe6ee1f58d2b9a4682db37a7c`.

M61 is **not complete yet**. The deterministic historical-dataset schema, acquisition gate, and integrity hardening are merged. The repository still needs actual historical coverage, data-quality boundary verification, deterministic Strategy v0 evaluation against real historical observations, aggregate/trade-level review, and final reproducibility validation before any performance conclusion is made.


### M61 Historical Dataset Boundary — DEC-128

DEC-128 is accepted. M61 will use a versioned external historical dataset as the production/backtesting evidence boundary, with a small repository-owned fixture dataset for deterministic tests.

The repository owns the dataset contract, schema, manifest, immutable version identity, integrity metadata, and loading rules. Large historical artifacts remain outside Git and are consumed only through an immutable dataset version and integrity hash.

The dataset must provide daily market observations and point-in-time financial snapshots with explicit availability and revision metadata. The physical artifact format remains a follow-up implementation decision.

M61 remains in progress. No real historical performance conclusion is valid until an actual dataset version is available and the full historical evaluation path is verified.


### M61 Dataset Schema — DEC-129

DEC-129 is accepted. The first historical dataset implementation uses deterministic UTF-8 CSV artifacts with canonical Decimal text, an immutable manifest, SHA-256 integrity checks, and repository fixtures using the same contract. Financial availability is date-based for the daily Strategy v0 boundary. Parquet remains deferred pending real scale requirements.


## 10. M61 Current Checkpoint

The latest main commit is `f78e6f0de411493887ef7b705fead7f0a77b5fa8` (2026-09-24), merged through PR #176. No pull requests are currently open.

M61 remains in progress. DEC-130 is accepted, but the repository does **not** contain an accepted real historical dataset version. The current blocker is acquisition and provenance validation for the bounded ten-symbol cohort.

Operational checkpoint: `docs/M61-HISTORICAL-DATASET-ACQUISITION-STATUS.md`.

The remaining historical-data branches are stale behind `main` and contain no unique commits relative to `main`; they are cleanup candidates. Branch deletion is not exposed by the current GitHub integration, so no deletion is claimed.

PR #176 passed GitHub Actions Tests Run #2903 on implementation head `1c82024b78275a1c94f07a705071904d4cc96467` before merge. No separate post-merge workflow run was exposed by the available GitHub integration, so no post-merge CI run is claimed.
