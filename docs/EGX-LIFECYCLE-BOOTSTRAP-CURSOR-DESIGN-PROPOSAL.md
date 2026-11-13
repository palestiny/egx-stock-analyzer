# EGX Lifecycle Bootstrap Cursor — Design Proposal

**Status:** PROPOSED — owner approval required before persistence or activation implementation  
**Decision context:** Owner approved Option 3 on 2026-11-13: no calendar activation until a controlled, durable cursor exists.  
**Related:** `docs/EGX-SESSION-CALENDAR-ACTIVATION-DESIGN-GATE.md`, `docs/OPPORTUNITY-LIFECYCLE-SCHEDULED-WORKER-DESIGN-GATE.md`, DEC-138, DEC-139.

## 1. Problem and non-goals

The lifecycle evaluator currently derives its cursor from the latest persisted completed daily-bar observation. If no observation exists, it starts from the opportunity's immutable publication date (Cairo-local date), then considers only completed sessions strictly after that date.

Option 3 requires a durable bootstrap cursor before calendar activation. The system currently has no separate persisted bootstrap record. Simply writing a date into the existing observation ledger would be unsafe: a bootstrap marker is not a market bar, is not evidence that any session was reconciled, and must not count toward the 20-session expiry rule.

This proposal introduces an explicit **pre-first-observation baseline** distinct from a **last-reconciled-session cursor**.

Non-goals:
- No provider selection, outreach, credential request, or provider-specific adapter.
- No synthetic candle, fake finality attestation, or claim that historical sessions were reconciled.
- No calendar activation, scheduled worker enablement, or lifecycle monitoring.
- No change to signal scoring, expiry semantics, or the existing rule that sessions on/before the publication date are excluded.

## 2. Proposed cursor semantics

A per-opportunity cursor has two semantically distinct positions:

1. **PUBLICATION_BASELINE** — an exclusive lower-bound date derived from the immutable `PUBLISHED` or `PUBLISHED_VERSION` history record in `Africa/Cairo`. It means *no session after this baseline has yet been proven reconciled*. It does not claim that any market session was processed.
2. **RECONCILED_SESSION** — the latest eligible EGX session for which a completed daily bar passed finality verification and the lifecycle observation, state/history update, and alert-outbox intent committed atomically.

The effective cursor is the latest RECONCILED_SESSION when present; otherwise it is the PUBLICATION_BASELINE. Sessions are always requested strictly after the effective cursor. A STALE gap does not advance the cursor. A rejected, provisional, missing, future, malformed, or unverified bar does not advance it.

The baseline preserves the evaluator's current publication-date-exclusive behavior. It must not be moved backward to include the publication date or forward to skip old sessions without a separate owner decision.

## 3. Proposed persistence contract

Add an append-only bootstrap record in the lifecycle Unit of Work, separate from daily-bar observations:

- `signal_id` — one immutable opportunity/revision identity; never share a cursor across parent and child revisions.
- `baseline_date` — Cairo-local date derived from the first publication event for that signal identity.
- `publication_event` and `publication_recorded_at` — provenance for the baseline derivation.
- `bootstrapped_by` — individually authenticated operator identity or explicitly approved system principal.
- `reason` — non-empty bootstrap reason.
- `calendar_version` — published candidate calendar version against which coverage was checked; not proof of activation or market-data finality.
- `recorded_at` — timezone-aware audit timestamp.
- deterministic bootstrap identity / idempotency key derived from `signal_id`, baseline date, and calendar version.

The record is immutable and append-only. Repeating the same bootstrap is idempotent. A conflicting baseline, publication provenance, or calendar version is rejected; it cannot overwrite the earlier record. A changed candidate calendar requires a new explicit bootstrap/coverage review event, not mutation of the old record.

The current completed-observation table remains the source of truth for RECONCILED_SESSION. Observation persistence and cursor advancement must remain in the same lifecycle Unit of Work transaction; do not create a second independently updated mutable cursor that can drift from observations.

## 4. Bootstrap workflow

1. An individually attributable operator selects a published calendar version and submits a reason for the controlled bootstrap.
2. The system loads all currently ACTIVE published opportunity identities, including latest active revisions only.
3. For each opportunity, it derives the baseline from the immutable publication history record; it does not accept an arbitrary date from the client.
4. It verifies that the candidate calendar explicitly covers every date required from the baseline through the next scheduled evaluation date. It must not infer weekends or holidays.
5. It writes all bootstrap records and one append-only batch audit result atomically, or writes none. The operation is restart-safe and idempotent.
6. It reports per-opportunity coverage gaps and blocks the batch if any in-scope opportunity cannot be covered. No partial batch may be treated as activation-ready.
7. Calendar activation remains a separate audited operation and still requires all provider-finality, individual-operator, deployment, and end-to-end gates.

For opportunities published after activation, publication must create the baseline record transactionally with the publication event, or a pre-evaluation reconciliation step must create and verify it before that opportunity is eligible for worker processing. The implementation must choose one path and test crash/retry behavior; it must never evaluate an opportunity with no baseline record.

## 5. Activation validation

Activation must reject unless:
- The candidate calendar exists, passes content-hash integrity validation, and is evidence-accepted/published.
- Every currently ACTIVE published opportunity/revision has exactly one valid bootstrap baseline for the candidate version.
- Every required date after each baseline through the next scheduled evaluation date is explicitly covered.
- No calendar gaps, unresolved bootstrap conflicts, or incomplete bootstrap batch exist.
- The activation actor is individually attributable and the reason is non-empty.
- Pointer change and append-only activation event commit atomically.

Rollback re-runs the same validation against the current active-opportunity set and current cursor state. Previously active does not mean currently safe.

## 6. Tests required before implementation is accepted

### Domain / application
- Baseline derives from immutable publication history in Cairo time.
- Empty/missing publication history blocks bootstrap.
- Parent and child revisions receive distinct cursor identities and correct independent baselines.
- Baseline is not counted as a processed eligible session and cannot cause expiry.
- Latest reconciled observation supersedes the baseline as the effective cursor.
- STALE gap and all rejected/unverified bar outcomes leave the cursor unchanged.
- Bootstrap is idempotent for identical inputs and rejects conflicting replay.
- A newly published active opportunity cannot enter evaluation without a baseline.

### SQLite / Unit of Work
- Bootstrap record is append-only and survives restart.
- Bootstrap batch and its audit result are all-or-nothing.
- Failure on any opportunity leaves no partial bootstrap records.
- Lifecycle observation and effective-cursor advancement are atomic.
- Concurrent duplicate bootstrap attempts serialize and produce one logical result.
- A failed lifecycle write does not advance the cursor.
- Migration is backward-compatible with existing databases and does not synthesize cursor records for historical observations without explicit provenance.

### Calendar activation / API
- Missing baseline, wrong calendar version, uncovered intermediate date, or uncovered next scheduled session rejects activation.
- Rollback revalidates current coverage.
- Actor comes from authenticated principal, never request body.
- Failed activation preserves pointer and appends no success audit event.
- Activation never proves provider finality or enables monitoring by itself.

## 7. Risks and alternatives

| Design | Benefit | Risk / cost |
|---|---|---|
| **Separate append-only publication baseline (recommended)** | Makes the first lower bound durable without pretending a candle was observed; preserves existing publication-date semantics | Adds a lifecycle bootstrap record, batch workflow, and revision-aware tests |
| Require one real finality-verified bar before activation | No separate baseline record | Circular operational dependency: the evaluator currently requires an active calendar and provider finality before it can create the first observation |
| Reuse the daily-observation table with a fake marker | Smaller schema change | Rejected: corrupts evidence semantics, can distort expiry, and risks treating a marker as market data |

## 8. Owner decision requested

Approve or reject the **PUBLICATION_BASELINE / RECONCILED_SESSION** split and the append-only per-opportunity bootstrap-record design.

Recommendation: approve this proposal. It gives Option 3 a precise, auditable meaning while preserving the current evaluator's publication-date-exclusive behavior and preventing bootstrap metadata from masquerading as completed market evidence.

Until this decision and implementation are complete, calendar activation, scheduled lifecycle execution, and production monitoring remain disabled.
