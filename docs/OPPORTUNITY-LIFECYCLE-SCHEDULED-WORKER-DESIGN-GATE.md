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
| `SignalHistoryStore` | Exposes `all_records()`, per-signal history, and current signal records | A deterministic latest-active-opportunity projection and its SQLite query/performance behavior must be verified before worker implementation |
| `SignalLifecycleOrchestrator` | Provides per-opportunity latest-observation cursor, append-only gap events, lifecycle transitions, expiry, and correction-aware history | Does not schedule or claim work |
| `CompletedDailyBarObservation` | Carries daily OHLC, source/provider/revision/finality references, and timezone-aware timestamps | Its metadata is not proof by itself; a production verifier must validate provider guarantees |
| `MarketDataProvider` | Current generic port returns `RawPriceBarObservation` daily rows | It lacks the accepted finality, source-revision, and session-provenance contract; do not feed its raw rows directly into lifecycle transitions |
| `DailyBarFinalityVerifier` | Application protocol used by the evaluator | No production implementation is composed in `runtime.py` |
| `SQLiteSessionCalendarRepository` | Persists immutable calendar versions, active pointer, and append-only activation events | No operational calendar is verified active; HTTP activation is intentionally unavailable |
| `InProcessScheduler` | Stores one-shot operations in process memory | Not durable across restart and not suitable as the production scheduler |
| `RunDurableScheduledWorkflow` | Durable occurrence/idempotency and recovery for configured market analysis plus alert delivery | Its result and execution contract are analysis/delivery-specific; it is not a lifecycle worker that can be reused unchanged |

## 3. Proposed worker boundary

Keep provider retrieval, eligibility, lifecycle evaluation, and alert delivery as separate responsibilities.

1. **Occurrence coordinator** — creates one durable market-session occurrence only after the active calendar explicitly confirms a CLOSED session and the DEC-139 close + 60-minute eligibility time has elapsed.
2. **Opportunity enumerator** — loads the latest immutable revision of every ACTIVE published opportunity. Terminal revisions are excluded. Enumeration order must be deterministic.
3. **Completed-bar source port** — retrieves daily observations for the opportunity symbol and required session range. Its output must be the typed completed-bar contract, not an unqualified raw OHLC row.
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
| Lifecycle persistence failure | Retry the same occurrence idempotently; the existing lifecycle Unit of Work remains the atomic boundary for state/history/outbox intent |
| Telegram delivery uncertainty | Delegate to the existing outbox state machine; preserve manual-only handling for DELIVERY_UNKNOWN |

Operational observability must include occurrence ID, calendar version, opportunity ID, expected session date, provider identity, source revision, evaluated/rejected/gap counts, oldest unresolved gap, retry count, and terminal execution state. Do not log credentials or raw licensed data payloads.

## 6. Reuse decision

Do **not** wire the worker through `InProcessScheduler`: its pending operations are memory-only.

Do **not** pass a lifecycle operation through `RunDurableScheduledWorkflow` as-is: that runner is coupled to `ConfiguredMarketAnalysisDeliveryResult` and analysis/delivery terminal states. Either create a lifecycle-specific durable occurrence runner using the same proven persistence/claim principles, or first extract a genuinely generic durable-operation abstraction with separate typed result adapters and tests. Do not perform that refactor merely to avoid a small dedicated worker.

The current per-opportunity evaluator and lifecycle Unit of Work should be reused; do not reimplement candle crossing, expiry, gap, correction, or alert semantics inside the worker.

## 7. Implementation sequence after gates

1. Verify deterministic latest-active-opportunity enumeration against the SQLite-backed history store, including revisions and terminal states.
2. Define and test the completed-bar source port contract without implementing a provider adapter.
3. Implement a durable occurrence/claim boundary and restart/retry tests using test doubles only.
4. Compose the worker with the existing evaluator and lifecycle Unit of Work; test multiple opportunities for one symbol, multiple symbols, partial failure, and concurrent duplicate occurrence.
5. Add operational metrics/logging and prove alert outbox dispatch remains outside the lifecycle transaction.
6. Keep the schedule disabled by default; enable only after all Section 8 gates are independently evidenced.

## 8. Activation blockers

- [ ] Owner-authorized provider selection and written technical/commercial evidence for EGX EOD finality, timestamp/session mapping, correction identity, and intended use rights.
- [ ] Production `DailyBarFinalityVerifier` implemented and contract-tested; unknown finality fails closed.
- [ ] Evidence-backed EGX calendar published and an owner-approved bootstrap/cursor-derived coverage policy implemented.
- [ ] Calendar activation performed by an individually attributable operator and audited; deployment bootstrap/recovery verified.
- [ ] Durable worker occurrence/claim store, lease fencing, restart recovery, and duplicate-run acceptance tests pass.
- [ ] Full provider → calendar → worker → lifecycle → Telegram outbox → authenticated user-history E2E acceptance passes.
- [ ] Exact-head CI passes; worker remains disabled until the owner authorizes activation.

## 9. Owner decisions still open

1. **Calendar bootstrap:** OWNER APPROVED OPTION 3 — no activation until a controlled, durable, audited cursor exists. The exact cursor semantics and atomic persistence contract remain to be designed; do not use a synthetic completed-bar observation or skip unreconciled sessions.
2. **Worker deployment model:** choose the deployment scheduler/hosting mechanism only after the durable occurrence contract is accepted. The current in-process scheduler is not sufficient.
3. **Operational retry window:** approve retry/backoff and alerting thresholds after provider rate limits and service-level expectations are known.

## 10. Current result

**DESIGN PROPOSED / WORKER NOT WIRED / NOT ACTIVATED.** Calendar bootstrap policy Option 3 and cursor-derived coverage are owner-approved; durable bootstrap-cursor semantics and implementation remain open. Existing evaluation and lifecycle semantics should be reused. Provider retrieval, production finality, calendar bootstrap/activation, durable worker execution, and full end-to-end proof remain separate gates.

**External-contact boundary:** no provider outreach, quote request, account request, or credential request is authorized. EGID remains a research candidate only. M61/backtesting remains paused.
