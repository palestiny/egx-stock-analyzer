# Signal Lifecycle Observation Integration — Design Gate

**Status:** Integration gap confirmed; observation and market-data semantics must be accepted before wiring  
**Scope:** Non-M61 opportunity lifecycle observation, invalidation, terminal outcomes, and Telegram event publication  
**Related owner policy:** DEC-135 (accepted 2026-10-31)  
**Related implementation:** `SignalLifecycleOrchestrator`, `SignalMarketState`, `GenerateSignal`, `PublishSignalOpportunity`

## 1. Verified current composition

The repository currently has these separate capabilities:

- `GenerateSignal` derives an ACTIVE signal from the latest persisted analysis result and carries the analysis source-bar `data_timestamp`.
- `PublishSignalOpportunity` records a published signal and creates an immutable `SIGNAL_PUBLISHED` alert event in the durable SQLite outbox.
- `DispatchSignalAlertOutbox` handles per-recipient Telegram delivery, entitlements, retry/reconciliation, and durable recipient state.
- `SignalLifecycleOrchestrator` can transition a supplied signal using a supplied `SignalMarketState`, record a terminal market-proxy outcome, and publish a lifecycle alert event.
- `SignalLifecycleOrchestrator` is constructed in `app/infrastructure/runtime.py` and exposed on the runtime object.

The inspected API publication route `POST /api/v1/opportunities/{symbol}/publish` calls `GenerateSignal` and `PublishSignalOpportunity`. It does not call `SignalLifecycleOrchestrator.process` or `invalidate_for_evidence_change`. No completed end-to-end observation path has been evidenced that supplies fresh market observations to the lifecycle service after analysis updates.

Therefore the repository must not currently describe target-hit/stop/invalidation monitoring as an automatically operating end-to-end feature. The presence of the domain transition and a constructed orchestrator is not proof of active observation.

## 2. Owner-approved constraints

- Published opportunities are immutable versions; a materially revised setup must not silently rewrite the original publication.
- Re-evaluation and invalidation must be traceable.
- No actual trade execution or portfolio P&L is implied; lifecycle outcomes are market-proxy observations.
- Missing analysis, unavailable source data, or incomplete coverage is not evidence that an opportunity became invalid.
- Delayed/daily data must not be presented as live intraday monitoring.
- Do not change signal-generation rules, scoring, target/invalidation levels, or automatic recommendation policy without a separate accepted decision.

## 3. Decisions required before wiring

Do not infer these from generic price fields:

1. **Observation price semantics:** Which value is authoritative for transition: daily close, last trade, or a bar's high/low? The current analysis result exposes a current-price value, but its use as a completed-bar close or intraday last trade must be verified per provider and timeframe.
2. **Crossing semantics:** Whether a target or invalidation is considered crossed by close-only, OHLC range, or another documented rule. If one candle spans both target and invalidation, the current domain rule prioritizes invalidation because intrabar path is unknown; owner must confirm that conservative behavior for the product.
3. **Data eligibility:** What constitutes a completed/usable bar, how corrections are handled, and how stale, future-dated, duplicated, or missing observations are rejected. This depends on provider timestamp semantics and an approved EGX session calendar.
4. **Observation cadence:** Whether evaluation runs after every accepted analysis result, once after a completed session, or on a separately licensed intraday feed. Do not use an in-process timer as a substitute for durable scheduling.
5. **Expiry policy:** Define `expires_at`, valid session/timeframe semantics, and what causes EXPIRED. The status enum contains EXPIRED/CLOSED, but the current transition function only transitions ACTIVE to TRIGGERED or INVALIDATED; no expiry duration or close policy is inferred here.
6. **Revision semantics:** Which changes in entry zone, invalidation, targets, direction, timeframe, evidence, confidence, or strategy version constitute a new version versus invalidation of the prior published setup. Preserve lineage and avoid duplicate Telegram notifications.
7. **Outcome price semantics:** Define how gaps through invalidation and target overshoots are recorded. A stop threshold, observed close, and executable fill are different values. Never call a market-proxy return an executed result.
8. **Recovery and operations:** Define durable observation identity/cursor, duplicate handling, late corrections, replay, missed-run reconciliation, and operator-visible failures.

## 4. Recommended application flow

After owner decisions and provider/session verification, implement a dedicated application use case rather than calling domain services ad hoc from API handlers:

1. Receive a successfully persisted analysis snapshot with explicit symbol, timeframe, provider, source-bar timestamp, and observation/cutoff metadata.
2. Validate the observation against the accepted data eligibility policy.
3. Load the active published opportunity version for the symbol/timeframe/strategy identity.
4. If the setup's supporting evidence materially changed, apply the approved revision/invalidation policy. A missing candidate or failed analysis must not invalidate the existing opportunity.
5. Construct `SignalMarketState` from the verified observation price and its actual source-data timestamp. Keep source-data time separate from processing/observation time.
6. Apply the pure domain transition and create an immutable lifecycle event with a stable idempotency key derived from signal version and source observation identity.
7. Persist transition, outcome, and alert intent through a reviewed durable transaction/outbox boundary. The current separate history, outcome, and outbox stores do not share one transaction; do not claim cross-store atomicity.
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
- Per-user history/read model accurately distinguishes PUBLISHED, TRIGGERED, INVALIDATED, EXPIRED, and CLOSED.

### End-to-end evidence
- Persisted analysis → eligible observation → active opportunity → lifecycle transition → outcome provenance → durable alert → entitled linked Telegram recipient.
- Startup/restart and missed-observation recovery.
- Operational metrics and failure visibility for rejected observations, lag, skipped evaluations, and delivery state.

## 6. Gate decision

**Current result: GAP — do not claim automatic lifecycle monitoring.**

The generation/publication/Telegram-delivery path and the lifecycle domain/orchestrator exist as separate pieces, but automatic observation integration is not evidenced. The observation-price, crossing, data-eligibility, expiry, revision, and outcome semantics must be resolved before the orchestration is wired.

The PR #443 change adds the source-data timestamp to `SignalMarketState` and records that timestamp on terminal outcomes. It corrects provenance for callers that supply a state; it does not itself create an automatic observation pipeline.

M61/backtesting remains paused and is outside this gate.
