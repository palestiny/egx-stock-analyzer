# Signal Lifecycle Observation Integration — Design Gate

**Status:** Correction replay/rebuild and compensating-notification behavior are implemented on this branch and passed code CI on `1d2b902a646174521b143cf19c1b7c7c126cd072` (run #43405799607; all six jobs successful). Production activation remains blocked by the absence of an accepted provider finality adapter, an active deployment calendar, scheduled-worker wiring, and deployment-level end-to-end acceptance. No current market-data provider has been accepted for automatic lifecycle transitions. PR #515 remains Draft and unmerged.  
**Scope:** Non-M61 opportunity lifecycle observation, invalidation, terminal outcomes, and Telegram event publication  
**Related owner policy:** DEC-135 (accepted 2026-10-31)  
**Related implementation:** `SignalLifecycleOrchestrator`, `SignalMarketState`, `GenerateSignal`, `PublishSignalOpportunity`

## 0. Implementation status — 2026-11-13

PR #515 contains the completed-daily-OHLC lifecycle implementation, including:

- Append-only SQLite daily-observation evidence, transactionally persisted with lifecycle history and alert-outbox intent.
- Idempotent replay, conflicting-payload and out-of-order rejection, and conservative same-candle dual-touch handling.
- Calendar-gated eligibility using an explicitly closed session, close confirmation, and the accepted 60-minute post-close buffer.
- Durable chronological recovery using the latest committed observation as the cursor; missing/unverified expected sessions create an append-only gap and stop advancement.
- Expiry after 20 eligible EGX sessions, without creating a realized return/R record.
- Immutable opportunity revision links and append-only correction intake, review, and rebuild records.

**Correction replay/rebuild — implementation complete in this PR:** a correction must have a latest `REPLAY_REQUIRED` review; unresolved sibling corrections block replay; the system rebuilds state from the publication baseline using the effective corrected candle set in chronological order; it records the corrected observation and an append-only rebuild audit record containing operator identity, previous/resulting status, observation count, and deterministic replay digest. A repeated rebuild request is idempotent. The rebuilt opportunity can accept later completed sessions. When a previously communicated lifecycle state changes, the prior unsent alert and its unsent recipient rows are superseded, while already delivered recipients receive a scoped corrective event; ambiguous `DELIVERY_UNKNOWN` recipients are not resent or treated as confirmed recipients. In-flight sends block the replay to avoid racing a correction against a network send.

**Still not production-complete:** no production provider currently supplies an accepted finality attestation; no active deployment calendar version is available in the target deployment; no scheduled worker is wired; and the complete provider → calendar → lifecycle → Telegram → per-user history path has not passed deployment-level acceptance. These are separate activation gates, not missing correction-replay code. PR #515 remains Draft and unmerged; do not activate production monitoring until those gates pass.

## 1. Historical baseline before PR #515 (superseded by implementation updates below)

The repository currently has these separate capabilities:

- `GenerateSignal` derives an ACTIVE signal from the latest persisted analysis result and carries the analysis source-bar `data_timestamp`.
- `PublishSignalOpportunity` records a published signal and creates an immutable `SIGNAL_PUBLISHED` alert event in the durable SQLite outbox.
- `DispatchSignalAlertOutbox` handles per-recipient Telegram delivery, entitlements, retry/reconciliation, and durable recipient state.
- `SignalLifecycleOrchestrator` can transition a supplied signal using a supplied `SignalMarketState`, record a terminal market-proxy outcome, and publish a lifecycle alert event.
- `SignalLifecycleOrchestrator` is constructed in `app/infrastructure/runtime.py` and exposed on the runtime object.
- The current `SignalMarketState` contract carries one `price`, `observed_at`, and `data_timestamp`; it does not carry daily OHLC, provider identity, source candle identity, revision, or a completion attestation. The current `transition_signal` therefore evaluates a single price rather than DEC-138's completed-candle High/Low rules.
- The current `SignalLifecycleOrchestrator.process` requires `entry_price` and creates a market-proxy outcome whenever a target/invalidation transition occurs. Its outcome builder uses the observation close as the target exit and the invalidation level as the stop exit. That behavior is not accepted as completed-OHLC level monitoring or as performance accounting under DEC-139; it must be separated before production wiring.
- `RawPriceBarObservation` contains OHLC values and timeframe/timestamp but no provider completion/finality attestation or immutable source-candle/revision identity. The current Yahoo adapter maps daily history rows into this raw type but does not attest that a bar is final/complete. Yahoo rows are therefore not currently eligible for automatic lifecycle transitions under DEC-139.
- `SQLiteSignalHistoryStore` records signal-level history keyed by signal identity; it does not model a user's saved/acknowledged opportunity list. The Telegram delivery store tracks recipient delivery state, which is not equivalent to a per-user opportunity lifecycle/history read model.

The inspected API publication route `POST /api/v1/opportunities/{symbol}/publish` calls `GenerateSignal` and `PublishSignalOpportunity`. It does not call `SignalLifecycleOrchestrator.process` or `invalidate_for_evidence_change`. No completed end-to-end observation path has been evidenced that supplies fresh market observations to the lifecycle service after analysis updates.

Therefore the repository must not currently describe target-hit/stop/invalidation monitoring as an automatically operating end-to-end feature, or claim a complete per-user opportunity history. The presence of the domain transition, a constructed orchestrator, or per-recipient delivery rows is not proof of active observation or a user-facing lifecycle read model.

## 2. Owner-approved constraints

- Published opportunities are immutable versions; a materially revised setup must not silently rewrite the original publication.
- Re-evaluation and invalidation must be traceable.
- No actual trade execution or portfolio P&L is implied; lifecycle outcomes are market-proxy observations.
- Missing analysis, unavailable source data, or incomplete coverage is not evidence that an opportunity became invalid.
- Delayed/daily data must not be presented as live intraday monitoring.
- Do not change signal-generation rules, scoring, target/invalidation levels, or automatic recommendation policy without a separate accepted decision.

## 3. Decisions required before wiring

The following policy decisions are accepted in DEC-138 and DEC-139. They are **not** evidence that the current provider/runtime satisfies the requirements:

1. **Observation semantics — accepted:** Swing transitions use completed daily OHLC candles only; `High >= target` records target reach and `Low <= invalidation` records invalidation. Same-candle dual touch resolves to invalidation. Persist source candle identity/timestamp, provider provenance, OHLC evidence, policy version, and transition identity. Same-candle replay is idempotent; corrections are append-only and auditable.
2. **Session and cadence — accepted:** Use a versioned operator-maintained EGX calendar until an authoritative machine-readable source is verified. Evaluate once after configured session close + 60 minutes and only for sessions explicitly marked closed.
3. **Provider/data eligibility — policy accepted, provider proof open:** Require provider-attested daily timeframe, source identity/timestamp, and final/complete status. If completion cannot be established, suppress transitions. Reject missing, non-finite, non-positive, or internally inconsistent OHLC. Mark an expected-session observation STALE at the next scheduled evaluation if eligible data is absent. Actual adapter guarantees and timestamp semantics still require verification.
4. **Expiry — accepted:** Active Swing opportunities expire after 20 eligible EGX trading sessions, as a distinct terminal event.
5. **Revision — accepted:** A materially changed setup creates a new immutable linked revision; prior evidence and terminal events are not overwritten.
6. **Entry/performance — accepted:** Keep level monitoring separate from performance accounting. Do not calculate realized return/R without an explicit entry/fill; otherwise record only level reached/invalidated.
7. **Corrections and recovery — accepted:** Append correction/reconciliation records; replay identity is provider + symbol + timeframe + candle timestamp + revision. Reconcile missed eligible sessions chronologically after restart and stop/mark a gap if required session data is missing.

Implementation and provider/session eligibility verification remain open. See `docs/DEC-138-COMPLETED-DAILY-OHLC-OPPORTUNITY-OBSERVATION.md` and `docs/DEC-139-LIFECYCLE-MONITORING-OPERATIONAL-POLICY.md`.

## 4. Recommended application flow

After owner decisions and provider/session verification, implement a dedicated application use case rather than calling domain services ad hoc from API handlers:

1. Receive a successfully persisted analysis snapshot with explicit symbol, timeframe, provider, source-bar timestamp, and observation/cutoff metadata.
2. Validate the observation against the accepted data eligibility policy.
3. Load the active published opportunity version for the symbol/timeframe/strategy identity.
4. If the setup's supporting evidence materially changed, apply the approved revision/invalidation policy. A missing candidate or failed analysis must not invalidate the existing opportunity.
5. Construct `SignalMarketState` from the verified observation price and its actual source-data timestamp. Keep source-data time separate from processing/observation time.
6. Apply the pure domain transition and create an immutable lifecycle event with a stable idempotency key derived from signal version and source observation identity.
7. Persist transition, outcome, and alert intent through `SQLiteSignalLifecycleUnitOfWork`. The history, outcome, and alert outbox stores must share one SQLite database; the unit of work uses one connection and `BEGIN IMMEDIATE` so these writes commit or roll back together. Telegram network delivery remains outside this transaction.
8. Dispatch the lifecycle alert through the existing per-recipient Telegram delivery state machine. Preserve delivered-recipient suppression and manual-only handling for ambiguous `DELIVERY_UNKNOWN`.
9. Expose lifecycle history and outcome provenance through authenticated per-user/operator read models with clear proxy-not-execution wording.

## 5. Required acceptance tests

### Observation and domain
- Correct source-data timestamp is persisted for the observation that triggered the transition, not copied from signal generation.
- Naive, future-dated, missing, stale, and corrected observations follow the approved policy.
- Close-only versus OHLC crossing cases, gaps, target/stop same-bar ambiguity, and both BUY/SELL directionality.
- Duplicate processing of the same source observation is idempotent.
- A later valid observation can progress an ACTIVE signal; an older observation cannot overwrite a newer state.

### Publication and revision
- First publication, identical republish, material revision, and unchanged evidence.
- Missing/failed analysis does not invalidate a published opportunity.
- Material evidence change invalidates or versions the prior opportunity only as approved.
- Expiry and close transitions are tested against an explicit policy, not just enum values.

### Persistence, Telegram, and recovery
- Crash between lifecycle transition, outcome persistence, and alert intent does not silently lose or duplicate lifecycle events.
- Multiple workers cannot apply the same observation twice.
- Recipient delivery uses existing claim fencing, entitlement checks, retry exhaustion, and manual unknown-outcome reconciliation.
- A delivered recipient is never resent on event replay; an ambiguous send is not automatically resent.
- Per-user history/read model accurately distinguishes PUBLISHED, TRIGGERED, INVALIDATED, EXPIRED, and CLOSED, with authorization preventing cross-user disclosure.

### End-to-end evidence
- Persisted analysis → eligible observation → active opportunity → lifecycle transition → outcome provenance → durable alert → entitled linked Telegram recipient.
- Startup/restart and missed-observation recovery.
- Operational metrics and failure visibility for rejected observations, lag, skipped evaluations, and delivery state.

## 6. Gate decision

**Current result: GAP — do not claim automatic lifecycle monitoring.** DEC-138 resolves the Swing daily-OHLC crossing rule only; it does not authorize runtime monitoring until provider/session eligibility, freshness, idempotent persistence, recovery, and end-to-end delivery are implemented and verified.

The generation/publication/Telegram-delivery path and the lifecycle domain/orchestrator exist as separate pieces, but automatic observation integration is not evidenced. DEC-138/DEC-139 settle the product semantics; the remaining blockers are provider/session eligibility proof, the durable observation/cursor and correction implementation, runtime wiring, and end-to-end recovery/delivery/read-model acceptance.

PR #443 adds the source-data timestamp to `SignalMarketState` and records that timestamp on terminal outcomes; its exact-head CI run #41205688356 passed all five jobs and merge commit is `f7de38c6a1c8a2e4cdb0bd29fd7eac5eed80342d`. This corrects provenance for callers that supply a state; it does not itself create an automatic observation pipeline.

M61/backtesting remains paused and is outside this gate.


## 7. Verified implementation update — 2026-11-07

- PR #450 merged the SQLite lifecycle Unit of Work. It requires the history, outcome, and alert outbox stores to share one database and commits their writes through one connection/transaction.
- PR #452 added failpoint coverage after history writes, outcome persistence, and outbox insertion; each injected failure verifies rollback across the participating stores.
- PR #454 merged persistent-history dispatcher-restart coverage and a transport-boundary test. The restart test reconstructs the dispatcher and its SQLite-backed stores, proves a pending event is delivered after restart, and proves a second dispatcher does not redeliver it. The transport-boundary test verifies the committed lifecycle rows are visible to a separate SQLite connection before the fake Telegram transport is invoked.
- PR #454 exact-head CI passed all five jobs. Post-merge `main` workflow run #42399538146 subsequently completed successfully with all five jobs passed: unit tests (including lint, type-check, and coverage), deterministic integration tests, frontend tests/build/audit, dependency audit, and container build.

These changes close the atomic persistence, rollback, restart-recovery, and tested transport-boundary acceptance items. They do **not** close automatic observation integration.

M61/backtesting remains paused and is outside this gate.


## 8. Owner decision update — 2026-11-07 (DEC-138)

The owner accepted completed daily OHLC semantics for Swing opportunities: High touching target means target reached; Low touching invalidation means invalidated; if both occur in the same completed candle, invalidation takes precedence. The decision also requires persisted source-candle identity/timestamp, provider provenance, OHLC evidence, policy version, idempotent replay, and explicit auditable correction handling. See `docs/DEC-138-COMPLETED-DAILY-OHLC-OPPORTUNITY-OBSERVATION.md`.

This closes only the crossing-semantics decision. Provider completion guarantees, EGX session calendar, stale/future/corrected data eligibility, observation cadence/recovery, entry basis, expiry, revision lineage, and user-facing history remain open. Automatic monitoring remains unimplemented until the end-to-end acceptance path passes.


## 9. Owner decision update — 2026-11-07 (DEC-139)

The owner approved the operational defaults in `docs/DEC-139-LIFECYCLE-MONITORING-OPERATIONAL-POLICY.md`: versioned operator-maintained EGX calendar until an authoritative machine-readable source is verified; evaluation after close + 60 minutes for explicitly closed sessions; provider-attested completed daily bars; STALE suppression for missing expected-session data; strict OHLC validation; no performance return without explicit entry/fill; 20 eligible-session Swing expiry; immutable linked revisions; append-only correction/reconciliation; idempotent candle replay; chronological restart reconciliation with gaps blocking progression.

DEC-139 closes the product-policy decisions, not implementation or data-provider verification. Automatic monitoring remains disabled until the acceptance boundary in DEC-139 is implemented and verified. No Yahoo redistribution rights are implied; M61 remains paused.



## 10. Session calendar implementation status — 2026-11-09

- PR #459 merged the versioned EGX session-calendar domain model. It requires explicit, contiguous date records, uses Africa/Cairo, distinguishes scheduled/open/closed/non-trading/cancelled days, and only treats explicitly confirmed closed sessions as completed.
- PR #460 merged SQLite persistence for immutable calendar versions, SHA-256 payload verification on reads, a single active-version pointer, and append-only activation/deactivation/rollback audit events.
- PR #467 merged the authenticated publication and read API with persistent runtime composition. Publication is not activation. Activation/deactivation/rollback are intentionally not exposed through HTTP because the operational coverage horizon is not yet defined.
- No real EGX calendar version has been published or activated. No weekend/holiday/session schedule is inferred. The per-day evidence registry is implemented, but publication does not yet require evidence IDs for each calendar-day claim.
- The calendar is not yet connected to lifecycle scheduling or freshness evaluation. Provider-completed-bar attestation, one-session freshness gating, durable observation identity/cursor, chronological recovery, and end-to-end lifecycle delivery remain open.

Therefore the calendar domain and persistence foundations are implemented, but the DEC-139 operational calendar/freshness gate is not complete. Automatic lifecycle monitoring remains disabled.


## 11. Initial implementation snapshot — 2026-11-13 (superseded by §11.1 and §11.2)

The following subsection records an earlier snapshot of PR #515. Any status statement here that conflicts with §11.1 or the consolidated status matrix in §11.2 is historical and must not be treated as current.

The isolated branch `feature/opportunity-lifecycle-completion` now contains the following implementation increments:

- A `CompletedDailyBarObservation` domain contract requiring DAILY timeframe, explicit source reference, finality-attestation reference, revision identity, timezone-aware timestamps, finite positive OHLC, and valid candle geometry.
- DEC-138 BUY/SELL High/Low crossing semantics, with invalidation taking precedence when both levels are touched in one candle.
- A completed-bar lifecycle orchestration path that does not require an assumed entry price and does not create realized return/R records.
- A SQLite append-only daily-observation ledger, persisted atomically with lifecycle history/outbox writes, including provider/candle/revision identity, OHLC, policy version, calendar version, and resulting status.
- Same-identity replay suppression, conflicting-payload rejection, out-of-order rejection, and explicit same-session correction deferral.
- A calendar-gated single-observation application service requiring an active versioned calendar, an explicitly CLOSED session, close confirmation, the configured close + 60-minute buffer, and a finality-verifier approval.
- An authenticated `GET /api/v1/me/opportunities` read model that exposes lifecycle history only for Telegram opportunity publication events addressed to the authenticated user. Its scope is deliberately not described as a universal in-app saved-opportunity list.

### Still not complete / not activated

- No production `DailyBarFinalityVerifier` exists. Yahoo Finance does not provide the accepted completion attestation in the current adapter, so Yahoo bars remain ineligible.
- No authoritative/accepted calendar version is published or active in the repository deployment.
- No durable per-symbol evaluation cursor, missed-session gap ledger, chronological restart recovery, or scheduled worker is wired.
- The 20-eligible-session expiry transition is not implemented.
- Materially changed setups are still not represented by a fully linked immutable revision identity; current publication history can record `PUBLISHED_VERSION` under the existing identity.
- Correction/reconciliation workflow for a changed source revision is not implemented; the normal evaluator fails closed on same-session corrections.
- No end-to-end provider → calendar → lifecycle → Telegram → user-history acceptance run has been completed.
- At the time of this initial snapshot, CI for the latest draft head had not yet completed. This statement is superseded by §11.2, which records the later exact-head CI result.

**Current gate result remains GAP.** These changes are implementation foundations only. Do not enable automatic lifecycle monitoring or claim production completion until every remaining gate above is implemented and verified.


### 11.1. Further implementation update — 2026-11-13

The same draft branch now also contains:

- Opportunity-specific observation identity: one market candle can be evaluated against multiple published opportunities for the same symbol without one signal overwriting or suppressing another.
- Immutable linked signal revisions: materially changed active setups receive a new signal identity, parent link, monotonic revision number, and snapshot digests. Terminal opportunities cannot be revised; the revision chain is linear and latest-parent-only.
- Revision-aware lifecycle writes: status transitions remain attached to the exact child revision rather than falling back to the original identity.
- Twenty-session expiry: a separate `EXPIRED` terminal event is emitted only after 20 chronologically completed, calendar-eligible sessions have each passed the provider-finality gate and have an accepted bar.
- Chronological recovery: the latest append-only observation per opportunity is the durable cursor. The evaluator resumes after that cursor, stops at the first missing/unverified session, and does not process later sessions.
- Durable stale-gap events: missing/invalid session evidence is recorded as append-only `STALE` events; a later successfully committed observation appends a `RESOLVED` event.
- Explicit source correction records: a corrected source revision is recorded append-only with operator identity, reason, calendar version, and `RECORDED_NOT_REEVALUATED` disposition. Immutable review decisions (`REJECTED`, `ACCEPTED_NO_STATE_CHANGE`, `REPLAY_REQUIRED`) are also persisted append-only; progression fails closed until the latest decision explicitly rejects the correction or confirms no lifecycle-state change. `REPLAY_REQUIRED` remains blocking because corrected-candle replay/rebuild and downstream compensating-notification semantics are not implemented.
- Protected operator APIs expose correction history and accept attributed review decisions. They require an active, individually attributable operator credential; the legacy shared operator identity is not sufficient.
- Authenticated per-user lifecycle history now includes linked revision metadata; it is scoped to Telegram publication events addressed to that user.

### Remaining activation and acceptance blockers

- The evaluator and recovery use cases are implemented but are not wired to a production scheduled worker.
- No production provider finality verifier is implemented. The current Yahoo Finance adapter cannot satisfy the accepted final/complete-bar contract.
- No accepted active EGX session-calendar version has been verified in the target deployment.
- Corrected-candle replay/rebuild is still not implemented. `REPLAY_REQUIRED` intentionally blocks progression; there is no automated reconstruction of downstream lifecycle events or defined compensating-notification policy.
- No full end-to-end acceptance run has yet verified provider retrieval, calendar gating, chronological recovery, expiry, Telegram delivery, and authenticated user history together.
- The draft PR has not been merged. Exact-head CI status is recorded in §11.2.

**Gate remains GAP / NOT ACTIVATED.** The domain and persistence foundations are implemented on the isolated branch, but do not enable production monitoring or describe Opportunity Lifecycle as complete until the production provider, active calendar, worker wiring, correction disposition, and exact-head CI/e2e gates pass.


### 11.2. Consolidated authoritative status — 2026-11-13 (reconciled)

This matrix is the current source of truth for PR #515. It supersedes earlier snapshots and stale status statements above while preserving them as historical design context.

| Capability / gate | Current status | Evidence / remaining condition |
|---|---|---|
| Completed daily OHLC contract and BUY/SELL crossing semantics | IMPLEMENTED | Domain contract and evaluator tests; invalidation wins on same-candle dual touch |
| Durable append-only observation evidence and atomic lifecycle/history/outbox writes | IMPLEMENTED | SQLite Unit of Work and observation ledger; replay identity and evidence are persisted |
| Idempotent replay, conflicting-payload rejection, and out-of-order rejection | IMPLEMENTED | Covered by lifecycle application and persistence tests |
| Calendar-gated evaluation and close + 60-minute eligibility rule | IMPLEMENTED IN APPLICATION | Requires an active deployment calendar version; no accepted active version is currently verified |
| Opportunity-specific observation identity | IMPLEMENTED | A single market candle can be evaluated independently against multiple published opportunities |
| Immutable linked revisions | IMPLEMENTED | New material active setup gets a child identity, parent link, monotonic revision, and snapshot digests |
| Twenty-eligible-session expiry | IMPLEMENTED | Distinct EXPIRED event after 20 chronologically completed, calendar-eligible sessions that pass provider finality |
| Durable chronological recovery and stale-gap blocking | IMPLEMENTED IN APPLICATION | Per-opportunity committed observation history is used for chronological progression; missing/unverified session blocks later progression; STALE/RESOLVED evidence is append-only. A production scheduled worker is not wired |
| Correction intake and attributed review decisions | IMPLEMENTED | Append-only correction/review records and protected operator APIs exist |
| Corrected-candle replay/rebuild | IMPLEMENTED | Deterministic chronological rebuild from publication baseline, latest REPLAY_REQUIRED review gate, unresolved-sibling blocking, replay digest/audit, and idempotent repeated rebuild |
| Compensating notification behavior for corrected outcomes | IMPLEMENTED | Unsent alerts/recipient rows are superseded; confirmed delivered recipients receive a scoped corrective event; DELIVERY_UNKNOWN is not resent; in-flight sends block replay |
| Production DailyBarFinalityVerifier/provider | NOT IMPLEMENTED | The application boundary accepts an injected verifier and fails closed when finality is not verified, but runtime has no production verifier and no provider is approved. Yahoo remains ineligible |
| Active accepted EGX calendar version in target deployment | NOT VERIFIED / NOT ACTIVE | Calendar domain, immutable persistence, evidence-gated publication, individual operator identity, and audit primitives exist; no evidenced calendar version is published/activated in target deployment |
| Calendar activation policy | OWNER DECISION / IMPLEMENTATION GAP | Cursor-derived coverage is proposed but not approved; no durable lifecycle evaluation cursor or bootstrap policy is implemented. Activation endpoints remain unavailable |
| Scheduled production worker | NOT WIRED | Evaluator/recovery use cases are not connected to a production schedule; keep disabled until provider and calendar gates pass |
| Full provider → calendar → lifecycle → Telegram → authenticated user-history E2E acceptance | NOT PASSED | Must exercise normal progression, restart/gap recovery, expiry, delivery, correction replay, and per-user authorization together |
| Provider outreach / selection | NOT AUTHORIZED | EGID is research-only; no provider contact, quote request, credential request, or selection is authorized |
| CI for code implementation | PASS | Run #43405799607 on code commit `1d2b902a646174521b143cf19c1b7c7c126cd072`; all six jobs successful |
| CI for documentation-only updates | TRACK LIVE CHECKS | Documentation-only commits trigger the repository CI workflow; use the current PR checks for the latest head and never infer success from an earlier commit |
| PR state | OPEN / DRAFT / NOT MERGED | PR #515 remains draft and unmerged; do not merge or activate production monitoring while activation blockers remain |

**Gate decision: GAP / NOT ACTIVATED.** Correction replay/rebuild and notification compensation are implemented; the remaining blockers are provider finality, an evidence-backed active calendar and approved activation/bootstrap policy, scheduled worker wiring, and full deployment-level E2E acceptance. CI success does not substitute for those operational gates. Automatic monitoring must remain disabled.

**Next implementation order (provider-neutral and owner-controlled):**
1. Complete internal fail-closed contract and runtime-composition verification without selecting or contacting a provider.
2. Resolve the calendar activation bootstrap/cursor policy as an explicit owner decision; implement only after approval, and do not invent calendar dates or evidence.
3. Implement a production finality adapter only after the owner authorizes provider selection and written technical/commercial evidence is obtained.
4. Wire the scheduled worker behind provider and calendar gates, disabled by default.
5. Pass full provider → calendar → lifecycle → Telegram → authenticated user-history E2E acceptance.

M61/backtesting remains paused and outside this gate.
