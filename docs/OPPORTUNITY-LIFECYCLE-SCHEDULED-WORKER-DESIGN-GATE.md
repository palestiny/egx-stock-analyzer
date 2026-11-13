# Opportunity Lifecycle Scheduled Worker — Design Gate

**Status:** PROPOSED / NOT WIRED / DISABLED — implementation is blocked by provider-finality and calendar-activation gates  
**Reviewed:** 2026-11-13  
**Related:** DEC-138, DEC-139, PR #515, `docs/EGX-SESSION-CALENDAR-ACTIVATION-DESIGN-GATE.md`, `docs/MARKET-DATA-PROVIDER-RELIABILITY-DESIGN-GATE.md`  
**Scope:** Durable daily scheduling and execution of the already implemented opportunity-session evaluator.

## 1. Executive decision

Do not enable or deploy a scheduled lifecycle worker yet.

The application already contains the per-opportunity evaluation logic in `EvaluateOpportunityLifecycleSessions`. It reconciles explicitly completed EGX sessions chronologically, uses the latest committed completed observation as the per-opportunity cursor, records missing/unverified-session gaps, stops at the first gap, and applies the 20-eligible-session expiry rule.

The missing part is a production orchestration boundary that discovers active opportunities, obtains eligible completed daily bars from an approved source, invokes the evaluator, and durably coordinates/retries the daily occurrence.

This worker must remain disabled until all activation gates in Section 8 pass. This design does not select a provider, authorize external contact, publish or activate a calendar, or enable lifecycle monitoring.

## 2. Verified existing building blocks

| Existing component | Verified responsibility | Limitation for worker use |
|---|---|---|
| `EvaluateOpportunityLifecycleSessions` | Reconciles a single opportunity against a supplied `bars_by_session` mapping and active calendar; blocks on missing, future, mismatched, or unverified bars | Does not acquire provider data or enumerate opportunities |
| `SignalHistoryStore` | Exposes a deterministic `latest_active_published_opportunities()` projection; SQLite selects latest signal revisions and their first publication event in one indexed query, excluding superseded parents and non-ACTIVE latest states | The projection is now reused by bootstrap and is covered for revision, unpublished, terminal, and restart behavior; realistic-volume query-plan/latency verification remains before worker-scale adoption |
| `SignalLifecycleOrchestrator` | Provides per-opportunity latest-observation cursor, append-only gap events, lifecycle transitions, expiry, and correction-aware history | Does not schedule or claim work |
| `CompletedDailyBarObservation` | Carries daily OHLC, source/provider/revision/finality references, and timezone-aware timestamps | Its metadata is not proof by itself; a production verifier must validate provider guarantees |
| `MarketDataProvider` | Current generic port returns `RawPriceBarObservation` daily rows | It lacks the accepted finality, source-revision, and session-provenance contract; do not feed its raw rows directly into lifecycle transitions |
| `CompletedDailyBarSource` | Provider-neutral port returns `ProviderDailyBarEvidence`, including provider contract version, instrument symbol, explicit Cairo session date, source timestamp, retrieval timestamp, and typed lifecycle bar; the envelope is now consumed by both lifecycle evaluation paths and persisted with observations and correction records in SQLite | Contract only; no provider-specific adapter or production finality verifier is implemented, and no real provider evidence has been independently validated |
| `DailyBarFinalityVerifier` | Application protocol used by the evaluator | No production implementation is composed in `runtime.py` |
| `SQLiteSessionCalendarRepository` | Persists immutable calendar versions, active pointer, and append-only activation events | No operational calendar is verified active; HTTP activation is intentionally unavailable |
| `InProcessScheduler` | Stores one-shot operations in process memory | Not durable across restart and not suitable as the production scheduler |
| `RunDurableScheduledWorkflow` | Durable occurrence/idempotency and recovery for configured market analysis plus alert delivery | Its result and execution contract are analysis/delivery-specific; it is not a lifecycle worker that can be reused unchanged |

## 3. Proposed worker boundary

Keep provider retrieval, eligibility, lifecycle evaluation, and alert delivery as separate responsibilities.

1. **Occurrence coordinator** — creates one durable market-session occurrence only after the active calendar explicitly confirms a CLOSED session and the DEC-139 close + 60-minute eligibility time has elapsed.
2. **Opportunity enumerator** — loads the latest immutable revision of every ACTIVE published opportunity. Terminal revisions are excluded. Enumeration order must be deterministic.
3. **Completed-bar source port** — `CompletedDailyBarSource` and its `ProviderDailyBarEvidence` envelope are now defined and contract-tested. A provider-specific implementation must retrieve daily observations for the opportunity symbol and required session range; its output must preserve the typed envelope, not an unqualified raw OHLC row.
4. **Finality verifier** — validates provider identity, daily timeframe, source timestamp/session semantics, completion/finality, and correction/revision identity against documented provider guarantees. Unknown or unsupported finality fails closed.
5. **Session evaluator** — invokes the existing `EvaluateOpportunityLifecycleSessions` for each opportunity, passing bars indexed by Cairo session date. It must preserve the evaluator's chronological stop-at-first-gap behavior.
6. **Outbox dispatcher** — sends already committed lifecycle alert intent through the existing per-recipient delivery state machine. Network delivery must remain outside lifecycle persistence transactions.

A single provider fetch may be shared for multiple opportunities with the same symbol and date range, but each opportunity must be evaluated independently using its own identity and cursor.

## 4. Scheduling and occurrence identity

- Use `Africa/Cairo` and the active calendar's explicit session records. Do not hard-code an assumed EGX close time or infer weekends/holidays.
- The earliest evaluation time for a session is `max(session_close + 60 minutes, closed_at)`.
- One market-session sweep may fan out into independently recoverable opportunity tasks.
- Proposed child occurrence identity: `calendar_version + session_date + opportunity_id`. Provider candle/revision identity remains part of the lifecycle observation idempotency key; it must not be replaced by a scheduler timestamp.
- A retry must reuse the same occurrence identity. A new calendar version or a different session date is a distinct occurrence.
- The durable claim must prevent two workers from processing the same child occurrence concurrently. Use lease/claim fencing or an equivalent compare-and-set mechanism; a process-local lock is insufficient.
- A partially completed sweep must resume only unfinished opportunity occurrences. It must not reset already committed lifecycle observations or bypass a recorded session gap.

## 5. Failure and recovery semantics

| Condition | Required behavior |
|---|---|
| No active calendar | Do not fetch bars or evaluate opportunities; report a blocked/no-op run |
| Calendar date not explicitly CLOSED | Do not evaluate; do not infer a session |
| Close + 60-minute buffer not elapsed | Defer the occurrence |
| No approved provider/finality verifier | Do not construct a trusted completed bar; fail closed and keep the worker disabled |
| Provider timeout/unavailable | Preserve the occurrence as retryable; do not advance any opportunity cursor |
| Missing expected session bar | Let the evaluator append a STALE gap and stop that opportunity at the first missing session |
| Provisional, stale, future, malformed, or unverified bar | Reject it as lifecycle evidence; do not transition the opportunity |
| Provider correction/revision | Use the existing correction intake/review/rebuild path; never overwrite prior evidence |
| Lifecycle persistence failure | Retry the same occurrence idempotently; execute_claimed validates the current owner/token and completes the claim in the same BEGIN IMMEDIATE transaction as lifecycle history, observations, outcomes, and outbox intent. It samples the clock before and after the operation; expiry before commit rolls the whole transaction back |
| Telegram delivery uncertainty | Delegate to the existing outbox state machine; preserve manual-only handling for DELIVERY_UNKNOWN |

Operational observability must include occurrence ID, calendar version, opportunity ID, expected session date, provider identity, source revision, evaluated/rejected/gap counts, oldest unresolved gap, retry count, and terminal execution state. Do not log credentials or raw licensed data payloads.

## 6. Reuse decision

Do **not** wire the worker through `InProcessScheduler`: its pending operations are memory-only.

Do **not** pass a lifecycle operation through `RunDurableScheduledWorkflow` as-is: that runner is coupled to `ConfiguredMarketAnalysisDeliveryResult` and analysis/delivery terminal states. Either create a lifecycle-specific durable occurrence runner using the same proven persistence/claim principles, or first extract a genuinely generic durable-operation abstraction with separate typed result adapters and tests. Do not perform that refactor merely to avoid a small dedicated worker.

The current per-opportunity evaluator and lifecycle Unit of Work should be reused; do not reimplement candle crossing, expiry, gap, correction, or alert semantics inside the worker.

## 7. Implementation sequence after gates

1. Verify the new deterministic latest-active-published projection against realistic SQLite history volumes, including query-plan/index use, revisions, unpublished records, and terminal states.
2. Define and test the completed-bar source port contract without implementing a provider adapter.
3. Implement a durable SQLite occurrence/claim boundary with atomic acquisition, lease expiry, monotonically increasing fencing tokens, restart/retry tests, and same-transaction fencing of lifecycle plus outbox writes. Keep runtime composition disabled.
4. Compose the worker with the existing evaluator and lifecycle Unit of Work; test multiple opportunities for one symbol, multiple symbols, partial failure, and concurrent duplicate occurrence.
5. Add operational metrics/logging and prove alert outbox dispatch remains outside the lifecycle transaction.
6. Keep the schedule disabled by default; enable only after all Section 8 gates are independently evidenced.

## 8. Activation blockers

- [ ] Owner-authorized provider selection and written technical/commercial evidence for EGX EOD finality, timestamp/session mapping, correction identity, and intended use rights.
- [ ] Production `DailyBarFinalityVerifier` implemented and contract-tested; unknown finality fails closed.
- [ ] Evidence-backed EGX calendar published and an owner-approved bootstrap/cursor-derived coverage policy implemented.
- [ ] Calendar activation performed by an individually attributable operator and audited; deployment bootstrap/recovery verified.
- [ ] Durable worker occurrence/claim store, lease fencing, restart recovery, and duplicate-run acceptance tests pass exact-head CI; the store and transaction guard are implemented, but the latest CI result is still pending.
- [ ] Full provider → calendar → worker → lifecycle → Telegram outbox → authenticated user-history E2E acceptance passes.
- [ ] Exact-head CI passes; worker remains disabled until the owner authorizes activation.

## 9. Owner decisions still open

1. **Calendar bootstrap:** OWNER APPROVED OPTION 3 — the `PUBLICATION_BASELINE` / `RECONCILED_SESSION` semantics, append-only bootstrap persistence, batch atomicity, cursor-derived coverage validator, calendar-backed schedule adapter, and SQLite activation coordinator are implemented on PR #515. The coordinator is not exposed as an operational API/command; no real calendar is active. Do not use a synthetic completed-bar observation or skip unreconciled sessions.
2. **Worker deployment model:** choose the deployment scheduler/hosting mechanism only after the durable occurrence contract is accepted. The current in-process scheduler is not sufficient.
3. **Operational retry window:** approve retry/backoff and alerting thresholds after provider rate limits and service-level expectations are known.

## 10. Synthetic query-plan and latency probe — 2026-11-13

A reproducible-in-session SQLite probe executed the exact SQL shape used by
`latest_active_published_opportunities()` against synthetic in-memory databases.
It used the same relevant indexes: `idx_signal_history_timeline(signal_id, id)`
and `idx_signal_revision_parent(parent_signal_id)`.

| Synthetic scale | History rows | Opportunity identities | SQL result rows | Median query time |
|---|---:|---:|---:|---:|
| Baseline | 155,000 | 55,000 (5,000 superseded parents) | 50,000 | 199.4 ms |
| Larger | 310,000 | 110,000 (10,000 superseded parents) | 100,000 | 416.6 ms |

The larger-scale run's maximum across five executions was 424.3 ms. The baseline
median is from seven executions. These are SQL fetch timings only: they exclude
application deserialization, status filtering, filesystem I/O, concurrent writers,
and cold-start effects. The databases were in-memory and generated for this probe;
this is not a production-volume acceptance benchmark and must not be used as a
production latency SLO.

`EXPLAIN QUERY PLAN` confirmed:
- `idx_signal_history_timeline` is used as a covering index for latest-history
  aggregation and for publication lookup by signal identity.
- `idx_signal_revision_parent` is used as a covering index for superseded-parent
  exclusion.
- Primary-key rowid lookups are used for latest and publication rows.
- SQLite creates a temporary B-tree for the final `ORDER BY`.

The probe confirms intended index selection at these synthetic scales, but the
temporary sort and the post-query Python ACTIVE-state filter remain measurable
costs. Before worker-scale adoption, add an automated on-disk benchmark with
repeatable data generation, warm/cold runs, P50/P95, concurrent reader/writer
pressure, and application deserialization included.

## 11. Current result

**DESIGN COMPLETE / WORKER NOT WIRED / NOT ACTIVATED.** Existing per-opportunity evaluation, lifecycle persistence, correction/replay, append-only bootstrap, cursor-derived calendar validation, and the provider-neutral SQLite activation coordinator are implemented on PR #515. The remaining worker-specific engineering is a provider-specific source adapter, production finality verifier, durable occurrence/claim store with lease fencing and restart recovery, runtime composition, outbox dispatch orchestration, operational observability, automated on-disk query-plan/latency acceptance benchmark for the active-opportunity projection, and multi-opportunity/concurrency/restart E2E tests. Calendar activation remains unavailable operationally: no real origin/evidence is approved, and provider finality/deployment validation remain blockers. Worker stays disabled.

**External-contact boundary:** no provider outreach, quote request, account request, or credential request is authorized. EGID remains a research candidate only. M61/backtesting remains paused.


## 12. Durable occurrence claims — implementation added 2026-11-13

The lifecycle-specific claim boundary is implemented on this branch without wiring or activating a worker.

- lifecycle_occurrence_id() derives a stable SHA-256 identity from calendar version, Cairo session date supplied by the caller, and opportunity UUID. A calendar-version, session, or opportunity change creates a distinct occurrence; retries reuse the same identity.
- SQLiteLifecycleOccurrenceClaimStore persists owner, status, attempt, claimed_at, lease expiry, last error, completion time, and a monotonically increasing fencing token. Acquisition uses BEGIN IMMEDIATE; only one concurrent worker can acquire a live occurrence. Expired claims can be reclaimed, increasing both attempt and fencing token. Completed occurrences cannot be claimed again.
- mark_failed accepts only the current owner/token while its lease is still valid. Old or expired workers cannot mutate the current claim.
- SQLiteSignalLifecycleUnitOfWork.execute_claimed() validates the claim, applies lifecycle persistence (including alert outbox intent), and marks the claim completed inside the same SQLite write transaction. It checks lease validity both before and after the lifecycle operation. If the lease expires during processing, the transaction rolls back lifecycle and outbox writes. SQLite BEGIN IMMEDIATE prevents a competing claimant from taking over while that transaction is active.
- Tests added for concurrent acquisition, expired-lease recovery and fencing, retry after failure, completed-occurrence rejection, stale-owner write rejection, lease-expiry rollback across history and outbox, and store reconstruction/restart recovery.

Boundaries and remaining work:
- This is a persistence/application primitive, not a running worker. No provider adapter, calendar activation, scheduler, runtime composition, monitoring, or outbound delivery was enabled.
- The claim store must be initialized against the same SQLite database used by the lifecycle Unit of Work. Runtime composition must make this dependency explicit and must never silently point claims at a separate database.
- The current implementation uses caller-supplied aware timestamps. A production worker must supply a trusted clock and define lease duration, renewal, retry/backoff, and operational recovery policy before activation.
- Exact-head CI for the latest claim-store and restart/outbox tests is required before treating this implementation as verified.
