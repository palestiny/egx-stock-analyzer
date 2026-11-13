# Outcome Event Ledger — Approved Design

**Status:** Owner-approved for implementation  
**Approved:** 2026-11-13  
**Scope:** Signal outcome knowledge-time integrity, corrections, and report provenance  
**Branch:** `feature/opportunity-lifecycle-completion`

## Problem

`SignalOutcomeRecord.observed_at` describes when the outcome was observed/effective. It does not describe when the application durably learned and recorded that outcome. The current session opportunity report selects outcomes using `observed_at <= generated_at`. A result entered after a report cutoff can therefore appear in a report generated before the application knew it.

The existing outcome store is keyed by `signal_id` and rejects a different payload for the same signal. It has no recording timestamp, correction chain, review event, or stable event provenance.

## Approved model

1. Introduce a separate append-only outcome event ledger. Do not reinterpret `observed_at` as knowledge time.
2. Every newly accepted initial outcome event receives a trusted, timezone-aware `recorded_at` generated at the persistence boundary. Callers cannot backdate this value.
3. Keep `observed_at` and `data_timestamp` as event/source-time fields. They remain distinct from `recorded_at`.
4. An outcome correction is a new event. It references the event it supersedes; it never overwrites or deletes the original event.
5. Corrections are pending until reviewed. Review is a separate append-only event with authenticated reviewer identity and decision. The correction author cannot review their own correction.
6. A rejected correction remains in the audit history but never becomes the current accepted outcome.
7. A report generated at cutoff T may use only outcome events durably recorded at or before T and eligible under the accepted review state as of T.
8. A report must retain the exact outcome event ID(s) used for each resolved outcome. Its snapshot remains immutable; later corrections do not rewrite prior reports.
9. Replay of the same event/request is idempotent. A conflicting replay or invalid supersession/review transition fails explicitly.
10. SQLite persistence must survive restart and enforce append-only behavior at the database boundary, not only in application methods.

## Legacy data policy

Existing `signal_outcomes` rows have no trustworthy recording timestamp. Their historical `recorded_at` is unknowable.

- Do not infer it from `observed_at`, `data_timestamp`, file modification time, or migration time.
- Do not backfill a fabricated timestamp.
- Preserve the legacy rows and expose them as `LEGACY_UNKNOWN` knowledge-time provenance.
- Legacy outcomes are not eligible for strict historical as-of reconstruction before an explicit, documented reconciliation process. They may be shown as legacy/current context only when clearly labeled as such.
- A migration timestamp may describe when migration ran, but must never be represented as the original recording time.

## Report selection semantics

For a report cutoff T:

- First filter the append-only event stream to events with `recorded_at <= T`.
- Resolve correction/review relationships using only decisions recorded by T.
- Select the latest eligible accepted outcome revision for the signal as of T.
- Preserve the selected event ID and its effective/source timestamps in the report entry.
- If no eligible event exists by T, the outcome remains unresolved in that historical report.

The existing publication/history cutoff remains based on its own durable `recorded_at` field.

## Implementation sequence

1. Add domain event types and an application event-store contract with deterministic in-memory behavior.
2. Add SQLite append-only event/review persistence, restart/idempotency/conflict tests, and safe schema migration. Keep legacy rows explicitly unknown.
3. Add correction submission and independent review application services with authenticated identities.
4. Integrate the report builder with the event ledger and persist outcome event provenance in immutable report snapshots and API responses.
5. Add regression tests for late-entered outcomes, corrections recorded after cutoff, accepted/rejected review timing, author self-review rejection, restart durability, idempotent replay, and immutable report provenance.
6. Run the full CI matrix on the exact resulting PR head. No completion claim until all required jobs finish successfully.

## Explicit non-goals and safety boundaries

- No provider/EGID contact or external evidence requests.
- No calendar activation, worker, scheduler, monitoring, or Telegram delivery activation.
- No M61 resumption and no canonical market-data changes.
- No mutation or deletion of legacy outcome rows.
- No rewrite of already persisted report snapshots.
- PR #515 remains open and Draft; do not merge or mark Ready without owner approval.

## Acceptance criteria

- A result observed at 10:00 but first recorded at 15:00 is absent from a report generated at 12:00 and may appear in a report generated after 15:00.
- A correction recorded/reviewed after a historical cutoff cannot alter the report's as-of state at that cutoff.
- The original event and every correction/review remain auditable.
- Every resolved report entry identifies the exact accepted event revision used.
- Legacy rows are never assigned fabricated historical knowledge times.
- All event transitions are deterministic, durable, idempotent where specified, and covered by tests.
