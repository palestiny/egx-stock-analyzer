# Project Completion Gap Register

**Status:** Active non-M61 engineering/acceptance register  
**Updated:** 2026-10-31  
**Baseline:** `main` at `c0448e796328c805ccc544d0e7f72083da5ce3e4` (PR #430); PR #429 main CI run #41191307763 passed all five jobs, and PR #430 branch CI run #41191550843 passed all five jobs. Verify the post-#430 main workflow before treating the latest main commit as fully CI-verified.  
**M61:** Explicitly paused by owner request; do not advance M61/backtesting work until the owner resumes it.  
**EGXBot direction:** Owner-approved dual strategy engines (intraday + swing), delayed/daily data, new-opportunity and material-change alerts, manual execution only. See `docs/EGXBOT-DUAL-ENGINE-DESIGN-GATE.md`.

This register separates verified implementation from incomplete acceptance and decisions. A module, endpoint, or passing unit test alone does not prove an end-to-end user capability is complete. Owner policy baseline DEC-135 was accepted on 2026-10-31; policy approval does not mark the related engineering acceptance items complete.

## Verified merged foundations

- Technical-analysis stack includes deterministic indicators and price-action evidence, with API/dashboard integration (PR #364 and follow-on integration).
- News/event ingestion foundations include normalized metadata, SQLite persistence, provider-neutral orchestration, authenticated API, and operator-configured RSS/Atom feeds.
- Crash Radar exposes explainable components and per-symbol snapshot-date evidence (merged PR #387), while the existing 50/40/10 heuristic remains unvalidated as a crash probability.
- Operator subscription administration includes immutable versioned plans, guarded provisioning, audited transitions, and subscription event history (PR #407).
- Owner dashboard subscription controls are merged (PR #408).
- Telegram dispatch has explicit terminal suppression when no linked recipients exist (PR #409).
- Session opportunity ledger/report domain, report builder, SQLite snapshot store, and authenticated snapshot API exist. PR #414 prevents signals generated after a report's `generated_at` cutoff from leaking into a historical snapshot and validates signal data timestamp timezone-awareness. Automatic end-of-session scheduling and subscriber delivery remain unproven end-to-end.
- PR #416 adds a passing contract test for publication through durable outbox to an entitled linked Telegram recipient with idempotent replay. This proves that tested path only, not all lifecycle states or production scheduling.
- `docs/RELEASE-READINESS-CHECKLIST.md` exists as a checklist template, not a declaration of production readiness.
- EGXBot approved design constraints and implementation gates are recorded in `docs/EGXBOT-DUAL-ENGINE-DESIGN-GATE.md`.

## Non-M61 work remaining

### P0 — Verify latest merged main CI

- [x] PR #422 merge commit `fa5d16a9b8a47e3cdcb9467d1e31ffd4ee6bed64` passed all five main-branch jobs in run #41185546490 (unit, integration, frontend, dependency audit, container build).
- [x] PR #430 merged the Telegram delivery operator runbook; its exact-head CI run #41191550843 passed all five jobs. Post-merge main CI for `c0448e796328c805ccc544d0e7f72083da5ce3e4` remains to be verified.

### P1 — EGXBot market-data readiness and dual engines (stale/invalid-data safety policy accepted in DEC-135)

- [ ] Inventory actual Yahoo Finance adapter behavior, EGX symbol coverage, supported bar intervals, timestamps, data delay, corrections, rate limits and licensing/terms.
- [ ] Implement and test an explicit data freshness/provenance gate; suppress or clearly mark stale/insufficient data rather than producing a current-session actionable claim.
- [ ] Introduce separate, versioned intraday and swing strategy boundaries without silently changing existing scoring or trade rules.
- [ ] Keep intraday strategy output suppressed or explicitly observational until suitable intraday data freshness/granularity is verified; daily bars must not be presented as live intraday evidence.
- [ ] Define relative volume/traded-value evidence from available bars; do not claim order-book imbalance or smart-money activity without suitable underlying data.
- [ ] Record rationale, data timestamp, strategy version, entry conditions, invalidation, targets and expiry on every published opportunity.

### P1 — Opportunity lifecycle and Telegram delivery acceptance (owner policy accepted in DEC-135)

- [x] Verify publication -> durable outbox -> entitled linked recipient -> Telegram transport with idempotent replay via PR #416 contract test.
- [ ] Add/verify contract tests for revised version, invalidation, expiry, target/stop observations, duplicate dispatch, transient failure/retry/recovery, retry exhaustion, no linked recipients and entitlement changes.
- [ ] Confirm per-user opportunity history and end-to-end re-evaluation are wired; event enum values or individual services alone are insufficient evidence.
- [ ] Preserve original published rationale and price levels; keep hypothetical opportunity outcomes separate from actual portfolio P&L.
- [ ] No change to scoring thresholds or automatic recommendation policy without a separately accepted decision.

### P1 — Session reports (owner policy accepted in DEC-135)

- [x] Historical snapshot builder excludes signals whose `generated_at` or `data_timestamp` is after the requested report cutoff; timezone-aware timestamp validation is covered by tests (PR #414).
- [ ] Trace session report API, store, owner dashboard, scheduler and Telegram delivery composition.
- [ ] Verify a durable end-of-session trigger using Cairo exchange timezone, with idempotency, rerun/correction semantics and operational failure visibility.
- [ ] Verify report contents include session summary, opportunities published during the session, status changes/invalidation, resolved versus unresolved outcomes, source freshness and methodology limitations.
- [ ] Add end-to-end tests for scheduled generation, duplicate scheduler invocation, missing data, delayed signals, timezone/session boundaries and delivery failure.
- [ ] Until scheduling and delivery are proven by integration tests or workflow evidence, describe reports as API/manual, not automatic.

### P1 — Subscription and commercial boundary (manual entitlement policy accepted in DEC-135; billing deferred)

- [ ] Keep operator-managed activation manual and auditable; do not treat manual provisioning or payment metadata as proof of payment.
- [ ] Before gateway implementation, record owner decisions for pricing/tiers, payment provider, checkout, trusted webhook verification, idempotency, refunds/chargebacks, cancellation and reconciliation.
- [ ] Verify server-side entitlement enforcement across API and Telegram, including expired/pending/cancelled subscriptions and replayed or out-of-order provider events.
- [ ] Do not treat `payment_provider` or `payment_reference` metadata as verified payment.

### P1 — Crash Radar policy gate (DEC-133 / DEC-135)

[x] Owner policy baseline accepted in DEC-135. Engineering implementation and verification remain open:

- [ ] Implement configurable monitored universe and completed-session freshness evaluation.
- [ ] Mark stale/missing/insufficient coverage explicitly; preserve explainability and avoid automatic alerts.

DEC-135 resolves the owner-policy baseline. Preserve the existing 50/40/10 heuristic; do not change score semantics, enable alerts, or call the score a crash probability or trading signal. The detailed implementation and evidence tasks remain open.

### P1 — News/source policy gate (official-source-only policy accepted in DEC-135; source-specific terms verification remains open)

- [ ] Review a specific official EGX/company-disclosure source, its terms/licensing, attribution, retention, rate limits, timestamp quality and historical coverage.
- [ ] Configure only sources whose terms and operational access have been accepted; retain provenance and point-in-time timestamps.
- [ ] Test duplicate/corrected/late/undated events and symbol-matching uncertainty.
- [ ] Keep news interpretation separate from signal ranking and Telegram alerts until a versioned scoring/alert decision and tests are approved.

### P2 — Repository hygiene and release readiness

- [ ] Review stale branches by comparing each branch to `main` and any associated PR before deletion. Do not mass-delete branches based on names alone.
- [ ] Keep PR #321 and other M61 work paused; do not merge or close them as “complete” while the owner has explicitly deferred M61.
- [x] Add a release checklist template for environment configuration, persistence/migrations, authentication/authorization, secrets, backups, observability and rollback; production readiness still requires evidence for every applicable item.
- [ ] Run a final complete CI and API/UI smoke-test matrix before claiming product completion.

## Acceptance standard

A work item is complete only when:
1. its user-visible behavior and failure states are specified;
2. the implementation respects domain/application/infrastructure boundaries and existing contracts;
3. tests cover normal, edge, invalid, duplicate/retry and authorization cases where relevant;
4. CI is green on the final commit;
5. docs match shipped behavior and explicitly identify external dependencies or owner decisions.

This register is not a claim that all listed work is implemented. It is the auditable checklist for closing remaining non-M61 gaps without silently inventing product policy.


## Owner policy decision update — 2026-10-31 (DEC-135)

The owner accepted the conservative non-M61 product/operational baseline:
- configurable Crash Radar universe, completed-session freshness and visible coverage limitations, with no automatic alerts;
- immutable opportunity versions, completed-session re-evaluation, explicit invalidation/expiry, durable auditable Telegram lifecycle, and manual trading only;
- Cairo-time session reports with idempotent generation and traceable corrections without duplicate distribution;
- manual audited subscription entitlements; live billing/pricing/refunds remain deferred;
- official news disclosures only after source access/reuse terms are verified;
- suppression of actionable output when data is stale, missing, future-dated, or invalid, with explicit reason and coverage.

This acceptance closes the owner-policy decision gate, not the implementation checklist. All engineering, integration, source-rights, and operational verification items above remain open until evidenced. M61 remains paused and PR #321 remains open Draft and untouched.


### Telegram concurrency and ambiguous outcomes — DEC-136 (implementation merged; retry policy open)

- [x] Owner decision: ambiguous outcome after send initiation becomes `DELIVERY_UNKNOWN`; do not automatically resend; require operator reconciliation.
- [x] PR #428: atomic per-recipient SQLite claim/lease, opaque claim-token fencing, safe expired-CLAIMED recovery, and expired-SENDING transition to `DELIVERY_UNKNOWN`.
- [x] PR #428: distinguish definite Telegram rejection from ambiguous timeout/connection/server outcomes; preserve unknown outcomes without automatic resend.
- [x] PR #429: operator-only unresolved-delivery listing, audited manual reconciliation, and terminal `NOT_DELIVERED` handling.
- [x] PR #430: operator runbook with authenticated API examples, evidence requirements, and escalation guidance.
- [x] Owner decision: derive lease duration at runtime as 2 × the effective configured Telegram transport timeout.
- [ ] Define definite-failure retry schedule, attempt budget, and exhaustion behavior; these remain open. `FAILED` is not automatically retried.
- [x] PR #428 tests cover concurrent claims, stale-token fencing, lease recovery, ambiguous transport outcomes, migration, partial recipient safety, and active-claim protection. PR #429 tests cover audited reconciliation and no-resend terminal resolution.

Implementation is merged, but this is not exactly-once delivery. `DELIVERY_UNKNOWN` remains manual-only. Definite-failure retry policy is still unapproved and must not be invented. PR #428 main CI passed in run #41189366403; PR #429 main CI passed all five jobs in run #41191307763.
