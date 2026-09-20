# M28 — Automatic Alert Delivery Policy MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design Gate:** `docs/DEC-087-M28-AUTOMATIC-ALERT-DELIVERY-POLICY-DESIGN-GATE.md`  
**Implementation PR:** #46

## Accepted Outcome

M28 adds a dedicated post-analysis automatic-delivery capability.

It consumes successful symbols from a completed market-analysis `Execution`, resolves existing alert candidates through `GetAlertCandidate`, and delegates delivery to the existing M25 `DeliverAlert` boundary.

The MVP:

- uses one configured default channel: `telegram`;
- processes successful symbols in deterministic normalized-symbol order;
- skips symbols with no existing alert candidate;
- continues after individual delivery failures;
- reports delivery-specific aggregate state and counts;
- adds no automatic retry;
- relies on M25 snapshot/channel idempotency;
- does not trigger fresh analysis or recalculate alert eligibility.

## Boundary

```
Completed Market Analysis Execution
          ↓
Automatic Alert Delivery Policy
          ↓
GetAlertCandidate
          ↓
DeliverAlert
          ↓
NotificationProvider
          ↓
Configured Provider
```

Analysis remains independent from notification availability. A delivery failure never changes the originating analysis execution.

## Validation

PR #46 was validated by GitHub Actions Run #763 on implementation head `06a109c573eb9994a46296ede3ea3b61fd17f584`.

- Python unit-tests job: **success**
- Frontend tests job: **success**
- Frontend production build: **success**

The implementation was merged into `main` as commit `768596381b098f1ff54b09c14e90043ed18e25ed`.

## Explicitly Deferred

- automatic provider retry;
- asynchronous queues/workers;
- multiple-channel fan-out;
- user notification preferences;
- delivery analytics;
- scheduled delivery policy;
- bulk delivery beyond the market-analysis execution input;
- trading execution;
- AI notification decisions.

The next capability requires a separate design gate.
