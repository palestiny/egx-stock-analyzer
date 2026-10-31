# Telegram Delivery Concurrency — Design Gate

**Status:** Proposed technical design; implementation not authorized by this document alone  
**Scope:** Per-recipient Telegram delivery ownership and recovery  
**Out of scope:** Retry timing/attempt limits, opportunity expiry, subscription policy, message content, scoring, automatic trading

## 1. Verified current behavior

The current dispatcher reads outbox records through `pending()`, then independently reads/creates a per-recipient delivery row and sends the Telegram message. The SQLite delivery table has a unique key on `(event_id, user_id, channel)`, but `INSERT OR IGNORE` only makes row creation idempotent; it does not grant exclusive ownership of the send operation.

The dispatcher marks a recipient delivered or failed only after the transport call returns. Consequently, two dispatcher processes can both observe a pending/failed delivery and both call the transport before either persists its result.

The current delivery record has no claim token, lease expiry, in-progress state, or conditional completion operation.

## 2. Required guarantees and honest limits

The implementation should guarantee:

- At most one valid database claim for a given event/recipient/channel at a time.
- Only the holder of the current claim token may renew or complete that claim.
- A crashed worker's claim can eventually be recovered.
- A stale worker cannot overwrite a newer worker's persisted delivery state.
- Successfully delivered recipients are never sent again during normal replay.
- One recipient's failure does not cause successful recipients to be resent.

The implementation must **not** claim exactly-once delivery. Telegram is an external side effect and does not participate in the SQLite transaction. If a process loses the response after Telegram accepted a message, the application cannot know with certainty whether the message was delivered. A retry may therefore create a duplicate.

The supported guarantee is durable, auditable, concurrency-controlled **at-least-once** delivery, with ambiguous outcomes explicitly represented rather than hidden.

## 3. Proposed state model

Per-recipient state:

- `PENDING`: persisted and eligible to be claimed.
- `CLAIMED`: a worker owns the record but has not begun the external send.
- `SENDING`: the owner has crossed the boundary immediately before calling Telegram.
- `DELIVERED`: transport acknowledged success.
- `FAILED`: transport returned a definite failure eligible for policy-governed retry.
- `SUPPRESSED`: recipient is ineligible; terminal for this event.
- `DELIVERY_UNKNOWN`: the worker/transport outcome became ambiguous after send initiation (for example, process loss or timeout where remote acceptance cannot be ruled out).

A claim should carry a fresh opaque token and an expiry timestamp. Claim acquisition must be a single atomic database operation, not a read-then-write sequence. Completion and renewal must be conditional on the current token. A stale token must update zero rows and must not mutate the current owner's record.

Recovery of an expired `CLAIMED` record is safe to return to `PENDING`, because the send boundary has not been crossed. Recovery of an expired `SENDING` record must become `DELIVERY_UNKNOWN`; automatically returning it to `PENDING` would conceal the duplicate-delivery trade-off.

## 4. Persistence and transaction approach

- Keep the claim in the existing per-recipient delivery row so the uniqueness boundary remains `(event_id, user_id, channel)`.
- Add claim token, lease expiry, and state needed to distinguish pre-send claim from in-flight send.
- Use a short SQLite write transaction for claim acquisition and conditional state changes. Never hold a database transaction open while calling Telegram.
- Use a token-conditional update as a fencing check for renew/complete operations.
- Add a schema migration that is safe for existing rows; existing PENDING/FAILED rows remain eligible, DELIVERED/SUPPRESSED remain terminal, and no historical row is silently treated as currently sending.
- Ensure event-level outbox finalization does not mark an event terminal merely because another worker currently owns all eligible recipient deliveries.

## 5. Dispatcher orchestration requirements

1. Persist/get the recipient delivery row.
2. Re-evaluate user active state and entitlement before starting an attempt.
3. Atomically claim the recipient delivery.
4. Persist transition to `SENDING` immediately before the transport call.
5. Call Telegram without holding a database transaction.
6. Complete with the same claim token as DELIVERED or definite FAILED.
7. If completion fails because the lease/token is no longer current, record an operational diagnostic; do not overwrite the newer owner's state.
8. Finalize the event only after evaluating all recipient states, including CLAIMED/SENDING/DELIVERY_UNKNOWN; active work must not be mistaken for “no eligible recipients”.

The implementation must preserve the current behavior that an entitlement revoked or expired before a retry suppresses that recipient rather than sending.

## 6. Retry policy is a separate decision

This design deliberately does not select numeric lease duration, transport timeout, retry delay, backoff multiplier, maximum attempts, or exhaustion state. Those values require an explicit operational policy and must be configuration-driven where appropriate.

Retry scheduling must be durable (`next_attempt_at` or equivalent) and use timezone-aware UTC instants. A FAILED record is not immediately retryable unless its scheduled time is due. Retry exhaustion must be explicit and observable, not an unbounded retry loop.

`DELIVERY_UNKNOWN` requires a separately approved handling policy. Options:

- **Conservative/manual resolution:** do not auto-resend; expose the event/recipient for operator reconciliation. Lowest duplicate risk, but can leave a message undelivered.
- **At-least-once automatic retry:** retry after a configured delay and disclose duplicate risk. Better delivery recovery, but duplicates are possible.

No option is selected here.

## 7. Required tests before implementation acceptance

- Two independent dispatcher instances race to claim the same recipient; exactly one claim succeeds.
- A second worker cannot claim a non-expired CLAIMED/SENDING record.
- Expired CLAIMED record is recoverable.
- Expired SENDING record becomes DELIVERY_UNKNOWN, not silently PENDING.
- A stale claim token cannot renew, mark delivered, or mark failed after a newer claim exists.
- Process restart preserves claim/recovery behavior.
- Partial recipient success never resends DELIVERED recipients.
- Entitlement expiry/revocation before retry suppresses delivery.
- One worker processing an event does not cause another worker to finalize it as no-eligible-recipient.
- Transport timeout/connection loss produces the documented ambiguous outcome.
- Migration preserves existing records and status semantics.
- Retry scheduling, backoff, exhaustion, and manual/automatic unknown-outcome handling are tested against the separately accepted retry policy.

## 8. Acceptance gate

Implementation may begin only after the owner accepts:

1. Whether `DELIVERY_UNKNOWN` is manually reconciled or automatically retried (and with what duplicate-risk disclosure).
2. Operational lease/transport timeout relationship.
3. Retry schedule, maximum attempts, and terminal exhaustion behavior.
4. Whether operator tooling is required for resolving unknown outcomes.

Until then, retain the current production behavior and report the concurrency gap honestly. Do not claim exactly-once delivery.


## 9. Additional code-review findings — 2026-10-31

A second pass over the dispatcher and SQLite outbox confirms additional behavior that the implementation must address:

- `SQLiteAlertOutbox.pending()` returns both `PENDING` and `FAILED` records. There is no persisted `next_attempt_at`, backoff schedule, or maximum-attempt/exhaustion filter in this path. Each invocation of the dispatcher can therefore make a FAILED event eligible again immediately.
- `DispatchSignalAlertOutbox.execute()` catches every `Exception` raised by `send_message()` and records the recipient as `FAILED`. The current contract does not distinguish a definite remote rejection from an ambiguous timeout/connection loss after Telegram may have accepted the message.
- The event-level outbox is marked FAILED when any recipient fails, while recipient-level successes are retained as DELIVERED. This supports partial-recipient replay, but event-level retry eligibility is not itself sufficient to decide which recipient may be sent again.
- Event-level terminal suppression must be guarded against concurrent recipient work. A worker that sees no completed delivery must not mark the event as having no eligible recipients while another worker owns a valid claim.
- The current `attempts` field is incremented on completion (`mark_delivered` / `mark_failed`), not when an attempt is claimed or initiated. It therefore cannot reliably count crashes between claim and completion without changing its documented meaning or adding a separate attempt/claim counter.

These are verified observations of the current implementation, not a proposed operational policy. In particular, this document does not choose automatic retry for ambiguous outcomes or a numeric retry budget.
