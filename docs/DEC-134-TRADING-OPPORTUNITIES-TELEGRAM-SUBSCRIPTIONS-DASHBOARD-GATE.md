# DEC-134 — Trading Opportunities, Telegram Distribution, Session Reports, Subscriptions, and Owner Dashboard

**Status:** Partially implemented on `main`; operator subscription API, owner-dashboard controls, and terminal no-recipient Telegram dispatch state are merged; remaining end-to-end acceptance and product/policy decisions are still open  
**Date:** 2026-10-26  
**Repository:** palestiny/egx-stock-analyzer  
**Current execution priority:** Non-M61 product and engineering gaps; M61 paused by owner request on 2026-10-28

## 1. Purpose

Define the product direction without silently changing current analytical, alert-delivery, or roadmap behavior. The goal is to evolve EGX Stock Analyzer into an explainable EGX opportunity-monitoring platform with a Telegram bot, post-session reports, subscription plans, and an owner dashboard.

This is a design proposal, not implementation approval. M61 is paused by explicit owner request as of 2026-10-28; no live historical performance, future profit, or brokerage execution is implied.

## 2. Verified Existing Foundation and Limits

Repository review confirms:
- Technical/fundamental analysis, scoring, stock quality, entry quality, opportunity classification, explainable scanners, market breadth/stress analysis, and a pre-breakout momentum/volume watchlist already exist.
- The application uses FastAPI + React/Vite and a modular-monolith architecture.
- Alert candidates, notification-provider abstraction, durable alert-delivery records, automatic alert delivery, scheduled analysis/delivery composition, and a Telegram provider already exist.
- The Telegram provider currently sends a formatted alert candidate to one configured chat ID. This is not yet a subscriber-aware opportunity-publishing product.
- The domain already defines AlertEvent types SIGNAL_TRIGGERED and SIGNAL_INVALIDATED, but that alone does not prove an end-to-end opportunity lifecycle, evidence re-evaluation, invalidation delivery, or subscription entitlements are complete.
- Telegram configuration and explicit live-send verification are documented in docs/TELEGRAM_CONNECTION_VERIFICATION.md.
- Strategy simulation and backtest metrics exist, but the real historical dataset and evidence-backed strategy validation remain unaccepted.
- PR #343 (Crash Radar analysis-date evidence metadata) is merged; it is not an outstanding implementation PR. The reconciled Crash Radar v2 policy gate is tracked in `docs/DEC-133-CRASH-RADAR-V2-DESIGN-GATE.md`.

Reuse existing contracts when suitable; do not create a parallel alert system or infer product completeness from a class name.

## 2.1 Implementation status reconciled — 2026-10-28

Verified merged increments:

- **PR #407** merged the operator-only subscription lifecycle API, application service boundary, immutable versioned plans, provisioning guards, audited state transitions, and subscription-event history.
- **PR #408** merged the owner-dashboard UI and API client integration for manual subscription administration.
- **PR #409** merged explicit terminal suppression for Telegram alert events dispatched when no linked recipients exist, including an operator-visible count. This is not equivalent to delivery and is not a payment or entitlement feature.
- The documentation reconciliation PR #412 passed all five reported CI jobs (unit tests, integration tests, dependency audit, container build, and frontend tests) before merge. A new main-branch CI run for merge commit `1861931814ddd781ca1284bd48c8dc8e7629202a` was in progress at the time of this update; verify that run separately before treating the latest main revision as fully green.

Remaining gaps are not all code-only:
1. Subscription pricing, payment provider, checkout/webhook trust boundary, refunds, and reconciliation require an explicit product/payment decision before gateway implementation.
2. Opportunity lifecycle semantics (publication, versioning, re-evaluation, invalidation, expiry, and user-facing history) need an accepted contract before changing signal scoring or automatic publication.
3. Automatic session finalization/scheduling and Telegram session-report distribution are not established as complete by the merged manual snapshot endpoints.
4. Subscriber delivery needs end-to-end tests for entitlement changes, duplicate events, retries, no-recipient suppression, and operational recovery before production acceptance.

No brokerage execution, paid billing, strategy profitability, or guaranteed trade outcomes are implied by the merged code.

## 3. Product Principles

1. Evidence before language: each opportunity states its observations, timeframe, data freshness, and rules.
2. A published setup is not proof of an executed trade.
3. Published opportunity versions and their original rationale are immutable and auditable.
4. Invalidation is a first-class event, never a silent edit.
5. Liquidity sweeps, order blocks, and inducement are labeled as confirmed only when suitable source data supports that claim. From OHLCV candles alone, label them as price-action inferences/proxies.
6. Stale, missing, or contradictory evidence is visible and may block publication under an owner-approved policy.
7. Retries and duplicate analysis runs must not duplicate subscriber messages.
8. Entitlements are enforced server-side across API and Telegram.
9. Explainable, versioned rules take precedence over opaque ranking.
10. Backtest metrics, hypothetical opportunity outcomes, and actual portfolio P&L remain separate.
11. High-impact administrative and policy actions are audited.

## 4. Opportunity Evidence and Lifecycle

### 4.1 Evidence families

Reuse current analysis and scanner outputs. Add a normalized, versioned evidence record only where existing contracts do not cover the requirement.

Potential evidence families:
- Market structure: trend regime, swing highs/lows, support/resistance, breakout/retest.
- Candles: rejection, engulfing, pin bar, inside bar, close strength, range expansion, volume-confirmed patterns.
- Volume/momentum: relative volume, momentum changes, volatility expansion/contraction, pre-breakout conditions.
- Liquidity/price action: equal highs/lows, sweep-like wick/close behavior, failed breakout, reclaim/rejection, inducement hypothesis.
- Risk context: volatility, drawdown, market breadth/stress, sector regime, turnover/liquidity constraints, corporate/event risk.
- Later optional sources: corporate actions, official disclosures, reliable intraday/order-book feeds.

Each evaluation should retain symbol, timeframe, observation/session timestamp, source/data version, rule version, evidence references, freshness/completeness, trigger state, explanation, and uncertainty.

### 4.2 Reuse the Existing Signal Model

Do not create a parallel TradingOpportunity aggregate without evidence that the existing signal domain cannot support the requirement. Repository review confirmed these existing components:

- `app/domain/signals/model.py` defines `Signal` with symbol, direction, status, generation/data timestamps, timeframe, entry zone, invalidation, targets, confidence/risk scores, evidence, and strategy ID/version.
- `app/application/signals/generate_signal.py` generates breakout/trend signals from saved analysis snapshots.
- `app/application/signals/lifecycle_orchestrator.py` coordinates deterministic lifecycle transitions, alert events, history, and terminal outcome recording.
- `app/application/signals/store.py` defines `SignalHistoryStore`, currently with an in-memory implementation.
- `app/application/signals/track_record.py` defines `TrackRecordStore`, currently with an in-memory implementation.
- `app/domain/signals/outcome.py` and `app/application/signals/performance.py` already represent terminal outcomes and descriptive track-record metrics.

The first missing foundation is durable history/outcome persistence and reliable event delivery, not a second signal entity. PR #345 was closed before merge after discovering the overlap. PR #346 now proposes SQLite implementations for the existing signal-history and outcome contracts, a durable alert-event outbox, and runtime composition of these stores with the existing lifecycle orchestrator. It also adds evidence-change invalidation for changes represented in the current Signal fields. It remains a draft and is not yet accepted or merged. Raw-data revision fingerprints and atomic transactions spanning lifecycle history plus outbox are still gaps; do not claim end-to-end delivery reliability until those are addressed.

Implementation follow-up status (open, unmerged PRs):
- PR #346: durable signal history/outcomes and outbox; all five reported CI jobs passed on the latest reviewed head.
- PR #348: explicit recipient-targeted Telegram provider transport; all five reported CI jobs passed.
- PR #349: short-lived single-use Telegram account linking with hashed challenges, durable chat binding and audit events; all five reported CI jobs passed on its latest reviewed head.
- PR #356: point-in-time session opportunity ledger over the existing signal history and outcomes; all five reported CI jobs passed on the latest reviewed head.
These are staged foundations, not proof of end-to-end subscriber publishing. Subscription entitlements, complete report persistence/finalization, payments, and owner dashboard remain outstanding.

Extend the existing model only where gaps are verified. Likely additions include:
- explicit published-version identity and immutable publication snapshots;
- an explicit entry-condition state distinct from terminal outcome;
- expected holding horizon as an estimate/range;
- evidence/data-quality state and the exact evidence version used for each evaluation;
- links to delivery/report events;
- a separate, explicit actual-execution record if the owner or subscriber reports a real trade.

**Compatibility warning:** current `SignalStatus.TRIGGERED` means the current lifecycle observed a target hit; it does not mean the entry condition triggered. Do not silently reinterpret this existing status. Introduce a clear entry-state/outcome distinction and preserve existing API behavior until a migration is designed and tested.

Keep separate: setup published; entry condition observed; market-price proxy met; actual user trade confirmed. A candle touching a price does not prove an order filled. If OHLCV cannot establish whether a stop or target happened first inside one candle, record ambiguity or use an explicitly approved conservative convention.

### 4.3 Lifecycle and Versioning

The extended product lifecycle must be mapped onto the existing `Signal` and `SignalLifecycleOrchestrator`, with explicit compatibility rules for the existing status enum.

Proposed user-facing lifecycle concepts:
- DRAFT / WATCHING: setup is being evaluated and is not yet a confirmed entry.
- ACTIVE: the setup has been published and its trigger condition has not yet been observed.
- ENTRY_TRIGGERED: the declared entry rule was met according to the stated timeframe and observation convention; this does not prove a user order filled.
- IN_PROGRESS: the market-based tracking convention considers the setup entered and unresolved.
- TARGET_PARTIAL / TARGET_REACHED: target progress under a defined evaluation rule.
- INVALIDATED: supporting evidence or a declared invalidation condition contradicts the setup.
- STOPPED_OUT: a defined risk boundary is crossed under the accepted convention.
- EXPIRED: the time horizon ends without resolution.
- CANCELLED: an authorized operator withdraws it.
- DATA_UNRELIABLE: data quality prevents a trustworthy evaluation; this is a suspension, not automatically market invalidation.

These are proposed product concepts, not permission to rename or change the current `SignalStatus` values in-place. A published version and every lifecycle event must preserve timestamp, reason, source/data version, rule version, and actor/source. Material amendments create a linked new publication version; no silent movement of stops or targets.

### 4.4 Re-evaluation and invalidation

Re-evaluate when new observations arrive, candles are corrected, corporate actions/symbol mappings change, supporting evidence changes, entry/target/stop/expiry conditions may have occurred, or source freshness/completeness fails policy.

Distinguish setup invalidation, risk boundary reached, data-quality suspension, owner-approved amendment, and expiry. Preserve the originally published rationale. If available data cannot prove intrabar sequence, report uncertainty rather than asserting exact order.

## 5. Telegram Product

### 5.1 Message types

1. New opportunity: symbol, direction, timeframe, entry zone/trigger, invalidation, targets, expected horizon, risk/reward assumptions, evidence summary, timestamp, data-quality state, methodology version, disclaimer.
2. Entry-condition update with observation and explicit note that actual execution is unconfirmed.
3. Target/stop/expiry update under the declared evaluation convention.
4. Invalidation/amendment with reason, old/new version, and reference to original post.
5. Optional pre-session watchlist, subject to data readiness.
6. Post-session market report and opportunity ledger.
7. Data-quality/service notices for stale feeds, missing symbols, suspensions, or provider conflicts.
8. Subscription activation, expiry, payment status, and entitlement-change notices.

### 5.2 Delivery design

- Reuse NotificationProvider, DeliverAlert, and durable delivery concepts where they fit.
- Add subscriber/recipient routing; one global chat ID cannot serve as the paying-customer model.
- Link Telegram identity only after a deliberate start/link flow and verification.
- Use a durable outbox or equivalent so a persisted state transition and pending message cannot be lost between separate steps.
- Idempotency key identifies event + opportunity version + recipient + channel.
- Track pending, sent/accepted, retryable/permanent failure, and suppressed/entitlement-denied outcomes. Telegram accepting a request does not prove it was read.
- Respect rate limits, bulk-send controls, and materiality thresholds; do not publish every internal recalculation.
- Keep bot tokens out of source, logs, URLs shown to users, errors, and audit records.
- Candidate commands: /start, /help, /status, /plans, /subscribe, /watchlist, /mute and owner-only private portfolio/admin commands. Every command must enforce identity and entitlements server-side.
- Separate private owner/admin chat from subscriber delivery. Never expose owner portfolio or subscriber data in a public group.

Users should be able to configure permitted topics and frequency, such as new opportunities, material updates/invalidation, session reports, and selected symbols. Never promise real-time updates if source data or scheduling is delayed.

## 6. Post-Session Report

Generate after the EGX session is closed and the accepted data-finalization condition is met. The trigger must use a verified exchange calendar, holidays, and feed-arrival behavior rather than assuming a fixed daily time.

### 6.1 Market-wide summary
- session date and data-finalization timestamp;
- benchmark/index move and available breadth/advance-decline statistics;
- sector/stock movers, turnover/volume context, unusual activity where sourced;
- market regime and Crash Radar state with evidence date/coverage;
- missing/stale symbols, suspensions, provider conflicts;
- comparison with the previous valid session where comparable.

### 6.2 Detailed analysis
- watchlist changes and notable structures;
- support/resistance/Fibonacci only when based on identified, validated swing points;
- breakout/retest and candle/volume evidence;
- risk context and uncertainty;
- clear distinction between observed facts and model interpretation.

### 6.3 Complete opportunity ledger — mandatory
For every opportunity in the defined reporting cohort:
- original publication time/version and original entry, invalidation, and targets;
- current status and entry-condition observations under the declared convention;
- targets reached/not reached, stop/invalidation, expiry, or unresolved status;
- favorable/adverse excursion only when data supports it;
- hypothetical result after declared costs/slippage, separated from actual portfolio P&L;
- amendment/invalidation reasons, intrabar ambiguity, and data-quality exceptions;
- cohort statistics with sample size, unresolved cases, and exclusions.

Never remove losing, invalidated, expired, or unresolved opportunities from the record. Do not report a success rate without a defined denominator, evaluation window, and treatment of unresolved cases.

Persist a versioned report reference, dataset/snapshot version, methodology version, generation timestamp, and delivery state. Re-running fixed finalized input should be deterministic or explicitly create a new version. Report-generation failure must not alter opportunity states.

## 7. Subscriptions and Monetization

### 7.1 Capabilities
- subscriber account and verified Telegram association;
- versioned plan and entitlements;
- lifecycle states for pending, active, past-due, grace period if offered, expired, cancelled, refunded/chargeback where applicable;
- payment intent/order, provider transaction reference, reconciliation events, append-only billing audit;
- shared entitlement evaluator for web API and Telegram;
- renewal/expiry notices and access revocation;
- audited complimentary access grants with reason and expiry;
- cancellation/refund/support workflow;
- privacy, export, and deletion handling while preserving legally required accounting records.

### 7.2 Payment boundary

Keep a provider-neutral payment interface. Do not hard-code a gateway before the owner selects launch countries/currencies and current fees, settlement, recurring-payment support, refund/webhook behavior, and legal availability are verified.

A payment is confirmed only by a trusted server-to-server event or verified reconciliation—not a screenshot or client redirect. Webhooks must authenticate, be idempotent, and handle replay/out-of-order delivery.

### 7.3 Candidate tiers — not approved

- Free: delayed/limited recap and a limited sample/watchlist.
- Plus: full opportunity stream and material lifecycle updates within declared data limits.
- Pro: richer evidence, strategy/risk views, personalized watchlists, detailed session reports.
- Owner/Admin: private operational controls, not a customer-facing tier.

These are packaging hypotheses, not approved prices or entitlements. Validate willingness to pay and data redistribution licensing before selling real-time feeds or reports.

## 8. Owner Dashboard

### Overview
Market/session status, latest finalized data time and coverage, source health, new/active/invalidated/expired opportunities, last report status, Telegram delivery health, subscribers, renewals, payment exceptions, and recent admin actions.

### Opportunities
Search/filter by symbol, strategy, status, timeframe, and date; view evidence timeline and versions; entry/target/invalidation history; audited pause/cancel/republish with mandatory reason; compare original terms with amendments.

### Strategy and performance lab
Hypothetical outcomes, unresolved cases, win/loss/flat counts, average win/loss, expectancy, profit factor, trade-sequence drawdown, fees/slippage assumptions, and breakdown by strategy/timeframe/regime/cohort. Show sample size, missingness, and uncertainty. Out-of-sample/walk-forward views only when data supports them. Do not label a small sample as predictive proof.

### Personal portfolio
Manual positions, quantities, average cost, fees, cash, dividends, deposits/withdrawals, and corporate actions; realized/unrealized P&L, concentration/exposure, benchmark comparison, drawdown, corrections, and reconciliation history. Keep actual holdings separate from paper portfolio and hypothetical opportunity ledger. No broker execution/account linking is assumed.

### Subscribers and billing
Plan mix, active/expired/past-due counts, renewals, churn, refunds, payment reconciliation exceptions, audited entitlement grants/revokes, support notes, Telegram linking and delivery status. Avoid unnecessary payment-sensitive data.

### Operations and governance
Provider freshness/coverage, ingestion errors, scheduled runs, session-report jobs, outbox/retry/replay, per-recipient delivery, audit logs, feature flags, methodology versions, incident history, backup/restore verification, retention and access-review status.

## 9. Additional Recommended Features

1. Opportunity replay/evidence timeline: reconstruct exactly what the system knew when each message was published.
2. Strategy/rule registry with version, tests, owner approval, and rollout history.
3. Paper portfolio/shadow ledger using a fixed, explicit execution convention.
4. Risk-budget/position-sizing calculator as a scenario, not a guarantee.
5. Regime analytics to inspect results across trend/range/volatility/stress states without silently tuning rules.
6. Corporate-action/event awareness for splits, dividends, suspensions, disclosures, and symbol mapping.
7. Personalized watchlists and filters within plan entitlements.
8. Separate setup quality from data confidence; do not hide poor evidence behind one score.
9. Digest/quiet hours, topic opt-outs, materiality thresholds, and duplicate suppression.
10. Transparent correction notices when revised source data changes reports or opportunity status.
11. Subscriber activation/retention/churn analytics with data minimization.
12. Reliability: outbox replay, dead-letter review, backup/restore drills, monitoring, and incident playbooks.
13. Public methodology/performance disclosure with cohort definitions, sample sizes, exclusions, costs, and limitations.
14. Additional channels (web push/email/mobile) only after Telegram lifecycle and entitlements are reliable.

## 10. Architecture Direction

Preserve the modular monolith unless measured load or operations justify a different deployment model.

Logical flow:
- Market data + provenance → analysis/signal evaluation → opportunity lifecycle/re-evaluation → durable domain event/outbox → Telegram delivery policy + entitlement check → per-recipient delivery.
- Finalized session + persisted opportunity history → report generator → versioned report → entitled delivery.
- Identity + plan + subscription + payment reconciliation → shared entitlement evaluator → API and Telegram authorization.

The owner dashboard reads application-facing query/reporting capabilities; it does not implement market rules. Important state transitions and outbox records need atomic persistence. Provider calls occur outside database transactions. Delivery retries must not duplicate events. Secrets stay in deployment secret configuration.

## 11. Proposed Delivery Sequence

M61 is paused by owner request as of 2026-10-28. This proposal does not authorize any M61 data acquisition or performance claim.

### Stage 0 — Design and acceptance
Resolve lifecycle and price evaluation semantics, timeframes/data needs for liquidity claims, publication/invalidation policy, entitlements, and report acceptance. Inspect existing alert, Telegram, audit, auth, and dashboard contracts before adding abstractions.

### Stage 1 — Evidence trust and opportunity ledger
Keep M61 data acquisition paused. Audit and complete the existing signal/outbox/lifecycle foundations first; add or change opportunity versions and lifecycle events only after compatibility semantics are accepted. Implement deterministic re-evaluation/invalidation and replay tests using fixed fixtures. No paid performance claims before M61 evidence acceptance.

### Stage 2 — Telegram opportunity delivery
Link users/recipients, add durable outbox, per-recipient idempotency, delivery states, safe retry, and new-opportunity/material-update/invalidation messages. Use fake-transport end-to-end tests; live send remains explicit opt-in.

### Stage 3 — Session reports
Define exchange calendar and data-finalization rule; generate market-wide and per-opportunity sections; persist report versions/delivery outcomes; test stale, missing, corrected, and unresolved cases.

### Stage 4 — Owner dashboard and personal portfolio
Build overview, opportunity lifecycle, data health, report history, delivery and audit views. Keep real portfolio and hypothetical ledger separate. Add performance analytics only after definitions/data are accepted.

### Stage 5 — Subscriptions and payment reconciliation
Build identity/linking and server-side entitlements first; select a gateway only after owner decision and verification. Add authenticated/idempotent webhooks, renewals, cancellations, refunds, reconciliation, and audit. Test-mode and reconciliation reports precede live payments.

### Stage 6 — Advanced analytics and growth
Add regime analytics, strategy registry, personalized watchlists, public methodology/performance disclosures, and other channels when evidence, licensing, operating cost, and user value justify them.

## 12. Critical Acceptance Tests

- Every opportunity version is immutable and each lifecycle transition is audited.
- Corrected inputs can change status and create exactly one corresponding event per version/recipient/channel.
- Missing/stale data cannot silently appear fresh.
- Actual trade execution is distinguished from market-price proxy.
- Ambiguous intrabar stop/target ordering follows an approved conservative/ambiguous rule.
- Replaying identical input is deterministic and does not duplicate messages.
- Telegram timeout/retry, rate limits, blocked recipients, expired entitlements, and process restart are tested.
- Payment webhook replay cannot activate/extend a subscription twice.
- A client-side redirect cannot grant premium access.
- Expired/unauthorized users cannot access premium API data or Telegram messages.
- Session reports include losing, invalidated, expired, unresolved, and data-suspended opportunities in the defined cohort.
- Reports are deterministic for fixed finalized data and methodology.
- Actual portfolio P&L and simulated results are never combined misleadingly.
- CI fixtures are deterministic; live provider tests are separately marked external.
- No profitability or real-time claim is published without accepted data, validation, and redistribution rights.

## 13. Owner Decisions Required

1. **M61 priority — RESOLVED 2026-10-28:** owner explicitly paused M61 and requested completion of non-M61 gaps first. M61 remains incomplete and its evidence gate is unchanged.
2. **Initial universe:** EGX30, current configured universe, or a versioned broad EGX universe?
3. **Timeframes:** daily only initially, or daily plus intraday? Intraday liquidity claims require suitable licensed data.
4. **Entry semantics:** publish a watch setup before trigger, wait for candle-close confirmation, or support both as separate states?
5. **Evaluation granularity:** daily OHLCV first, or reliable intraday bars/ticks? This changes claims about exact fills and target/stop ordering.
6. **Direction:** long-only first, or include short scenarios? No brokerage execution is assumed.
7. **Duration:** fixed horizon buckets or strategy-specific estimated bar ranges?
8. **Telegram packaging:** public/free channel plus private subscriber bot, or private bot conversations for all tiers?
9. **Plan limits:** which features, delays, watchlists, and message frequencies belong to Free/Plus/Pro?
10. **Payments:** launch countries/currencies and which gateway should be evaluated?
11. **Portfolio:** manual entries/import first, or broker integration later?
12. **Session report:** one final report after data finalization, or preliminary clearly labeled plus final?
13. **Publishing authority:** fully automatic under approved rules, operator approval for every opportunity, or hybrid?
14. **Performance transparency:** publish full cohort statistics to everyone, or reserve detailed analytics for paid tiers while keeping limitations truthful for all users?

## 14. Proposed Defaults — Not Yet Accepted

- Keep M61 paused until the owner explicitly resumes it; do not use exploratory artifacts as accepted performance evidence.
- Start with daily candles and long-only scenarios.
- Label liquidity sweep/inducement as inferred price-action evidence unless suitable source data verifies liquidity/order-book behavior.
- Support pre-trigger watch setups and confirmed entry events as distinct states.
- Automate invalidation/material amendments under versioned rules with an operator pause/kill switch.
- Use a durable outbox and server-side entitlements.
- Publish final session reports only after data finalization; preliminary reports must be labeled provisional.
- Start personal portfolio with manual entry and separate actual holdings from hypothetical results.
- Do not accept live subscriptions until billing reconciliation, access revocation, support/refund handling, and data redistribution rights are verified.

## 15. Non-Goals

This gate does not authorize changing Crash Radar scoring, changing existing BUY/scanner behavior, brokerage execution, silent stop/target movement, treating a Telegram send as trade execution, choosing a gateway or price, claiming profitability before M61 evidence acceptance, replacing the modular monolith without evidence, or removing M61 from the roadmap without owner decision.

## 16. Decision Record

**Status:** Draft. Decision 1 (M61 pause) is accepted on 2026-10-28; remaining product-policy decisions in Section 13 are still open.  
**Next step:** resolve the remaining universe/timeframe, entry semantics, publishing authority, Telegram packaging, and subscription/payment scope; then split approved work into small design-gated milestones.


## 17. Implementation Status — 2026-10-27

### Merged and verified foundations

- **PR #376 — Telegram opportunity delivery core:** merged. Persists immutable signal snapshots in the alert outbox, dispatches to linked active users with server-side entitlement checks, records per-recipient delivery outcomes, and suppresses duplicate webhook update IDs.
- **PR #378 — owner operations and session-report foundation:** merged. Wires operator-only publication/dispatch endpoints, aggregate owner overview, immutable session report persistence and as-of reads, and retry-safe Telegram webhook replies.
- **PR #381 — owner session-report UI:** merged after all five CI jobs passed. Operators can manually generate or load a saved report snapshot and inspect original entry/invalidation/targets, current evidence/status, and market-proxy outcomes. The UI explicitly labels the result as a manual point-in-time snapshot, not a finalized-session certification or profitability claim.
- **CI remediation issue #341:** closed after the current main passed all five CI jobs with Vite 8.3.5 and Vitest 5.0.5.
- **PR #382 — report snapshot idempotency hardening:** merged after all five CI jobs passed. It canonicalizes snapshot timestamps to UTC and makes duplicate concurrent saves idempotent; latest main CI run #4497 is validating the combined merged state.

### Verified engineering and data status

- Latest main CI run #4497 passed all five jobs after both PRs were merged. The Python suite reported 1,348 passed, 8 deselected, and 90.46% coverage.
- PR #381 latest-head CI run #4491 and PR #382 latest-head CI run #4494 each passed all five jobs.
- Synthetic M61 end-to-end execution is verified, but **real-market Strategy v0 validation remains blocked**. The current no-cost probe classified all ten Yahoo candidates as mutual funds and produced 3,843 OHLCV validation findings; the anonymous EGID history request returned HTTP 401; TradingView-backed extraction is rejected for this automated research use. No permitted real COMI artifact or point-in-time financial snapshots are currently accepted.
- No live Telegram delivery claim is made. Real delivery still requires explicit deployment secrets and an authorized live-send verification.

### Remaining implementation and acceptance gaps

- **Session reports:** automatic scheduling/finalization and Telegram distribution are not implemented. Do not schedule or label a report final until the exchange calendar, data-finalization cutoff, missing/stale-source behavior, and provisional-versus-final policy are accepted.
- **Opportunity lifecycle:** preserve the existing meaning of `SignalStatus.TRIGGERED` (target hit) until a compatibility migration is designed; entry-trigger, published-active, invalidated, suspended, amended, and expired states still need an accepted mapping.
- **Subscriptions and billing:** no approved product tiers/prices or payment gateway. Payment reconciliation, authenticated/idempotent provider webhooks, refunds/chargebacks, support flows, and entitlement revocation remain outstanding. No live subscription activation should depend on a client redirect or screenshot.
- **Strategy validation:** requires an owner-accessible historical CSV/API export whose terms permit local research/storage, preserved raw artifact and provenance, corporate-action semantics, warm-up history, and point-in-time financial snapshots. Do not use synthetic fixtures or rejected sources as performance evidence.
- **Advanced analytics:** Crash Radar v2 and comprehensive technical/news intelligence remain under their separate draft design gates.

The design gate remains **Draft — owner decisions required**. Implementation progress does not accept the remaining decisions in Section 13, authorize paid data, select payment terms, change the explicit M61 pause, or permit profitability claims.


## 18. Status reconciliation — 2026-10-28

The earlier status notes above are historical snapshots. The current GitHub main branch now includes the following additional foundations:
- PR #343: Crash Radar per-symbol analysis-date evidence metadata (merged).
- PR #346: durable SQLite signal history/outcomes and alert outbox (merged).
- PR #348: recipient-targeted Telegram delivery transport (merged).
- PR #356: point-in-time session opportunity ledger (merged).
- PR #376: Telegram opportunity delivery core with immutable snapshots, recipient entitlement checks, per-recipient outcomes, and webhook replay suppression (merged).
- PR #378: owner operations and session-report persistence/read foundations (merged).
- PR #381: owner session-report UI for manually generated or loaded point-in-time snapshots (merged).
- PR #382: UTC canonicalization and idempotent report snapshot persistence (merged).
- PR #384: Clean Architecture dependency-boundary regression tests (merged).

The session-report feature is not end-to-end complete: automated scheduling/finalization and Telegram distribution remain unimplemented until the exchange calendar, data-finalization cutoff, stale/missing-data behavior, and provisional-versus-final policy are accepted. The existing UI report is a manual snapshot, not a certified final session report. Account linking and recipient delivery must be verified against current main behavior rather than inferred from older PR statuses.

M61 is paused by the owner as of 2026-10-28. No historical performance conclusion or source acceptance is implied. Remaining policy decisions in Section 13 stay open; this status refresh does not authorize payment gateway selection, prices, paid entitlements, or unreviewed lifecycle semantics.
