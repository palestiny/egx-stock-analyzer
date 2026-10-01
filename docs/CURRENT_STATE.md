# EGX Stock Analyzer — Current State

**Authority:** GitHub `main` + current open pull requests  
**Last verified:** 2026-10-01  
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


### M61 Engineering Hardening Review — PR #201

A project-wide engineering review was completed against the GitHub repository. The accepted hardening slice merged through PR #201 addresses the highest-confidence software-quality findings that could be completed without inventing external historical evidence:

- the historical-dataset backtest runner no longer imports infrastructure adapters directly; it now consumes the existing application-facing market-data and historical-fundamental contracts;
- deterministic integration tests are now explicitly classified and run in CI;
- live EGAL and provider smoke tests are explicitly classified as external rather than being silently mixed with deterministic CI coverage;
- pytest now declares both integration and external markers;
- unit, deterministic integration, and frontend/build CI jobs all pass on the merged hardening head.

This hardening does not claim that the real M61 historical dataset is accepted. Real historical acquisition, provenance closure, immutable dataset freeze, and evidence-backed Strategy v0 evaluation remain the analytical acceptance path.

## 10. M61 Current Checkpoint

The latest functional main merge is `d3b663156cc19a223f59d44b5fab74be49adec03` through PR #204; the follow-up state-documentation commit is `c3aa161420adb309a41cdd016977e6a4d53f43fa` (2026-10-01).

M61 remains in progress. DEC-130 is accepted, but the repository does **not** contain an accepted real historical dataset version. The current blocker is acquisition and provenance validation for the bounded ten-symbol cohort.

Operational checkpoint: `docs/M61-HISTORICAL-DATASET-ACQUISITION-STATUS.md`.

Current source-validation documentation now covers EGI, Mubasher, Mansa Markets, and the separate point-in-time financial-source boundary. Mansa's non-production acquisition probe is merged and CI-verified, but Mansa remains **NOT ACCEPTED** pending authenticated cohort extraction, provenance, and licensing/storage validation.

The immediate executable work remains:
1. run the merged Mansa market-source probe with valid access when the project key has the required history entitlement and preserve evidence only within permitted terms;
2. close the COMI financial provenance chain and extract one required Strategy v0 metric deterministically;
3. expand the same evidence package across the remaining nine symbols;
4. freeze the immutable M61 dataset manifest only after DEC-130 acceptance passes.

PR #180 and PR #181 are merged. PR #182 was superseded and closed after its branch diverged from main; its unique documentation content was reconstructed and merged through PR #183.

Branch deletion is not exposed by the current GitHub integration, so no branch deletion is claimed.


### M61 Backtest Warm-up Contract — PR #202

PR #202 is merged at `b1fe311f07f15a5228ba694c4f5fe6181c825984`. The backtest domain now models `warmup_bars` explicitly in `BacktestConfiguration`. Warm-up observations remain visible to strategy history for indicator/state construction, but signals are not evaluated before the configured evaluation boundary. Negative warm-up values are rejected.

This establishes the simulator contract only. It does **not** prove that the real M61 dataset contains the required 252 valid trading observations before the evaluation window. That remains part of dataset acceptance.

CI for PR #202 passed for unit tests, deterministic integration tests, and frontend tests.

### M61.3 Operational Conflict Durability — ACCEPTED

PR #204 is merged at d3b663156cc19a223f59d44b5fab74be49adec03. DEC-131 is now implemented at the software-boundary level: operational market data has an application-facing persistence port, a SQLite durable adapter, acquisition-linked observations, and a provider-neutral MarketDataConflictEvent. A conflicting duplicate never overwrites the existing observation; the conflicted acquisition and conflict event are committed durably before MarketDataConflictError is raised. Restart-safe deterministic tests verify acquisition round-trip, idempotent duplicates, conflict durability, acquisition linkage, and preservation of the original observation.

The PR #195 draft slice is superseded by PR #204 and should not be treated as an independent acceptance target. The immutable M61 historical dataset remains a separate blocker; DEC-131 acceptance does not imply that the real ten-symbol dataset or its raw-source evidence chain is accepted.

### M61.5 Operational Acquisition Provenance — ACCEPTED

DEC-132 is now accepted. The operational acquisition provenance boundary is implemented and verified through the existing application service and durable SQLite store. Successful, incomplete, and failed acquisitions retain requested/observed coverage, provider/source-symbol identity, stable stock identity, timestamps, row counts, and optional raw-artifact hashes. Acquisition history is queryable through the application-facing store boundary. This closes the operational provenance design gate without accepting the real immutable M61 evaluation dataset.

### M61.4 Raw-source Evidence Verification — IMPLEMENTED

PR #205 is merged at 2a3babd3b7227cc17d7868f52c1f6cf1dc9ebdbe. The historical dataset loader now exposes an explicit raw-source evidence acceptance check that validates dataset-relative evidence references and recomputes the preserved evidence SHA-256. Tamper and path-escape tests are covered by CI. This closes the software-side evidence-chain verification gap, but the synthetic repository fixture is not real market evidence; a real M61 dataset still requires an authenticated source artifact, preservation/usage rights, cohort coverage validation, and a frozen manifest.


### M61.6 Exact Raw Acquisition Artifact Integrity — ACCEPTED

PR #207 is merged at 802e38617fec2ab50a5d26660c51bdd50b113710 after GitHub Actions Tests Run #3225 passed on head e4c9d00679e1b85b0d6ee584ac589c8e1bfb7b61. The M61 acquisition probe now preserves the exact provider response bytes when raw preservation is enabled, so the recorded SHA-256 is tied to the actual preserved artifact rather than a re-serialized JSON representation. Deterministic validation also requires 252 observations before the 2021-01-01 evaluation start and checks evaluation-window/coverage evidence. This is an acquisition-tool integrity gate only; it does not accept any real provider artifact or the immutable M61 dataset.

The next acceptance boundary is now real COMI acquisition and provenance closure. No Strategy v0 performance conclusion should be made before the COMI artifact passes identity, coverage, data-quality, price-semantics, raw/transformed checksum, licensing/retention, and point-in-time financial evidence requirements.
