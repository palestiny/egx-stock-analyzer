# M25 — Alert Delivery & Notification Boundary — Completion

**Status:** Complete  
**Completed:** 2026-09-19  
**Implementation PR:** #39  
**Implementation merge commit:** `b83f8793e59a951506390e299219f48272d57a6a`

## Delivered

M25 implemented the accepted provider-neutral alert delivery boundary.

The delivered capability:

- accepts an existing `AlertCandidate`;
- carries the immutable analysis `snapshot_id`;
- uses `(stock_id, snapshot_id)` as logical alert identity;
- uses `(stock_id, snapshot_id, channel)` as the delivery idempotency key;
- persists `PENDING`, `DELIVERED`, and `FAILED` delivery state separately from analysis-result state;
- isolates provider failures from analytical and historical state;
- keeps the provider behind a provider-neutral application boundary;
- executes synchronously and sequentially;
- treats successful delivery as terminal;
- does not implicitly retry failed deliveries.

## Persistence

SQLite delivery state is implemented independently from the analysis-result store.

Delivery state survives store recreation and successful delivery remains idempotent across process/store recreation.

## TDD / CI Validation

Focused tests cover successful delivery, snapshot identity propagation, duplicate successful delivery, provider failure isolation, independent success/failure records, explicit non-retry semantics, SQLite persistence across store recreation, and SQLite idempotency after store recreation.

GitHub Actions Run #668 completed successfully for implementation head `d8a2759bde75b8530acfaa78af4d2939c4dca426` before merge.

## Boundary Preserved

M25 does not introduce:

- new analytical signals;
- classification or threshold changes;
- ranking changes;
- AI decisions;
- trading;
- user notification preferences;
- distributed queues;
- provider retry engines;
- engagement analytics;
- external notification-provider integration;
- API/dashboard delivery orchestration.

These capabilities remain future work and require their own design decisions where they cross the current boundary.
