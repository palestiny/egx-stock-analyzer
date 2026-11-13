# Session Opportunity Report Scheduler — Design Gate

**Status:** Design required; implementation not authorized by this document alone  
**Scope:** Non-M61 session-report generation, durable scheduling, and Telegram delivery  
**Related owner policy:** DEC-135 (accepted 2026-10-31)  
**Related prior decision:** DEC-051 explicitly deferred EGX calendar, holidays, market-close calculation, recurring schedules, persistence, and timezone conversion policy.

## 1. Current verified baseline

The repository currently contains:

- `BuildSessionOpportunityLedger`, which builds a point-in-time report for a supplied EGX session date and timezone-aware `generated_at` cutoff.
- `SQLiteSessionOpportunityReportStore`, which persists immutable snapshots and supports latest-as-of reads.
- PR #441 exposes each opportunity's original signal source-data timestamp and the outcome observation's source-data timestamp in API responses and immutable snapshots. These are provenance timestamps only; they do not classify data as fresh or stale.
- Authenticated API routes for building, persisting, and reading reports.
- Telegram infrastructure and durable delivery machinery for signal-opportunity notifications.

The following are **not** implemented as a complete session-report capability:

- No session-report scheduler is composed into `InfrastructureRuntime` or application lifespan.
- The existing `InProcessScheduler` is memory-only and one-shot; it does not survive process restart or provide durable occurrence claims.
- `RunDurableScheduledWorkflow` is coupled to configured market analysis and its analysis/delivery result contract. It is not a session-report scheduler.
- No end-to-end scheduled report delivery contract proves idempotent generation and delivery, duplicate suppression, recovery, or operational failure visibility.

Therefore reports must currently be described as API/manual, not automatically scheduled or delivered.

## 2. Owner-approved constraints

The accepted policy establishes:

- Report timestamps and session interpretation use the Cairo exchange timezone (`Africa/Cairo`).
- Generation must be durable and idempotent.
- Corrections/reruns must be traceable and must not cause duplicate distribution.
- Reports should explain the session, opportunities published, lifecycle/status changes, resolved versus unresolved market-proxy outcomes, data freshness, and methodology limitations.
- Market-proxy outcomes are not actual executions or portfolio P&L.
- Stale, missing, future-dated, or invalid source data must not be presented as current evidence.

These constraints do **not** specify an exact report run time, official holiday source, calendar update process, or data-correction publication policy.

## 3. Unresolved inputs — do not guess

Before implementation, the following must be established and recorded:

1. **Session calendar authority:** an authoritative EGX source for trading days, official holidays, exceptional closures, and any amended sessions; its access, retention, and reuse terms; and how updates are verified.
2. **Session-close semantics:** the exact event/time that means a session is complete for report purposes, including any post-close publication/data-settlement delay. Do not infer this from a generic weekday schedule.
3. **Calendar operations:** who owns calendar updates, how missing/late notices are handled, and what the system does when calendar data is unavailable or stale.
4. **Correction policy:** which late/corrected market data or signal events justify a revised report, how a revision is labelled, and whether/when subscribers receive a correction.
5. **Delivery policy:** whether reports go to every entitled linked Telegram account or a configured subscriber segment, and how entitlement changes between generation and dispatch are treated.
6. **Operational ownership:** alerting/escalation for missed sessions, repeated failures, blocked data, and ambiguous Telegram delivery outcomes.

Fail closed when required calendar or source evidence is unavailable. Do not silently fall back to Sunday–Thursday weekdays as proof of an open exchange session.

## 4. Architecture options

### A. In-process timer

A process-local timer invokes report generation at a configured Cairo time.

- Pros: small initial implementation.
- Cons: lost on restart, duplicate execution across replicas, missed-run recovery and correction semantics require separate mechanisms.
- Assessment: **not sufficient** for the accepted durable/idempotent policy.

### B. External cron calling an authenticated endpoint

A deployment scheduler calls an idempotent occurrence endpoint.

- Pros: clear separation between deployment timing and application use case; easy to operate in a single deployment.
- Cons: external scheduler configuration and availability become critical dependencies; a cron timestamp alone does not prove the exchange session was open or complete; missed triggers require reconciliation.
- Assessment: viable only with durable occurrence reservation, calendar validation, deployment ownership, and a reconciliation process.

### C. Durable occurrence ledger plus worker

A calendar/schedule policy derives eligible session occurrences; a durable store reserves each occurrence; a worker claims due work, builds a report using a stable cutoff, persists a version, and dispatches through a report-specific idempotent delivery contract.

- Pros: supports multi-instance claims, restart recovery, duplicate suppression, explicit correction versions, and operational history.
- Cons: more implementation and operational complexity; requires the unresolved calendar, cutoff, and correction policies above.
- Assessment: **recommended target** because it best satisfies the accepted durability and traceability requirements.

## 5. Recommended boundaries

Keep policy and orchestration separate:

- `TradingSessionCalendar`: answers whether a date/session was officially scheduled, closed, exceptional, or unknown; returns provenance and calendar version.
- `SessionReportSchedulePolicy`: determines when a verified session becomes eligible for reporting. It must not invent close times or holidays.
- `SessionReportOccurrence`: stable identity for one reportable session and policy version.
- `SessionReportOccurrenceStore`: atomically reserves/claims occurrences and records state, attempts, timestamps, and failure reason.
- `GenerateSessionOpportunityReport`: builds and persists a report with a deterministic occurrence cutoff and explicit revision identity.
- `DispatchSessionOpportunityReport`: delivers the persisted report through a report-specific durable/idempotent delivery contract; do not overload signal-opportunity semantics without a reviewed abstraction.
- `SessionReportWorker`: coordinates claim → generate → persist → dispatch → terminal/retry state, and supports startup recovery/reconciliation.
- API/operator read models: expose occurrence state, last success, blocked reason, attempts, revision history, and delivery state.

The existing signal-alert outbox's ambiguous Telegram outcomes must remain conservative: an ambiguous send is not automatically resent. Report delivery must preserve equivalent no-duplicate behavior.

## 6. Idempotency and correction semantics to design

- One stable occurrence identity per exchange session and schedule-policy version.
- Repeated triggers for the same occurrence return/reconcile the same durable execution; they do not create a second report delivery.
- A retry uses the original occurrence cutoff, not a newly sampled `now`.
- A data correction creates an explicit new report revision linked to the prior revision; it must not overwrite the immutable original snapshot.
- Dispatch identity is per report revision and recipient. Reconciliation of an ambiguous delivery must not trigger blind resend.
- Entitlement and recipient eligibility are evaluated at a documented point in the dispatch flow and rechecked where required by the existing delivery contract.

## 6.1 Verified correction-lineage gap (design proposal only)

Repository inspection on 2026-11-13 confirms the current persistence contracts are intentionally immutable but do not yet model corrections:

- `TrackRecordStore` exposes one `SignalOutcomeRecord` per `signal_id`. The SQLite implementation uses `signal_id` as the primary key; an identical replay is a no-op and a different payload for that signal is rejected.
- `SignalOutcomeRecord` has no correction/revision identity, predecessor link, correction reason, or correcting-actor metadata.
- `SQLiteSessionOpportunityReportStore` identifies a snapshot by `(session_date, methodology_version, generated_at)`. It accepts an identical replay and rejects different content for the same identity. It has no explicit report-revision or supersedes relationship.
- Consequently, the current behavior is safe against silent overwrite, but an operator cannot append a corrected outcome for the same signal and publish a traceable corrected report under a distinct revision identity.

### Proposed model — not approved for implementation

1. Preserve each original outcome and report snapshot as immutable records.
2. Introduce an append-only outcome-revision identity, separate from `signal_id`, with at minimum: revision ID, signal ID, monotonically assigned revision number, optional superseded revision ID, correction reason, recorded-at timestamp, and the complete validated outcome payload including source-data provenance.
3. Require correction authority/actor provenance to be explicit. Do not infer an actor from an API token or use a generic system identity until the operator authorization and audit contract is specified.
4. Resolve the effective outcome revision as-of a report cutoff using the revision's recorded-at time; retain both source observation time and correction-recorded time. This prevents a later correction from rewriting what an earlier report knew.
5. Give each report snapshot an explicit revision ID and predecessor/supersedes link. Keep the existing session/methodology/cutoff identity as occurrence context, not as the sole identity for corrected content.
6. A corrected report must reference the exact outcome revision set it used, explain what changed, and never update the original snapshot in place. Delivery of corrections remains separately gated by the unresolved audience, entitlement, and duplicate-delivery policy.

### Additional verified read-selection gap: methodology versions

The current snapshot primary key permits more than one methodology version for the same session and UTC generation timestamp. However, `get_latest(session_date, as_of=...)` orders by `generated_at DESC, methodology_version ASC` and returns one row, while the authenticated GET API does not accept a methodology-version selector. If two methodology versions share the same generation timestamp, the endpoint silently chooses the lexicographically first version. That ordering is deterministic but is not a documented business rule and must not be mistaken for "the latest" methodology.

**Proposed resolution — design only:** expose an optional exact `methodology_version` selector. If omitted and the latest timestamp has multiple methodology versions, return an explicit ambiguity result (or require an owner-selected default policy); never use lexical ordering as a proxy for semantic recency. Define whether a new methodology version supersedes an older one for the same session before implementing an automatic default. Add tests for same-cutoff multi-methodology snapshots, explicit selection, and ambiguous unqualified reads.

**Gate:** no API or persistence contract changed in this increment.

---

### Decisions still required before implementation

- Who may authorize an outcome correction, and what durable actor identity is recorded?
- Is a correction a new revision of the original outcome, a retraction followed by a replacement, or both depending on error type?
- How are competing corrections serialized and how is the effective revision selected when corrections arrive out of order?
- Does a correction to an old signal trigger a new report for the original session, a current-session correction notice, or both?
- Which subscribers receive corrections, and what happens when entitlement has changed since the original report?
- How are ambiguous Telegram delivery outcomes reconciled without duplicate sends?

**Gate:** The proposal is a design finding only. Do not change the current one-outcome-per-signal or immutable-snapshot contracts until these decisions are approved. Do not add correction delivery or activate scheduling as part of this gap closure.

---

## 7. Required verification before acceptance

### Domain and policy
- Verified open session, official holiday, exceptional closure, and unknown/stale calendar.
- Cairo timezone and daylight-saving transitions.
- Session-close boundary and configured post-close delay.
- Stable occurrence identity and deterministic cutoff.
- Late, corrected, missing, and stale market data.
- Revision lineage and no mutation of prior snapshots.

### Persistence and concurrency
- Concurrent claims by multiple workers.
- Duplicate trigger and duplicate API invocation.
- Process crash before generation, after report persistence, and during dispatch.
- Recovery after restart and missed-occurrence reconciliation.
- Idempotent report persistence and recipient delivery.
- Optimistic concurrency/lease fencing and bounded retry exhaustion.

### End-to-end API/Telegram
- Scheduled report includes required session summary and methodology/freshness limitations.
- Entitlement changes and unlinked recipients.
- Definite rejection versus ambiguous Telegram outcome.
- Operator-visible failure and reconciliation path.
- No duplicate subscriber delivery after retries or corrections.

### Release evidence
- CI green on the final merged commit.
- Integration test proving the complete calendar → occurrence → report snapshot → recipient dispatch path.
- Deployment scheduler/worker configuration and restart/recovery runbook.
- A monitored missed-session and delivery-failure alert.

## 8. Gate decision

**Current result: GAP — do not implement a guessed schedule.**

The implementation gap is confirmed, but schedule time, authoritative calendar, correction policy, and delivery audience semantics are not yet evidenced. The recommended durable occurrence-ledger architecture is a proposal, not a silently accepted architecture decision.

Until those inputs are resolved and the implementation passes the acceptance matrix, the product must describe session reports as manually/API generated. M61 remains paused and is outside this gate.
