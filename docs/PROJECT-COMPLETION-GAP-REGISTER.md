# Project Completion Gap Register

**Status:** Active non-M61 engineering/acceptance register  
**Updated:** 2026-10-28  
**Baseline:** `main` after PR #412 merge (`1861931814ddd781ca1284bd48c8dc8e7629202a`)  
**M61:** Explicitly paused by owner request; do not advance M61/backtesting work until the owner resumes it.

This register separates verified implementation from incomplete acceptance and decisions. A module, endpoint, or passing unit test alone does not prove an end-to-end user capability is complete.

## Verified merged foundations

- Technical-analysis stack includes deterministic indicators and price-action evidence, with API/dashboard integration (PR #364 and follow-on integration).
- News/event ingestion foundations include normalized metadata, SQLite persistence, provider-neutral orchestration, authenticated API, and operator-configured RSS/Atom feeds.
- Crash Radar exposes explainable components and per-symbol snapshot-date evidence (merged PR #387), while the existing 50/40/10 heuristic remains unvalidated as a crash probability.
- Operator subscription administration includes immutable versioned plans, guarded provisioning, audited transitions, and subscription event history (PR #407).
- Owner dashboard subscription controls are merged (PR #408).
- Telegram dispatch has explicit terminal suppression when no linked recipients exist (PR #409).
- Session opportunity ledger/report domain, report builder, and SQLite snapshot store exist. This does not by itself prove automatic end-of-session scheduling or subscriber delivery is wired end-to-end.

## Non-M61 work remaining

### P0 — Verify main after the documentation reconciliation merge

- [ ] Confirm the latest `main` CI run for merge commit `1861931814ddd781ca1284bd48c8dc8e7629202a` completes successfully across unit tests, integration tests, frontend tests, dependency audit, and container build.
- [ ] If any check fails, inspect the failing job and fix the root cause in a scoped PR; do not infer a green state from the earlier PR branch run.

### P1 — Opportunity lifecycle and Telegram delivery acceptance

- [ ] Trace the full path from analysis/evidence generation through publication, durable outbox, recipient/entitlement resolution, delivery, retries, duplicate suppression, and operator-visible outcome.
- [ ] Add or verify contract tests for new publication, revised version, invalidation, expiry, duplicate dispatch, retry exhaustion/recovery, no linked recipients, and entitlement changes.
- [ ] Confirm that invalidation/re-evaluation and per-user opportunity history are actually wired end-to-end; event enum values or individual services alone are insufficient evidence.
- [ ] Preserve original published rationale and price levels; keep hypothetical opportunity outcomes separate from actual portfolio P&L.
- [ ] No change to scoring thresholds or automatic recommendation policy without a separately accepted decision.

### P1 — Session reports

- [ ] Trace the session report snapshot API, report store, owner dashboard, scheduler, and Telegram delivery composition.
- [ ] Verify a repeatable end-of-session trigger using the Cairo exchange timezone, with idempotency, rerun/correction semantics, and operational failure visibility.
- [ ] Verify report contents include session summary, opportunities published during the session, status changes/invalidation, resolved versus unresolved outcomes, and clear data/methodology limitations.
- [ ] Add end-to-end tests for scheduled generation, duplicate scheduler invocation, missing data, delayed signals, timezone/session boundaries, and delivery failure.
- [ ] Do not label this feature complete until scheduling and delivery are proven by integration tests or workflow evidence.

### P1 — Subscription and commercial boundary

- [ ] Keep current operator-managed activation explicitly manual until payment policy is approved.
- [ ] Before gateway implementation, record owner decisions for pricing/tiers, payment provider, checkout, trusted webhook verification, idempotency, refunds/chargebacks, cancellation, and reconciliation.
- [ ] Verify server-side entitlement enforcement across API and Telegram, including expired/pending/cancelled subscriptions and replayed or out-of-order provider events.
- [ ] Do not treat `payment_provider` or `payment_reference` metadata as verified payment.

### P1 — Crash Radar policy gate (DEC-133)

Owner decisions required before changing score semantics:
- Universe ownership (fixed EGX30, broad EGX universe, or operator-configured universe).
- Freshness threshold and handling of unknown dates.
- Minimum coverage and whether to suppress the composite score when evidence is insufficient.
- Daily history persistence, retention, and correction policy.
- Notification thresholds/hysteresis, audience, rate limits, and recovery/suppression behavior.

Until accepted, preserve the existing 50/40/10 heuristic, show coverage/freshness and limitations, and do not call it a crash probability or trading signal.

### P1 — News/source policy gate

- [ ] Review a specific official EGX/company-disclosure source, its terms/licensing, attribution, retention, rate limits, timestamp quality, and historical coverage.
- [ ] Configure only sources whose terms and operational access have been accepted; retain provenance and point-in-time timestamps.
- [ ] Test duplicate/corrected/late/undated events and symbol-matching uncertainty.
- [ ] Keep news interpretation separate from signal ranking and Telegram alerts until a versioned scoring/alert decision and tests are approved.

### P2 — Repository hygiene and release readiness

- [ ] Review stale branches by comparing each branch to `main` and any associated PR before deletion. Do not mass-delete branches based on names alone.
- [ ] Keep PR #321 and other M61 work paused; do not merge or close them as “complete” while the owner has explicitly deferred M61.
- [ ] Add a release checklist for environment configuration, migrations/persistence, authentication/authorization, secrets, backups, observability, and rollback.
- [ ] Run a final complete CI and API/UI smoke-test matrix before claiming product completion.

## Acceptance standard

A work item is complete only when:
1. its user-visible behavior and failure states are specified;
2. the implementation respects domain/application/infrastructure boundaries and existing contracts;
3. tests cover normal, edge, invalid, duplicate/retry, and authorization cases where relevant;
4. CI is green on the final commit;
5. docs match the shipped behavior and explicitly identify external dependencies or owner decisions.

This register is not a claim that all listed work is implemented. It is the auditable checklist for closing the remaining non-M61 gaps without silently inventing product policy.
