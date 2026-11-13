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
- [ ] Durable worker occurrence/claim store, lease fencing, restart recovery, and duplicate-run acceptance tests pass exact-head CI; the claim/transaction primitive is implemented, but runtime composition remains disabled.
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
- The claim store supports fenced lease renewal: only the current owner/token may extend a still-live claim; exact-expiry renewal is rejected. Renewal preserves occurrence identity, attempt, fencing token, and original claimed_at.
- The implementation uses caller-supplied aware timestamps. A production worker must supply a trusted clock and define lease duration, heartbeat/renewal cadence, maximum renewal policy, cancellation behavior, retry/backoff, and operational recovery policy before activation.
- Exact-head CI passed on d236e6b7f28f4a481878d501af6e4df0309d3001 in [run #43446251002](https://github.com/palestiny/egx-stock-analyzer/actions/runs/43446251002): all six jobs succeeded; Python 3.12 unit tests reported 1,810 passed, 8 deselected, 89.66% coverage (85% minimum). This verification predates the lease-renewal addition and does not verify the new renewal code.


## 13. Fenced lease renewal — implementation added 2026-11-13

SQLiteLifecycleOccurrenceClaimStore.renew() atomically extends a claim with a compare-and-set update inside BEGIN IMMEDIATE.

- Renewal succeeds only when occurrence ID, owner ID, fencing token, and CLAIMED status match the persisted row and the stored lease expiry is strictly later than the supplied aware UTC instant.
- Renewal at the exact expiry instant is rejected (lease_until > now, not >=). An expired or reclaimed claim cannot be revived by its previous owner.
- A successful renewal changes only lease_until; it preserves claimed_at, owner, attempt, occurrence identity, and fencing token, and returns an updated immutable claim.
- Regression tests cover successful renewal, exact-expiry and post-expiry rejection, stale owner/token rejection after reclaim, invalid inputs, and persistence across store reconstruction.
- The application claim-store protocol now exposes the renewal operation.

This remains a persistence primitive only. No heartbeat loop, worker, scheduler, runtime composition, provider retrieval, calendar activation, monitoring, or outbound delivery has been added. Before activation, an owner-approved operational policy must define trusted clock source, lease duration, heartbeat interval, maximum renewals/runtime, cancellation and shutdown semantics, and retry/backoff. The claim store and lifecycle Unit of Work must continue to share the same SQLite database.


## 14. Claim-store database binding — implementation added 2026-11-13

SQLiteSignalLifecycleUnitOfWork accepts an explicit SQLiteLifecycleOccurrenceClaimStore binding for claimed execution. Construction rejects a claim store whose resolved database path differs from the lifecycle history/track-record/outbox database. execute_claimed() refuses to run unless this binding was supplied, preventing accidental validation/completion against a missing or separate claims table. Tests cover mismatched database paths and missing binding. This is dependency-boundary enforcement only; no worker runtime composition has been introduced.

## 15. Verified engineering delta — 2026-11-13

The earlier Section 11 statement that deterministic active-opportunity enumeration and the durable occurrence/claim primitive were still outstanding is superseded by the implementation recorded in Sections 12–14 and the current PR branch.

- Deterministic `latest_active_published_opportunities()` projection is implemented in the SQLite history store and consumed by lifecycle bootstrap.
- Durable occurrence claims, monotonic fencing, stale-owner rejection, fenced lease renewal, and explicit same-database binding are implemented and covered by persistence tests.
- Added an on-disk SQLite regression test that seeds 240 opportunity identities, including terminal opportunities and superseded revisions, reopens the database, and verifies deterministic active-published projection results. This is a correctness/regression test, not a P50/P95 performance acceptance benchmark.
- The worker remains intentionally unwired and disabled. No provider retrieval, production finality verifier, calendar activation, runtime scheduler, outbox dispatcher, or monitoring is enabled.

Remaining engineering before any worker activation: provider adapter and production finality contract; owner-approved deployment scheduler and trusted-clock/lease/retry/shutdown policy; runtime composition; outbox orchestration; operational observability; automated on-disk latency/query-plan benchmark with warm/cold P50/P95 and concurrent read/write pressure; and worker-level concurrency/restart/E2E acceptance. External provider rights/finality and authentic calendar evidence remain independent blockers.


## 16. Reproducible on-disk projection benchmark harness — 2026-11-13

A manual benchmark harness is now available at `tools/benchmark_lifecycle_projection.py`. It creates temporary disk-backed SQLite databases with synthetic active, terminal, and revised opportunities, then measures the actual `latest_active_published_opportunities()` implementation (including row deserialization and ACTIVE-state filtering).

Run from the repository root:

```powershell
python -m tools.benchmark_lifecycle_projection --sizes 10000 50000 100000 --samples 7 --warmups 2 --writer-operations 250 --output reports/lifecycle-projection-benchmark.json
```

The JSON report includes database size, first-query and reopened-store timings, warm P50/P95 samples, timings under a concurrent SQLite writer, and `EXPLAIN QUERY PLAN` output. The writer only appends synthetic history events to the temporary benchmark database. The harness does not open the canonical market-data archive or mutate application data.

**Measurement caveat:** reopened-store timing is a process/store-initialization approximation. It does not flush the operating-system page cache and must not be described as a physical cold-disk measurement. Percentiles are diagnostic samples, not production SLOs.

**Status:** BENCHMARK HARNESS IMPLEMENTED / MEASURED ACCEPTANCE RUN PENDING. Do not mark projection performance accepted until the harness is executed on the intended deployment class, its JSON artifact is reviewed, and query-plan/index behavior plus P50/P95 under writer pressure are assessed. This does not authorize worker wiring or activation.

## 17. Automated pull-request benchmark execution — 2026-11-13

The existing pull-request CI workflow now includes a dedicated on-disk projection benchmark job. It runs the harness at 10,000, 50,000, and 100,000 synthetic opportunity identities, with seven measured samples, two warmups, and 250 synthetic concurrent-writer operations per scale. The generated JSON is uploaded as a 30-day GitHub Actions artifact.

The benchmark uses only temporary synthetic SQLite databases and does not read or mutate the canonical market-data archive. The job is diagnostic and does not activate or compose the lifecycle worker.

**Status:** CI wiring committed; exact-head workflow validation and the first complete benchmark artifact are pending. Performance acceptance remains pending until the artifact is reviewed against an explicitly approved deployment class and its P50/P95/query-plan behavior is assessed.


## 18. First automated on-disk benchmark — baseline measured 2026-11-13

The first exact-head automated benchmark completed successfully on PR head
`264a65c3a81ab0d47a44affb66d8d42b2ac5fd35` (GitHub Actions run
`43475780322`). It measured the actual projection implementation, including
signal deserialization and ACTIVE-state filtering, using temporary on-disk
SQLite databases.

| Opportunity identities | Active published revisions | Database size | Warm P50 | Warm P95 | Writer-pressure P50 | Writer-pressure P95 |
|---:|---:|---:|---:|---:|---:|---:|
| 10,000 | 9,000 | 11.4 MB | 424.3 ms | 435.5 ms | 423.2 ms | 434.9 ms |
| 50,000 | 45,000 | 56.8 MB | 2,412.1 ms | 2,698.7 ms | 2,480.5 ms | 2,800.4 ms |
| 100,000 | 90,000 | 114.0 MB | 5,731.3 ms | 5,927.7 ms | 5,714.4 ms | 5,884.8 ms |

The query plan used `idx_signal_history_timeline` and
`idx_signal_revision_parent`, but also required a full grouped latest-row
projection and a temporary B-tree for ordering. The result is correct at all
three scales, but the 100,000-identity P95 is approximately 5.93 seconds.
This is a material scaling limitation, not an accepted performance result.

The artifact is retained for 30 days as
`lifecycle-projection-benchmark-e41f20c3d0d38a3848bfc5eff1fd6ff7a65b28a7`.
Reopened-store timings are not physical cold-disk measurements; the operating
system page cache was not flushed. The benchmark's 250 writer operations are
synthetic and do not represent a production write-rate model.

**Decision:** baseline benchmark succeeded technically; performance acceptance
FAILED / NOT ACCEPTED at 50k–100k scale pending optimization and a comparable
rerun. Worker remains unwired and disabled.

## 19. Materialized opportunity-history pointers — implementation in progress

To remove repeated full-history aggregation from the read path, the SQLite
history store now maintains a compact `signal_opportunity_projection` table.
An insert trigger advances the latest-history pointer and preserves the first
publication-event pointer. Initialization backfills the projection from
existing append-only history, so existing databases are migrated without
fabricating events or rewriting source history.

The application query joins the two pointed history rows and retains the
existing superseded-parent exclusion and Python ACTIVE-state check. This keeps
the published baseline and latest-state semantics explicit while avoiding the
per-query `GROUP BY MAX(id)` and correlated earliest-publication lookup.

The benchmark's EXPLAIN query and regression assertion were updated to measure
the same materialized-pointer query. Exact-head CI and a repeat of the 10k /
50k / 100k disk benchmark are pending. No performance improvement is claimed
until the new artifact is available and compared under the same environment
and parameters. Worker activation remains out of scope.


## 20. Materialized-pointer benchmark result — 2026-11-13

The comparable automated on-disk benchmark completed on head
`2b72b171a54fe5a2582070c8f15c5d7aff0f8850` (workflow run
`43476777804`, Python 3.12.16, SQLite 3.45.1). It used the same 10k / 50k /
100k identity scales, seven warm samples, two warmups, and 250 synthetic writer
operations as the baseline in Section 18.

| Opportunity identities | Warm P50 | Warm P95 | Writer-pressure P50 | Writer-pressure P95 |
|---:|---:|---:|---:|---:|
| 10,000 | 425.7 ms | 488.4 ms | 444.1 ms | 503.9 ms |
| 50,000 | 2,762.2 ms | 3,341.0 ms | 2,770.8 ms | 3,371.6 ms |
| 100,000 | 6,477.8 ms | 6,907.2 ms | 6,456.4 ms | 6,921.3 ms |

Compared with Section 18, warm P50 is effectively unchanged at 10k and regresses
by approximately 14.5% at 50k and 13.0% at 100k. At 100k, warm P95 regresses
from 5,927.7 ms to 6,907.2 ms. The query plan now scans the projection primary
key index and performs indexed revision-parent lookups plus primary-key
lookups for the latest and publication rows; the former grouped aggregation is
removed, but the full candidate scan and Python materialization remain.

**Decision: MATERIALIZED POINTERS ARE NOT AN ACCEPTED PERFORMANCE FIX.** Keep
the correctness implementation and migration under regression review, but do
not claim a latency improvement or use this result as worker-scale acceptance.
The next diagnostic separates SQLite fetch time from JSON/domain-object
deserialization and ACTIVE filtering before selecting another optimization.
The benchmark does not define a production SLO and its synthetic writer is not
a production workload. Worker remains unwired and disabled.


## 21. Query-versus-materialization diagnostic

The benchmark harness now emits a `stage_breakdown` for each dataset size.
It reports (a) SQLite statement execution plus full row fetch, and (b) the
application-side materialization pass that deserializes the latest record,
checks ACTIVE status, and deserializes the publication record only for active
candidates. It also records candidate and active row counts so the two stages
cannot silently benchmark different result populations.

These are diagnostic stage timings, not additive replacements for the end-to-end
store measurement: the diagnostic uses a separately opened SQLite connection
and repeated samples, so cache state and connection overhead differ. The
end-to-end `warm` and `under_concurrent_writer` measurements remain the
authoritative comparable series. No performance conclusion is drawn until the
new workflow artifact is available and reviewed.


## 22. Exact-head stage diagnostic and CI result — 2026-11-13

The stage diagnostic completed on commit
`d360e3a3494afd88bed3c875738de06784451123` in GitHub Actions run
`43477931961` (Python 3.12.16, SQLite 3.45.1). All seven workflow jobs
completed successfully: unit tests with coverage, deterministic integration
tests, frontend tests, dependency audit, daily-history audit, container build,
and the on-disk lifecycle benchmark. The benchmark artifact was uploaded and
retained by GitHub Actions.

| Identities | Candidates | Active | SQLite fetch P50 | Deserialize/filter P50 | End-to-end warm P50 | Warm P95 |
|---:|---:|---:|---:|---:|---:|---:|
| 10,000 | 10,000 | 9,000 | 32.0 ms | 221.9 ms | 489.1 ms | 597.3 ms |
| 50,000 | 50,000 | 45,000 | 212.2 ms | 1,124.9 ms | 3,192.8 ms | 3,368.8 ms |
| 100,000 | 100,000 | 90,000 | 434.7 ms | 2,136.6 ms | 6,407.9 ms | 6,773.1 ms |

The stage diagnostic indicates that deserialization and filtering dominate the
measured two-stage pass: approximately 87.4%, 84.1%, and 83.1% of the combined
SQLite-fetch plus materialization time at 10k, 50k, and 100k respectively.
This is diagnostic evidence, not a precise attribution of total end-to-end
latency: it uses a separate connection and does not include every store-call
overhead. The end-to-end measurements remain authoritative.

Against the previous materialized-pointer run (Section 20), this run's warm
P50 is approximately 14.9% slower at 10k, 15.6% slower at 50k, and 1.1%
faster at 100k. Against the original baseline (Section 18), all three warm P50
measurements remain slower. These runs are synthetic and do not establish a
production SLO.

**Decision:** CI correctness/build checks PASSED for this exact head. Performance
acceptance remains NOT ACCEPTED; the materialized-pointer change is not
demonstrated to be an improvement. The next optimization investigation should
focus on avoiding repeated full domain-object construction for projection
filtering, while preserving the exact latest-state, revision-exclusion,
publication-provenance, and ordering semantics. No implementation change is
authorized by this diagnostic alone. Worker remains unwired and disabled.


## 23. SQL-side terminal-state filtering benchmark — 2026-11-13

The follow-up optimization moves the known-terminal-state exclusion into SQLite using the serialized `status` field. The query deliberately keeps ACTIVE rows and also keeps unknown, missing, or JSON-null status values in the candidate set so that domain deserialization still fails closed instead of silently hiding malformed or newly introduced states. Only the known terminal states (TRIGGERED, INVALIDATED, EXPIRED, CLOSED) are filtered before domain-object construction. The benchmark query mirrors the store query.

Exact-head GitHub Actions run [#5757](https://github.com/palestiny/egx-stock-analyzer/actions/runs/43479263348) completed successfully on branch head `2577eca2370830d978f841275707cd2f731ad763`. All seven jobs passed. Python 3.12 unit tests: **1,862 passed, 8 deselected, 89.66% coverage** (85% minimum); lint, type-check, deterministic integration tests, frontend tests, dependency audit, daily-history audit, container build, and the on-disk benchmark passed. Benchmark artifact ID: `14065035961`.

| Identities | Candidates after SQL filter | Active | SQLite fetch P50 | Deserialize/filter P50 | Warm P50 | Warm P95 | Concurrent-writer P50 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10,000 | 9,000 | 9,000 | 35.0 ms | 202.2 ms | 398.1 ms | 424.0 ms | 424.4 ms |
| 50,000 | 45,000 | 45,000 | 229.5 ms | 1,012.9 ms | 2,954.4 ms | 3,193.5 ms | 2,855.4 ms |
| 100,000 | 90,000 | 90,000 | 506.0 ms | 2,115.1 ms | 6,097.1 ms | 6,245.4 ms | 6,329.5 ms |

The query plan scans the projection primary-key index, performs an indexed correlated lookup on `idx_signal_revision_parent`, and fetches latest/publication history rows by integer primary key. It no longer returns terminal latest-state identities to Python for domain-object construction. The stage diagnostic remains a separate-connection diagnostic, not an additive or exact decomposition of end-to-end latency.

Compared with the immediately preceding materialized-pointer benchmark (Section 22's predecessor run), warm P50 improved by **18.6% at 10k, 7.5% at 50k, and 4.9% at 100k**. Compared with the original pre-materialized-pointer baseline (Section 18), it is **6.2% faster at 10k, 22.5% slower at 50k, and 6.4% slower at 100k**. Thus the SQL-side filter is a measurable improvement over the immediately preceding implementation, but it does not recover the baseline performance at realistic larger sizes. The benchmark is synthetic, on temporary on-disk SQLite, and its reopened-store query is not a physical cold-disk measurement.

**Decision:** correctness and exact-head CI PASSED. Performance acceptance remains **NOT ACCEPTED**. Retain this SQL-side filter as a measured incremental reduction in candidate materialization, but do not claim the projection is performance-ready or enable the worker. The dominant remaining cost is still construction/deserialization of active domain objects (90% of identities in this fixture); the next investigation must avoid constructing full `Signal` objects merely to establish projection eligibility, while preserving fail-closed validation and all publication/revision semantics. No calendar activation, worker/monitoring activation, provider outreach, or merge is authorized.
## 24. Lightweight publication provenance projection — 2026-11-13

The projection contract now separates the full latest opportunity state from the immutable publication provenance needed by bootstrap:

- `PublishedOpportunityRevision.latest` remains a full `SignalRecord`, because eligibility and downstream lifecycle identity checks require the latest domain `Signal`.
- `PublishedOpportunityRevision.publication` is now a `SignalPublicationRecord` containing only `signal_id`, `event`, and `recorded_at`. Bootstrap uses exactly these fields to derive the Cairo publication baseline and verify immutable provenance.
- Both SQLite and InMemory stores return the same lightweight publication record. SQLite selects publication metadata without selecting or deserializing the publication JSON payload.
- The benchmark query and stage diagnostic now match the production projection and measure only latest-signal materialization. Regression coverage instruments deserialization and asserts exactly one full `Signal` is constructed per projected active opportunity.
- No persisted schema or historical event data changes. The projection continues to use the existing publication-history pointer and latest-history pointer; publication identity, timestamp, event, latest ACTIVE validation, superseded-parent exclusion, deterministic ordering, and bootstrap revalidation remain intact.

**Verification status:** implementation and regression-test changes are committed on this branch. Exact-head CI and the new 10k/50k/100k on-disk benchmark have not yet been verified for this change. Performance acceptance remains **NOT ACCEPTED** until exact-head correctness checks and benchmark artifacts are reviewed against Section 23. The worker remains unwired and disabled. No calendar activation, provider outreach, market-data changes, or merge is authorized.
