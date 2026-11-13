# EGX Lifecycle Bootstrap Cursor — Approved Design

**Status:** OWNER-APPROVED DESIGN — IMPLEMENTATION COMPLETE IN PR #515; production activation remains blocked  
**Decision date:** 2026-11-13  
**Decision record:** `docs/EGX-LIFECYCLE-BOOTSTRAP-CURSOR-OWNER-DECISION.md`  
**Related:** `docs/EGX-SESSION-CALENDAR-ACTIVATION-DESIGN-GATE.md`, `docs/OPPORTUNITY-LIFECYCLE-SCHEDULED-WORKER-DESIGN-GATE.md`, DEC-138, DEC-139.

## 1. Problem and non-goals

The lifecycle evaluator currently derives its cursor from the latest persisted completed daily-bar observation. If no observation exists, it starts from the opportunity's immutable publication date (Cairo-local date), then considers only completed sessions strictly after that date.

Option 3 requires a durable bootstrap record before calendar activation. A bootstrap marker is not a market bar, is not evidence that any market session was reconciled, and must not count toward the 20-session expiry rule.

Non-goals:
- No provider selection, outreach, credential request, or provider-specific adapter.
- No synthetic candle, fake finality attestation, or claim that historical sessions were reconciled.
- No calendar activation, scheduled worker enablement, or lifecycle monitoring.
- No change to signal scoring, expiry semantics, or the existing rule that sessions on/before the publication date are excluded.

## 2. Approved cursor semantics

1. **PUBLICATION_BASELINE** — exclusive lower-bound date derived from the immutable publication history record for the exact opportunity/revision identity, in `Africa/Cairo`. It proves no market session was reconciled.
2. **RECONCILED_SESSION** — latest eligible EGX session whose completed daily bar passed provider-finality verification and whose observation, lifecycle state/history, and alert-outbox intent committed atomically.

The effective cursor is the latest RECONCILED_SESSION when present; otherwise it is PUBLICATION_BASELINE. Sessions are requested strictly after it. A missing, stale, rejected, provisional, malformed, future, or unverified bar does not advance it.

The baseline preserves the current publication-date-exclusive behavior. It is never a synthetic observation and is never counted toward the 20-session expiry threshold.

## 3. Approved persistence contract

The lifecycle Unit of Work will persist an append-only bootstrap record separate from daily-bar observations, with:
- immutable `signal_id` (one identity per opportunity revision);
- `baseline_date` derived from publication history, never accepted from client input;
- publication event and publication timestamp provenance;
- individually authenticated `bootstrapped_by`;
- non-empty operator reason;
- candidate `calendar_version` used for explicit coverage validation;
- timezone-aware `recorded_at`;
- deterministic idempotency identity.

Identical retries are idempotent. Conflicting baseline, publication provenance, or calendar version is rejected. A later calendar review is a new append-only event, never an update to the prior record.

The observation ledger remains the source of truth for RECONCILED_SESSION. No separately mutable reconciled cursor is introduced.

## 4. Selected implementation path: pre-evaluation bootstrap

**Decision:** use a controlled pre-evaluation bootstrap workflow, not publication-time coupling.

Reason: the existing `PublishSignalOpportunity` currently persists signal history and outbox intent through separate abstractions, while the lifecycle Unit of Work is the established atomic boundary for lifecycle evidence. Retrofitting publication atomicity would expand this work into a separate publication/outbox architecture change. The pre-evaluation path is smaller and preserves the accepted safety boundary.

Rules:
1. A new or revised opportunity is not eligible for lifecycle evaluation until a valid bootstrap record exists.
2. The bootstrap application workflow derives baseline and provenance from immutable publication history. It does not accept an arbitrary baseline date.
3. It checks the candidate published calendar's explicit coverage from the baseline through the next scheduled evaluation date; it does not infer weekends or holidays.
4. It writes every in-scope active latest revision's bootstrap record and one batch audit result in a single Unit of Work transaction, or writes none.
5. Repeated identical batches are idempotent; conflicting retries fail closed.
6. After activation, every newly published opportunity must pass this same bootstrap gate before the worker may evaluate it.
7. Bootstrap does not activate the calendar, prove provider finality, or enable the worker.

## 5. Activation validation

Activation must reject unless:
- candidate calendar exists, passes content-hash integrity, and is evidence-accepted/published;
- every active latest opportunity revision has exactly one valid bootstrap record for the candidate calendar version;
- every required date after each baseline through the next scheduled evaluation date is explicitly covered;
- no gaps, unresolved bootstrap conflicts, or incomplete batch exists;
- actor is individually attributable and reason is non-empty;
- pointer change and append-only activation event commit atomically.

Rollback repeats validation against current active opportunities and cursors. Previously active does not mean currently safe.

## 6. Acceptance tests

### Domain / application
- Baseline derives from immutable publication history in Cairo time.
- Missing/ambiguous publication history blocks bootstrap.
- Parent and child revisions have distinct cursor identities and independent baselines.
- Baseline is not counted as a processed session or toward expiry.
- Latest reconciled observation supersedes baseline as effective cursor.
- Missing/ineligible bars and stale gaps do not advance cursor.
- Identical bootstrap retry is idempotent; conflicting replay is rejected.
- Newly published active opportunity cannot enter evaluation without a baseline.

### SQLite / Unit of Work
- Bootstrap and batch audit are append-only and survive restart.
- Batch writes are all-or-nothing.
- Failure on any opportunity leaves no partial records.
- Lifecycle observation and state/history/outbox intent remain atomic.
- Concurrent duplicate bootstrap attempts serialize safely.
- Migration is backward-compatible and does not synthesize records for historical observations without provenance.

### Calendar activation / API
- Missing baseline, wrong calendar version, uncovered intermediate date, or uncovered next scheduled session rejects activation.
- Rollback revalidates current coverage.
- Actor comes from authenticated principal, never request body.
- Failed activation preserves pointer and appends no success audit.
- Activation does not prove finality or enable monitoring.

## 7. Implementation checkpoint — 2026-11-13

The first implementation increment is present on the PR branch:
- Lifecycle Unit of Work defines bootstrap batch and per-opportunity record contracts.
- In-memory transaction adapter supports append-only bootstrap writes and rollback snapshots.
- SQLite has separate batch and per-opportunity tables, per-opportunity/calendar uniqueness, publication-identity foreign keys, and no-update/no-delete triggers.
- Persistence enforces SHA-256 digest shape, Cairo-derived baseline consistency, publication-before-bootstrap ordering, deterministic per-opportunity idempotency keys, and timestamp-independent identical retries.
- `BootstrapOpportunityLifecycle` derives publication baselines from immutable `PUBLISHED` / `PUBLISHED_VERSION` history in `Africa/Cairo`, selects active latest revisions only, validates explicit calendar coverage through the caller-supplied next evaluation session, and writes the batch atomically.
- Lifecycle evaluation now rejects an unbootstrapped opportunity, a publication-provenance mismatch, or a superseded parent revision.
- Tests cover Cairo date conversion, revision independence, retries, calendar coverage failure, unpublished opportunities, and evaluator eligibility guards.

**Verification: PASS on exact head `f27065858f72035d39c56f1942b4f24cdb89c584` (GitHub Actions run `43412122508`; all six jobs successful: unit tests, integration tests, lint/type-check within unit job, frontend tests, daily-history audit report, dependency audit, and container build).** This accepts the current persistence/application bootstrap increment at code-CI level. It does not accept calendar activation, provider finality, scheduled worker, or production E2E.

## 8. Risks and rejected alternatives

| Design | Decision |
|---|---|
| Separate append-only publication baseline | Approved |
| Require a real finality-verified bar before bootstrap | Rejected: circular dependency on active calendar/provider |
| Reuse daily-observation table with fake marker | Rejected: corrupts evidence semantics and may distort expiry |
| Couple publication/outbox refactor into this change | Deferred: expands scope; pre-evaluation gate provides safe eligibility boundary |

Until implementation and independent provider/calendar/worker/E2E gates pass, calendar activation, scheduled lifecycle execution, and production monitoring remain disabled.


## Calendar activation validation increment (2026-11-13)

Added `ValidateLifecycleCalendarActivation` as a fail-closed application validation service. It does not activate or mutate the active calendar pointer.

The validator requires an injected trusted evaluation-schedule port; callers cannot submit the next evaluation date. It checks candidate publication metadata and timezone, every latest active opportunity/revision, exact matching publication baseline for the candidate calendar version, complete append-only bootstrap batch counts, explicit day-by-day calendar coverage through the trusted next evaluation date, a trading-session next date, and compatibility of any latest reconciled-session cursor with the candidate calendar.

The service returns structured blockers and is not wired to an activation endpoint. There is no production trusted schedule adapter yet, so production calendar activation remains unavailable. This is intentional fail-closed behavior, not an operational activation approval.

The future evaluation date must be explicitly `SCHEDULED` (not merely historical `CLOSED` or currently `OPEN`). A persisted reconciled cursor must be strictly after the publication baseline, before the next evaluation date, and explicitly `CLOSED` in the candidate calendar. A candidate with no active latest opportunities is eligible with zero cursor checks; there is no active lifecycle workload to reconcile.

Regression tests now cover a non-closed cursor rejection, a closed cursor acceptance, rollback-time revalidation against the currently persisted cursor, and the no-active-opportunities case. The validator remains a pure precondition check: it does not serialize validation with calendar pointer mutation. A controlled activation/rollback transaction is still required before operational use.

Historical checkpoint: exact-head CI for `8c40230` passed all six jobs (run `43414055075`). Cursor/rollback/empty-workload tests and stricter future-session checks were subsequently added in `6578e4a` and `81a5e8d`; the then-pending CI state was superseded by later exact-head verification recorded in Section 8.


## Owner-approved trusted schedule policy and adapter — 2026-11-13

**Owner decision:** approved the following source-selection rule for the next evaluation date:

1. Initial activation (no currently active calendar): derive the first future `SCHEDULED` date from the published candidate calendar.
2. Calendar change or rollback (an active calendar exists): derive the first future `SCHEDULED` date from the currently active calendar, then require the candidate calendar to cover that exact date and the full opportunity baseline/cursor range.
3. If the selected source calendar is absent or has no future `SCHEDULED` date, return no date and fail closed. Do not fall back from an active calendar to the candidate calendar.

Implementation added as `CalendarBackedLifecycleEvaluationSchedule`, with tests for initial activation, change/rollback source preservation, no-future-session fail-closed behavior, and missing candidate fail-closed behavior.

**Historical boundary at this checkpoint:** the adapter was a provider-neutral schedule source and was not yet serialized with pointer mutation. This gap was subsequently closed by the SQLite activation coordinator described below, which joins the lifecycle Unit of Work to the calendar repository's `BEGIN IMMEDIATE` transaction and atomically validates, changes the pointer, and appends the audit event. The coordinator remains an internal capability only; no operational activation endpoint/command is exposed.


## Atomic calendar activation implementation increment — 2026-11-13

A provider-neutral SQLite activation coordinator is now implemented on the PR branch:

- `SQLiteSessionCalendarRepository.change_active_atomically` starts `BEGIN IMMEDIATE`, validates the candidate calendar integrity and rollback eligibility, invokes the lifecycle precondition callback, then updates the active pointer and appends the activation audit event before one commit.
- `SQLiteSignalLifecycleUnitOfWork.execute_in_transaction` lets lifecycle bootstrap/cursor reads join the caller-owned SQLite transaction; it does not begin, commit, or close that transaction.
- `ValidateLifecycleCalendarActivation.execute` accepts the caller-owned lifecycle transaction and uses it for bootstrap batch/record and latest-observation reads. Its standalone precondition mode remains available for diagnostics, but only the coordinator serializes it with pointer mutation.
- `SQLiteLifecycleCalendarActivationCoordinator` is the controlled activation/rollback path. An ineligible result raises an internal rejection inside the transaction and returns a validation result with no activation event. Any unexpected validation, pointer, or audit failure rolls the transaction back.
- The coordinator verifies that the calendar repository and lifecycle UoW use the same SQLite database file. The validator's other history/calendar reads occur while `BEGIN IMMEDIATE` holds the SQLite write reservation, so another writer cannot change those records before pointer mutation.

Focused persistence tests cover joining the caller-owned transaction (no nested UoW), rejection with no pointer/audit change, audit-insert failure rolling back a pointer update, and refusal to coordinate repositories backed by different database files. A validator test covers use of a caller-owned lifecycle transaction.

**Important boundary:** this is an application/infrastructure capability and test increment only. No activation API route, admin UI, runtime activation command, production active-calendar change, worker, or monitoring has been wired or enabled. Provider-finality remains an independent blocker. Exact-head CI is required before treating this increment as verified.


## 8. Implementation completion and exact-head verification — 2026-11-13

The approved bootstrap design is implemented on PR #515:
- Append-only bootstrap batch and per-opportunity records are persisted separately from daily-bar evidence, with immutable publication provenance, calendar-version identity, digest/idempotency, and SQLite no-update/no-delete enforcement.
- The application workflow enumerates active latest immutable revisions, derives each Cairo-local baseline from `PUBLISHED` / `PUBLISHED_VERSION` history, verifies explicit calendar coverage, and persists the batch atomically.
- The evaluator rejects missing/mismatched bootstrap evidence and superseded parent revisions. Baselines remain exclusive lower bounds and are excluded from eligible-session expiry counts.
- Calendar activation validation checks all active latest revisions, matching bootstrap evidence, candidate coverage through a trusted calendar-backed next-evaluation date, and reconciled-cursor compatibility.
- A SQLite coordinator serializes authenticity preflight proof checks, lifecycle validation, active-pointer mutation, and append-only activation audit in one transaction. The coordinator is not exposed as an operational activation API/command.

The earlier implementation checkpoint `2585eb9cbd9ad4cf4f4f5883395987f2f054d9ee` passed all six GitHub Actions checks in run `43432642040`. Subsequent provider-neutral source-port/envelope code and gate-documentation reconciliation were added after that checkpoint and require exact-head CI. Repository CI does not establish a real provider, production calendar origin, deployment network/recovery behavior, worker, or end-to-end operation. Keep activation, worker, and monitoring disabled; PR #515 remains Draft and unmerged.
