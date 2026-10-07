# DEC-134 — Real-Time & Active Trading Architecture Design Gate

**Status:** Proposed — Owner Approval Required  
**Parent:** Market Intelligence / Active Trading & Real-Time Scalping Intelligence  
**Current active execution milestone:** M61 — Backtesting & Strategy Validation

## 1. Purpose

Define the architecture and contracts required to support real-time, tick-by-tick active-trading intelligence without creating a second analytical core, bypassing the DEC-133 decision lifecycle, or coupling the domain to a specific market-data or broker provider.

This gate is architecture/contract work only. It does not authorize implementation, production deployment, or autonomous market actions.

## 2. Problem Boundary

The platform should eventually support both slower-horizon investment intelligence and short-horizon real-time active-trading intelligence. Both share the same Market Intelligence foundations while allowing different strategy horizons and data requirements.

## 3. Architecture

```text
Provider
  ↓
Market Adapter
  ↓
Normalized Market Events
  ↓
Ingest / Integrity Gate
  ↓
Real-Time State & Tick Engine
  ↓
Feature Engine
  ↓
Scanner / Opportunity Detection
  ↓
Strategy Eligibility
  ↓
Trade Plan
  ↓
Recommendation / Alert
  ↓
Human Action
  ↓
Safety / Execution Boundary
  ↓
Optional Execution Adapter
```

The Safety / Execution Boundary is a mandatory architectural boundary, not a UI concern.

## 4. Resolved Design Decisions

### 4.1 Clock and timestamp semantics

Preserve, when available: source/event time, receive time, processing time, decision time, and execution-related audit times. Source time identifies when the market event occurred; receive time identifies when the system knew about it. A monotonic local clock is used for duration/latency measurement. UTC timestamps are used for audit/correlation. Source time must never be overwritten by local receive time. If clock comparability is unreliable, precise source-to-system latency is reported as unavailable rather than guessed. citeturn0search0turn0search8

### 4.2 Event ordering and sequence semantics

Ordering authority comes from the provider contract. Priority is: guaranteed provider sequence, otherwise provider event-time ordering, otherwise explicitly declared provider semantics. Local arrival time is never authoritative market ordering.

Adapters classify streams as strict, ordered-with-gaps, timestamp-ordered, or unordered/unknown. Duplicate identities are idempotent. Sequence gaps create an integrity/recovery state. Backward sequence is treated according to provider semantics rather than silently accepted. Timestamp-only streams use bounded deterministic reordering when safe; otherwise ordering uncertainty is preserved.

### 4.3 Gap and reconnect handling

Disconnect/reconnect creates a recovery state. Recovery is: detect loss → mark affected state degraded → suspend decisions that require continuity → reconnect with bounded backoff → obtain provider-supported snapshot/resync → reconcile sequence/state → record the gap → rebuild required rolling state → restore decision eligibility only after integrity conditions pass.

Missing intervals are preserved as gaps. Synthetic market events are never invented to make the stream appear continuous.

### 4.4 Canonical market-event contracts

The core uses provider-independent normalized contracts.

**NormalizedTrade:** instrument identity, source/venue, event time, receive time, price, quantity, sequence/event identity when available, conditions when available, integrity status.

**NormalizedQuote:** instrument identity, source/venue, event time, receive time, bid/ask price and size when available, sequence/event identity when available, conditions when available, integrity status.

**NormalizedTick:** a generic event envelope, not a separate market truth. It identifies the underlying event type and preserves provenance.

**NormalizedOrderBook:** depth state/change only when the provider supplies sufficient Level-2 information.

Missing, unsupported, stale, invalid, and unknown are distinct states. Absence never means zero.

### 4.5 Stale-data policy

Freshness is relative to market/session state, instrument, event type, strategy requirements, and provider behavior. There is no universal stale threshold.

Track last event time, last receive time, last valid continuity state, freshness status, and degradation reason. Execution-relevant decisions fail closed when required evidence is stale or integrity is unknown. User-facing views may display stale information only with explicit stale status. Freshness thresholds are versioned strategy/configuration data and are observable. citeturn0search0

### 4.6 Market-session state

Normalized session states are: CLOSED, PRE_OPEN/AUCTION where applicable, OPEN, HALTED/SUSPENDED where applicable, POST_CLOSE/AUCTION where applicable, and UNKNOWN/DEGRADED.

Market adapters translate venue calendars into these states. Strategies declare eligible session states. A quiet CLOSED session is not automatically a data failure; stale data during OPEN may be.

### 4.7 Memory and state lifecycle

Real-time state is divided into ephemeral hot state, reconstructible derived state, and durable audit/provenance state.

Every in-memory state object has an owner, scope, warm-up rule, retention/window rule, invalidation rule, rebuild rule, and memory bound. Unbounded per-event state is prohibited. Restart never silently restores decision eligibility from opaque memory; required state is rebuilt or revalidated.

### 4.8 Backpressure

Backpressure is an integrity condition. The system distinguishes normal, elevated, degraded, and overload states.

Under overload, non-critical work may be shed and explicitly permitted derived computations may be reduced/coalesced. Critical event integrity must not be silently sacrificed. If safe processing capacity is exceeded, decision generation enters a degraded/blocked state instead of pretending the stream is complete.

Observe queue depth, event age, processing lag, drops/coalescing, and recovery state.

### 4.9 Market-wide scanner scaling

Market-wide scanning is a consumer of normalized per-instrument state and must not block instrument integrity processing.

Normalize once, maintain per-instrument state incrementally, derive features incrementally, publish opportunity updates, and maintain a bounded incremental ranking/index. Do not perform a full-market recomputation on every event. Under capacity pressure, scanner breadth/freshness may degrade before safety/integrity controls do.

### 4.10 Provider capability matrix

Each adapter declares capabilities explicitly:

| Capability | States |
|---|---|
| Trades | supported / delayed / unsupported |
| Quotes | supported / delayed / unsupported |
| Level-2 | full / partial / unsupported |
| Sequence | guaranteed / partial / unavailable |
| Replay | native / external / unavailable |
| Snapshot recovery | supported / partial / unavailable |
| Market status | supported / derived / unavailable |
| Corporate actions | supported / external / unavailable |
| Timestamps | source / provider / local-only |
| Latency metadata | measured / partial / unavailable |

The core uses capabilities for eligibility/degradation and never assumes EGX and US providers expose equivalent data.

### 4.11 Level-2 semantics

Level-2 is optional evidence. Distinguish best bid/ask, aggregated depth, price-level depth, order-level depth when actually available, snapshots, and incremental updates.

A book is considered reconstructible only when the provider supplies sufficient sequencing and snapshot semantics. Partial/delayed/unsupported Level-2 makes dependent strategies ineligible or lower-evidence; the system must not infer participant intent or queue position beyond what the data contract supports.

### 4.12 Replay fidelity

Replay is mandatory for any strategy whose behavior depends on real-time conditions.

Retain, where available: source timestamps, receive timestamps, provider/venue, sequence/event identity, observed arrival order, duplicates, gaps, reconnect/recovery events, corrections, session state, and capability state.

Two modes exist: market-time replay and system-observed replay. System-observed replay is authoritative for evaluating latency-sensitive live behavior because it reproduces what the live system actually received and when. Clean OHLCV history alone is insufficient for tick-level validation. citeturn0search4

### 4.13 Latency budget and measurement

Latency is measured as a chain: source event → receive → process → feature → strategy → recommendation → human action → execution boundary → broker acknowledgement/fill when available.

Each measurable segment exposes p50, p95, p99, maximum/outlier, sample count, and clock-quality status. The architecture does not impose a universal millisecond target. Targets are strategy/provider/market specific and must be established from measured evidence. Tail latency, queueing, staleness, gaps, and reconnects are part of real-time quality. citeturn0search3turn0search8

### 4.14 Hotkey safety and duplicate-action protection

Hotkeys belong to the Safety / Execution Boundary, not ordinary UI behavior.

The hotkey layer emits a human-action intent. Deterministic runtime enforcement decides whether that intent is admissible. Checks include session eligibility, freshness/integrity, strategy eligibility where applicable, instrument identity, current state, risk constraints, duplicate protection, idempotency identity, kill-switch state, and execution-boundary health.

The UI and any AI component cannot bypass these checks. Repeated key presses, retries, reconnects, or duplicated messages must not create unintended duplicate actions. Every accepted/rejected intent is auditable.

**Fail closed:** if execution-safety state cannot be established, the action is rejected rather than guessed. Safety enforcement belongs to deterministic runtime code, not the UI/model layer. citeturn0search2

### 4.15 Position synchronization

Position state is externally reconciled state. Maintain local intended state, execution-reported state, synchronization time, pending state where available, and reconciliation status.

Normalized states: SYNCED, PENDING, DIVERGED, UNKNOWN. Decision/execution-relevant actions are blocked when actual position state is unknown or materially divergent. Execution reports, when available, are authoritative over local intent.

### 4.16 Kill switch / emergency stop

The kill switch has higher authority than strategy, AI, hotkey, and UI intent.

It supports global blocking, scope where supported, cancellation of eligible pending actions where supported, durable audit, and explicit reset. No lower layer may bypass it.

Reset requires explicit revalidation of market-data integrity, position synchronization, pending-action state, execution-boundary health, and risk state.

### 4.17 Paper-trading equivalence

Paper mode uses the same normalized event path, feature engine, strategy registry, eligibility rules, trade-plan semantics, safety checks, and recommendation/execution boundary as live mode. Only the final execution adapter/model differs.

Paper/live differences are explicit and versioned: fill model, latency model, slippage model, liquidity assumptions, and external response behavior. Paper results record the model/version used.

### 4.18 Broker execution isolation

Broker integration is an adapter behind the Safety / Execution Boundary. Core domain and strategies do not depend on broker SDK types, authentication, transport, or account-specific objects.

The normalized execution boundary owns abstract actions and state queries; broker adapters translate them. Broker connectivity failure cannot corrupt analytical state.

### 4.19 Promotion criteria: research → paper → live

Promotion is strategy-version specific and evidence based.

**Research:** explicit strategy/version; deterministic configuration; point-in-time correctness; reproducible replay; historical validation; costs/slippage assumptions; OOS or walk-forward evaluation; robustness/sensitivity; known data-quality limits.

**Paper:** all research requirements plus production-path equivalence, operational telemetry, measured latency distribution, verified stale/gap/reconnect behavior, verified state reconciliation, no unresolved critical safety defect, and predeclared acceptance bounds.

**Live:** all paper requirements plus explicit version approval, defined risk limits, tested kill switch, duplicate-action protection, state reconciliation, execution-boundary failure/recovery tests, measured latency/slippage within declared bounds, monitoring, rollback/disable procedure, and explicit human owner authorization.

A strategy is never promoted solely because it is profitable in backtest or paper mode. Acceptance thresholds are declared before evaluation; changing them after seeing results creates a new version.

## 5. Failure and Recovery Model

Execution-relevant runtime states are:

- READY
- DEGRADED
- RECOVERING
- BLOCKED
- KILL_SWITCHED

Sequence gaps without successful resync, stale required evidence, unknown session, execution-critical overload, unknown/divergent state, unhealthy execution boundary, unresolved duplicate condition, or active kill switch can force DEGRADED/RECOVERING/BLOCKED as appropriate.

Recovery is explicit and observable. READY is restored only after the relevant invariants are re-established.

## 6. Explicit Non-Goals

This gate does not decide:

- a specific market-data vendor;
- a specific broker;
- a profitable scalping strategy;
- autonomous order execution;
- guaranteed latency;
- guaranteed profitability;
- production deployment of active trading.

Those require later evidence and/or dedicated gates.

## 7. Acceptance Criteria

DEC-134 can be accepted only when the repository documents and agrees on:

1. provider-independent real-time market-event contracts;
2. source/receive/process/decision/execution timestamp semantics;
3. provider-authoritative ordering and sequence semantics;
4. duplicate, gap, reconnect, and recovery behavior;
5. stale-data and freshness policy;
6. explicit market-session state model;
7. real-time state ownership, lifecycle, bounds, and rebuild semantics;
8. backpressure and overload behavior;
9. market-wide scanner scaling boundary;
10. provider capability matrix and graceful degradation;
11. Level-2 semantics and limitations;
12. replay-fidelity requirements;
13. measurable latency model and observability;
14. scanner/opportunity boundary;
15. strategy registry/versioning boundary;
16. integration with the DEC-133 six-stage decision lifecycle;
17. hotkey intent vs deterministic safety-enforcement boundary;
18. duplicate-action/idempotency protection;
19. position synchronization and reconciliation;
20. kill-switch authority and recovery;
21. paper/live-path equivalence;
22. broker/execution isolation;
23. research → paper → live promotion criteria;
24. failure/recovery state model.

## 8. Governance

Until this gate is accepted:

- no RT implementation is authorized;
- M61 remains the sole active execution milestone;
- no M61 acceptance criterion is changed;
- no downstream RT milestone is promoted to active work.

After acceptance, individual RT slices still require explicit roadmap authorization and their own design/implementation gates where architecture or significant behavior changes.

## 9. Decision

**Proposed — Owner Approval Required.**

The architecture details above are now resolved at the gate level. Acceptance of DEC-134 is a separate owner decision and does not authorize implementation by itself.
