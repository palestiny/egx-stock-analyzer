# EGXBot Dual-Engine Design Gate

**Status:** Owner-approved product direction; implementation design gate, not a claim of completed trading capability.  
**Updated:** 2026-10-28  
**Baseline:** `main` merge commit `2498bd98a848a37d3e2a4c47df9bb603339fe423` (PR #416).  
**Owner-approved constraints:** separate intraday and swing engines; delayed/daily data; alerts for new opportunities and material changes; manual execution only; M61/backtesting remains paused.

## 1. Product objective

EGXBot monitors EGX-listed instruments for explainable momentum, volume/liquidity and price-action evidence; proposes a conditional trade plan; sends Telegram alerts; and tracks the published setup through expiry, invalidation, target/stop observations, and end-of-session reporting.

It is an alerting and decision-support product. It does not place orders, assert a user executed a trade, or present hypothetical signal outcomes as actual portfolio P&L.

## 2. Approved operating modes

### Intraday engine

- Its strategy identity, configuration, signal state, and performance records must be isolated from swing.
- With the currently approved data constraint (delayed or daily), the engine must **not** claim actionable real-time monitoring or promise intraday execution quality.
- Until the data provider, timestamp semantics, delay/freshness limits, intraday bar granularity, session calendar and coverage are verified, intraday output is either suppressed as not eligible or explicitly labelled delayed/observational. Do not infer live prices from daily bars.
- A later move to reliable intraday data requires a separate data-readiness gate; it does not authorize automated brokerage execution.

### Swing engine

- Operates on dated daily or other verified delayed bars only.
- Signals must carry source/data timestamps, timeframe, strategy ID/version, rationale, entry conditions, invalidation, targets, expiry and known data limitations.
- A daily close or daily bar must not be represented as a price currently executable during the session.

### Shared services, separate policy

The engines may share data adapters, deterministic indicator calculations, persistence primitives, alert delivery and reporting. They must not silently share thresholds, stop/target rules, signal state, performance denominators, or strategy versions.

## 3. Repository evidence: reusable foundations

Reviewed on `main`:

- `app/application/analysis/daily_market_analysis.py`: runs analysis over supplied per-symbol price bars and stores results; it is a daily analysis orchestration boundary, not proof of a continuously running intraday scanner.
- `app/application/analysis/rank_market_opportunities.py`: ranks BUY/WATCH opportunities using existing quality scores. Its ranking order is existing behavior and must not be silently reinterpreted as a new momentum/liquidity score.
- `app/application/signals/generate_signal.py`: generates a versioned `breakout-trend` signal from a saved analysis result, including entry zone, invalidation, targets and evidence; it returns no signal when the saved analysis date/current price is unavailable. **Timestamp gap found:** it currently sets both `generated_at` and `data_timestamp` to midnight UTC on `analysis_date`, not the actual provider bar timestamp. Do not present this as the exact market-observation time; preserve this as a P1 correctness gap until provenance is carried through the analysis record.
- `app/application/signals/lifecycle_orchestrator.py`: persists lifecycle transitions, publishes alerts, records terminal outcomes and supports invalidation when supporting evidence changes.
- `app/application/alerts/publish_signal_opportunity.py`, `DispatchSignalAlertOutbox`, SQLite outbox and delivery stores: provide publication/delivery foundations. PR #416 adds a passing contract test for publication to an entitled Telegram recipient with idempotent replay.
- `app/application/reporting/change_detection.py`: detects changes in classification, scores, current price and nearby support/resistance between saved analysis snapshots.
- Session opportunity ledger/report builder, SQLite snapshot store and authenticated API exist; automatic end-of-session scheduling and Telegram report delivery are not yet proven end-to-end.
- `app/infrastructure/runtime.py` composes these capabilities and uses Yahoo Finance adapters. `YahooFinanceHistoryClient.history()` currently requests `interval="1d"`, so the inspected adapter path is daily-bar-only. This does not establish that every required EGX instrument has reliable, licensed, sufficiently fresh intraday volume/order-book data.

## 4. Important gaps before implementation is eligible

1. **Market data contract:** document actual provider, EGX instrument coverage, supported timeframes, volume semantics, currency, timestamps/timezone, delay, corrections, rate limits and licensing. Reject stale, missing, malformed or future-dated observations according to explicit configuration. Carry the actual last eligible `PriceBar.timestamp` through analysis persistence into `Signal.data_timestamp`; do not synthesize it from a date.
2. **Intraday eligibility:** no intraday recommendation mode until data granularity/freshness and Cairo exchange session boundaries are verified. Daily-only data can support a daily/swing view but cannot establish an intraday tape.
3. **Volume/liquidity evidence:** use relative volume and traded value only where comparable historical bars exist. Do not claim order-book imbalance, buyer/seller aggression, smart-money accumulation or distribution without the required trade/order data.
4. **Strategy definitions:** define intraday and swing entry/exit conditions, expiry, confirmation, stop/target behavior and duplicate-signal policy in separate versioned documents. This gate does not invent or change those rules.
5. **Lifecycle completeness:** add coverage for revised versions, invalidation, expiry, stop/target observations, duplicate dispatch, transient failure/retry/recovery, exhausted retries, no recipient, entitlement changes and stale-data suppression.
6. **Session report automation:** prove durable trigger, idempotent reruns/corrections, Cairo timezone, snapshot cutoff, Telegram delivery, and failure visibility. Until then describe reports as API/manual, not automatic.
7. **Operational visibility:** expose last successful data refresh, source timestamp, stale/missing symbol counts, analysis run identity, dispatch/outbox failures, and scheduler health without leaking secrets.
8. **Evidence of quality:** the user has explicitly deferred M61/backtesting. Do not start or merge M61 work. Unit/contract/CI evidence can verify software behavior, but it does not prove trading edge or expected profitability. A future performance-validation phase requires owner authorization.

## 5. Target architecture

- **Data ingestion & freshness gate:** provider adapters -> normalized dated OHLCV bars -> coverage/freshness/provenance validation.
- **Analysis domain:** deterministic momentum, volume/relative-volume, volatility, trend and price-action evidence. Indicators expose raw inputs, timestamps and explanations.
- **Strategy boundary:** independent `IntradayStrategy` and `SwingStrategy` policies, each versioned and configured independently. Intraday is blocked/suppressed if the input freshness contract is not met.
- **Opportunity evaluation:** candidate -> eligibility checks -> evidence/explanation -> conditional trade plan -> publish or suppress with reason. Scores are not calibrated probabilities unless validated later.
- **Lifecycle monitor:** immutable published snapshot; explicit state transitions; idempotent event IDs; manual-execution disclaimer; monitoring based on later eligible observations, not assumed fills.
- **Delivery:** durable outbox -> entitlement/recipient resolution -> Telegram -> retry and terminal state; alerts cover new opportunity and material lifecycle changes only.
- **Reporting:** session summary, opportunities and changes, unresolved/expired/invalidated outcomes, source freshness, and limitations; automated delivery remains gated on proven scheduler integration.
- **Observability:** durable run history, source health, stale data, suppression reasons, dispatch errors, and reproducible correlation IDs.

## 6. Proposed implementation sequence (non-M61)

### E0 — Data and contract audit

Inventory actual data adapters/configuration and tests. Record provider coverage, bar timeframes, timestamps, delay and licensing. Fix the observed timestamp-provenance gap: daily adapter returns timestamped bars, but analysis persistence currently stores only `analysis_date`, and `GenerateSignal` synthesizes `data_timestamp` as midnight UTC on that date. Add/verify data-freshness/provenance contracts before strategy changes.

**Acceptance:** a test matrix covers fresh, delayed, stale, missing, malformed, corrected and future-dated bars; unsupported intraday input cannot produce a real-time-labelled alert.

### E1 — Dual strategy boundaries

Extract/introduce independent strategy interfaces and configuration without changing existing score/threshold semantics. Preserve current signal generation as a separately named/versioned existing strategy until a deliberate migration decision is reviewed.

**Acceptance:** unit tests prove each engine uses its own strategy identity/configuration, cannot overwrite the other's active signal, and emits source/timeframe metadata.

### E2 — Opportunity lifecycle and Telegram

Connect eligible engine outputs to the existing publication/outbox/lifecycle flow. Add remaining transition, retry, idempotency, entitlement and suppression contract tests.

**Acceptance:** deterministic tests verify no duplicate event on replay, immutable published snapshot, visible terminal delivery state, and correct lifecycle changes. PR #416 currently covers only publication-to-entitled-recipient delivery idempotency.

### E3 — Session monitoring and reports

Complete the durable end-of-session report scheduler and delivery integration only after its runtime/deployment trigger is evidenced.

**Acceptance:** duplicate trigger, restart/recovery, missing data, delayed signal, Cairo timezone boundary and Telegram failure tests pass.

### E4 — Operational hardening and release evidence

Complete release checklist, API/UI smoke-test matrix, secrets/configuration checks, persistence/backup/restore and operational runbook. Keep M61 deferred.

**Acceptance:** required CI is green on the exact candidate SHA and each production claim has evidence.

## 7. Explicit non-goals / policy locks

- No automated brokerage orders or claims of executed fills.
- No changes to existing score weights, thresholds, stop/target rules, recommendation policy, Crash Radar 50/40/10 semantics, subscription/payment policy, or news-source policy without separate owner approval.
- No unsupported smart-money/order-flow claims from OHLCV alone.
- No claim of profitability, calibrated win probability, or completed backtesting.
- M61/backtesting remains paused.

## 8. Current CI evidence at design time

- Main before PR #416: run #40737429875 on `d925ec2aa0ce8f8e8b96623bc033a5beef68b0a4` succeeded across unit tests, integration tests, frontend tests, dependency audit and container build.
- PR #416: run #40737685273 on exact head `3928e24cc9df092424ce9257e7d1d5f5034b29ca` succeeded across all five jobs and was squash-merged as `2498bd98a848a37d3e2a4c47df9bb603339fe423`.
- Post-merge main run #40748408269 for the merge SHA was queued when this document was drafted. It must be checked before treating the merged baseline as CI-green.
