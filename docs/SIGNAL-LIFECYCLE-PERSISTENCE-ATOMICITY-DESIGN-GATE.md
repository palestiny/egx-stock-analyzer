# Signal Lifecycle Persistence Atomicity — Design Gate

**Status:** GAP confirmed; recommended design documented, implementation not authorized by this document alone  
**Scope:** Atomic persistence of one lifecycle transition, its market-proxy outcome (when applicable), and its durable alert intent  
**Related policy:** DEC-135 (immutable opportunity versions, traceable lifecycle events, durable auditable Telegram delivery, manual trading only)  
**Related gates:** `SIGNAL-LIFECYCLE-OBSERVATION-INTEGRATION-DESIGN-GATE.md`, `TELEGRAM-DELIVERY-CONCURRENCY-DESIGN-GATE.md`  
**Out of scope:** observation-price/cadence/expiry policy, signal scoring, strategy changes, Telegram transport retry policy, broker execution, M61/backtesting

## 1. Verified current persistence boundary

The runtime composes all three relevant SQLite adapters with `config.analysis_database_path`:

- `SQLiteSignalHistoryStore`
- `SQLiteTrackRecordStore`
- `SQLiteAlertOutbox`

They therefore target the same SQLite database file in the standard runtime. However, each adapter opens and commits its own connection/transaction. Sharing a file does **not** make separate transactions atomic.

The current `SignalLifecycleOrchestrator.process` order is:

1. Resolve/create signal identity and append `CREATED` history when needed.
2. Calculate the pure domain transition.
3. Publish the lifecycle alert to the outbox.
4. Record a terminal market-proxy outcome for `TRIGGERED` or `INVALIDATED`.
5. Append the terminal signal-history event.

The stores are individually idempotent for an identical record and reject conflicting payloads. That is useful but does not provide a cross-store transaction or a recovery protocol.

### Failure windows

| Failure point | Durable state that may remain |
|---|---|
| After outbox publish, before outcome write | Alert intent exists; outcome/history transition absent |
| After outcome write, before history append | Alert intent and outcome exist; latest history may still be ACTIVE |
| Alert publish succeeds, later retry sees terminal history | Existing early-return path may not repair a missing outcome/history side effect |
| Retry supplies a different entry price for the same terminal signal | Outcome store rejects a conflicting outcome; no explicit command/observation identity explains whether this is a replay conflict or a new observation |

The same failure class exists in `invalidate_for_evidence_change`: it publishes the alert before appending history, without a shared transaction. That path intentionally does not create a trade outcome.

**Conclusion:** current behavior must not be described as atomically persisting lifecycle transition, outcome, and alert intent. Telegram delivery is a later external side effect and must remain outside the SQLite transaction.

## 2. Invariants required

A completed lifecycle command must satisfy all of the following:

1. The signal-history transition, optional market-proxy outcome, and durable alert-outbox event are committed together, or none of those writes are committed.
2. A process crash before commit leaves no partial terminal transition.
3. A process crash after commit but before Telegram dispatch leaves a durable outbox event that the existing dispatcher can recover.
4. Replaying the same accepted lifecycle command does not create duplicate history, outcomes, or alert events.
5. A conflicting replay is surfaced explicitly; it must not silently overwrite an earlier observation, outcome, or published rationale.
6. Telegram network I/O never occurs while holding the SQLite write transaction.
7. Existing per-recipient claim fencing, entitlement checks, bounded definite-failure retries, and manual reconciliation of `DELIVERY_UNKNOWN` remain authoritative.
8. Market-proxy outcomes remain explicitly distinct from executed trades or portfolio P&L.

## 3. Options considered

### A. Keep separate stores and reorder writes — rejected

Writing history/outcome before publishing the alert only moves the failure window. If alert publication then fails, a retry can encounter terminal history and skip the missing alert. Reordering alone cannot satisfy the invariants.

### B. Compensating writes / best-effort repair — not recommended as the primary guarantee

A reconciliation job could compare terminal history, outcomes, and outbox rows and repair missing records. This requires durable command identity, deterministic reconstruction of the exact event/outcome, conflict policy, and safe concurrency. Without those, repair can invent or duplicate business events. Reconciliation may still be useful as a detection/repair layer after atomic writes exist, but it is not a substitute for the transaction.

### C. Shared SQLite Unit of Work for lifecycle writes — recommended

Introduce a lifecycle-specific Unit of Work that owns one SQLite connection and one `BEGIN IMMEDIATE` transaction for a single lifecycle command. Refactor the three persistence adapters (or add transaction-bound repository methods) so that identity/history, optional outcome, and outbox insertion can all use that exact connection.

The application layer should depend on a lifecycle persistence boundary rather than coordinate independently committing stores. The unit of work should expose only the operations required by the lifecycle command, not leak SQLite into domain entities.

Suggested transaction shape:

1. Begin one write transaction.
2. Resolve the stable signal identity and current lifecycle record under that transaction.
3. Validate command replay identity and compare any existing event/outcome payload.
4. Persist the lifecycle history event.
5. Persist the optional market-proxy outcome.
6. Insert the immutable alert event into the outbox.
7. Commit once.

Any exception before commit rolls back all three categories of write. The dispatcher later claims and sends the already-committed outbox event using its existing independent delivery state machine.

`BEGIN IMMEDIATE` serializes competing SQLite writers at the database boundary. It does not replace unique constraints, deterministic event identity, or explicit replay-conflict handling.

### D. Move lifecycle persistence to a separate event-sourcing platform — deferred

A dedicated event store/message broker could provide a larger distributed architecture, but the current runtime already uses one SQLite database for these records. Introducing another persistence platform now would increase operational complexity without being required to establish the needed local atomicity.

## 4. Recommended application boundary

Create a focused lifecycle Unit of Work / repository port in the application layer. Its implementation is SQLite-backed and receives the configured analysis database path. The same connection must be passed to all writes in one command.

Keep domain transition logic pure. The orchestrator should calculate the transition and outcome, then ask the Unit of Work to atomically persist the resulting records and outbox intent. Do not let the domain layer open connections or know about SQL.

The in-memory test implementation must preserve the same all-or-nothing semantics, so application tests can verify rollback behavior without relying only on SQLite integration tests.

### Identity and replay requirements

Atomicity does not by itself solve command idempotency. Before implementation, define a stable lifecycle-command identity from the accepted source-observation identity (or another explicitly approved command key). The same key with the same canonical payload is an idempotent replay; the same key with a different payload is a conflict.

The current event key includes `occurred_at`, while the outcome is keyed by `signal_id`. Those keys are insufficient to distinguish multiple legitimate observations over one signal from a conflicting retry. Do not invent a source observation ID or change event identity until the observation integration gate resolves source provider, symbol, timeframe, bar identity, correction/version semantics, and accepted cutoff.

The existing `entry_price` parameter also requires a stable, documented basis before automatic observation is wired. Do not infer a fill or trade execution from the signal entry zone.

## 5. Required acceptance tests

### Atomic commit / rollback
- Inject failure after history write, after outcome write, and before outbox insert; verify no partial lifecycle command is visible after reopening the database.
- Verify successful command writes all expected records in one transaction.
- Verify evidence-change invalidation atomically writes history and alert intent without creating a trade outcome.
- Verify a failed transaction leaves a retryable state and a successful retry produces exactly one logical event.

### Replay / conflict
- Same command identity and identical payload replays without duplicates.
- Same command identity with changed observation, entry basis, outcome, or alert snapshot fails explicitly.
- Concurrent workers attempting the same command cannot create duplicate lifecycle events or outcomes.
- A later distinct accepted observation can progress an ACTIVE signal; an older observation cannot overwrite a newer state. The observation-order rule must be supplied by the observation gate.

### Recovery / dispatch
- Crash after database commit but before dispatcher invocation leaves a pending outbox event that is dispatched after restart.
- Re-dispatch does not duplicate a recipient already marked delivered.
- Ambiguous Telegram send remains `DELIVERY_UNKNOWN` and is never automatically resent.
- Definite failures continue to follow DEC-137's bounded retry policy.
- No Telegram network request is made while the lifecycle SQLite transaction is open.

### Proxy-outcome wording
- API/report output identifies outcomes as market-observation proxies.
- No test or user-facing metric labels these records as executed trades, realized brokerage fills, or portfolio P&L.

## 6. Implementation sequence

1. Add the application Unit of Work contract and in-memory semantics.
2. Add SQLite transaction-bound persistence for signal identity/history, optional outcome, and outbox event.
3. Refactor the lifecycle orchestrator to use the single commit boundary for both normal transitions and evidence-change invalidation.
4. Add failpoint, rollback, replay-conflict, concurrency, and restart tests.
5. Verify runtime composition uses the same configured database and no nested adapter transaction escapes the Unit of Work.
6. Run full CI; inspect PR-head and post-merge main runs separately.
7. Update the observation integration gate only to mark the persistence boundary complete; do not mark automatic observation complete until its independent policy requirements pass.

## 7. Gate decision

**Current result: GAP — atomic lifecycle persistence is not implemented.**

**Recommendation:** approve Option C, a lifecycle-specific SQLite Unit of Work with a single transaction for history + optional outcome + alert outbox. This is the smallest design that satisfies the required durability invariant using the existing database and operational stack.

This recommendation does **not** authorize implementation of observation cadence, price/crossing semantics, expiry, opportunity revision policy, or entry-price assumptions. Those remain governed by `SIGNAL-LIFECYCLE-OBSERVATION-INTEGRATION-DESIGN-GATE.md` and DEC-135.

M61 remains paused and untouched.
