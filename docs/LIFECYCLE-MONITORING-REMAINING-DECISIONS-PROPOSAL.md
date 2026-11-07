# Lifecycle Monitoring — Remaining Product Decisions (Proposal)

**Status:** Proposal for owner approval; none of these defaults is an accepted product decision yet.
**Date:** 2026-11-07

The completed-daily-OHLC crossing rule is accepted in DEC-138. The following defaults are recommended to close the remaining product-policy questions without inventing market-data guarantees.

| Topic | Recommended default | Reason / guardrail |
|---|---|---|
| Session calendar | Versioned, operator-maintained EGX session calendar until an authoritative machine-readable EGX source is verified. No weekday-only inference. | Prevent holiday and exceptional-closure errors; every observation references calendar version and session date. |
| Observation timing | One scheduled evaluation after the configured session close plus a 60-minute buffer; only sessions explicitly marked closed in the calendar are eligible. | Allows delayed daily-bar publication; buffer is a conservative operational default, not a provider guarantee. |
| Provider eligibility | Adapter must explicitly attest daily timeframe, source identity, source timestamp, and final/complete status. If provider cannot establish completion, suppress lifecycle transitions. | Yahoo Finance must not be treated as a guaranteed final-bar source; commercial reuse rights remain a separate gate for subscriber-facing data. |
| Freshness | If the expected completed session has no eligible bar by the next scheduled evaluation, mark observation status STALE and suppress target/invalidation transitions until reconciled. | Avoid false negatives/positives from old data. |
| OHLC validation | Reject bars with missing/non-finite values, non-positive prices, High below Open/Close, Low above Open/Close, or Low above High. | Invalid bars cannot drive lifecycle transitions. Preserve rejected evidence/reason for operations. |
| Entry basis / performance | Separate lifecycle level monitoring from performance accounting. Do not calculate realized return/R until an entry is explicitly recorded; if no fill/entry record exists, outcome is level-reached/invalidated only. | Avoid inventing an entry fill from an entry zone or assuming execution. |
| Expiry | Default proposal: expire an active Swing opportunity after 20 eligible EGX trading sessions, not calendar days; expiry is a distinct terminal event. | Bounded opportunity lifetime while respecting market closures. Make duration configurable by strategy only after owner approval. |
| Revised opportunity | A materially changed setup creates a new immutable signal revision linked to the prior one; never overwrite prior evidence or terminal events. | Preserves audit trail and lets users distinguish revised recommendations. |
| Corrections / replay | Append correction/reconciliation records; never silently rewrite prior evaluation. Reprocessing same provider + symbol + timeframe + candle timestamp + revision is idempotent. | Deterministic recovery and auditability. |
| Missed sessions / recovery | On restart, reconcile all eligible closed sessions since the last durable cursor in chronological order; stop and mark a gap if any required session lacks eligible data. | Avoid skipping target/invalidation events or evaluating out of order. |

## Proposed acceptance boundary

Automatic lifecycle monitoring remains disabled until:
1. The owner approves the policy defaults (or explicitly changes them).
2. A provider adapter can prove completed daily-bar eligibility for the selected environment.
3. The versioned session calendar and freshness gate are implemented.
4. Observation identity, append-only evidence, idempotency, and restart reconciliation pass integration tests.
5. End-to-end tests prove target, invalidation, same-bar dual touch, duplicate replay, missing/stale data, correction, and missed-session recovery.

This proposal does not authorize Yahoo-derived market-data redistribution to paid users, does not change signal scoring/levels, and does not resume paused M61 backtesting.
