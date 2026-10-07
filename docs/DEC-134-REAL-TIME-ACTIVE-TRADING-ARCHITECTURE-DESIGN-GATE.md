# DEC-134 — Real-Time & Active Trading Architecture Design Gate

**Status:** Proposed — Owner Approval Required  
**Parent:** Market Intelligence / Active Trading & Real-Time Scalping Intelligence  
**Current active execution milestone:** M61 — Backtesting & Strategy Validation

## 1. Purpose

Define the architecture and contracts required to support real-time, tick-by-tick active-trading intelligence without creating a second analytical core, bypassing the DEC-133 decision lifecycle, or coupling the domain to a specific market-data or broker provider.

This gate is architecture/contract work. It does not authorize implementation of a scalping engine, broker integration, or autonomous trading.

## 2. Problem Boundary

The platform should eventually support both:

- slower-horizon investment intelligence; and
- short-horizon real-time active trading/scalping intelligence.

Both must share the same domain and Market Intelligence foundations while allowing different strategy horizons and data requirements.

## 3. Proposed Architecture

```
Provider
  ↓
Market Adapter
  ↓
Normalized Trade / Quote / Tick / Order-Book Events
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
Optional Execution Adapter
```

No component may silently skip evidence, strategy eligibility, or trade-plan semantics.

## 4. Design Areas To Resolve

### Data
- event contracts and timestamps;
- ordering, duplication, gaps, stale data, reconnects;
- quote/trade semantics;
- optional Level-2/order-book semantics;
- provider latency and availability;
- market-session state;
- provenance and replayability.

### Processing
- low-latency state management;
- rolling windows and tick aggregation;
- velocity/acceleration/volume-velocity features;
- liquidity and spread features;
- microstructure features where data permits;
- market-wide scanning and ranking;
- deterministic behavior under replay.

### Strategy
- strategy registry and versioning;
- short-horizon opportunity definitions;
- eligibility rules;
- dynamic entry/invalidation/exit/re-entry;
- costs and slippage;
- risk controls;
- evidence and explanation.

### Validation
- tick replay;
- historical data requirements;
- point-in-time controls;
- out-of-sample/walk-forward validation;
- robustness and sensitivity;
- paper trading;
- latency and operational measurements.

### Delivery and execution
- real-time alerts;
- user interface;
- hotkey boundary;
- position state;
- broker adapter isolation;
- manual confirmation;
- future autonomous execution boundary, if ever proposed.

### Market portability
- generic core contracts;
- EGX adapter;
- US adapter;
- provider-specific capabilities;
- graceful degradation when data is unavailable.

## 5. Explicit Non-Goals

This gate does not decide:

- a specific market-data vendor;
- a specific broker;
- a profitable scalping strategy;
- autonomous order execution;
- guaranteed latency;
- guaranteed profitability;
- production deployment of active trading.

Those require later evidence and/or dedicated gates.

## 6. Acceptance Criteria

DEC-134 can be accepted only when the repository documents:

1. provider-independent real-time market-event contracts;
2. timestamp, ordering, duplication, gap, and stale-data semantics;
3. data-availability and degradation rules;
4. real-time state/tick-engine ownership;
5. scanner/opportunity boundary;
6. strategy registry/versioning boundary;
7. integration with the DEC-133 six-stage decision lifecycle;
8. replay/backtesting boundary;
9. latency and observability model;
10. human-in-the-loop and hotkey boundary;
11. broker/execution isolation;
12. EGX/US market-adapter boundary;
13. failure/recovery semantics;
14. validation and promotion criteria.

## 7. Governance

Until this gate is accepted:

- no RT implementation is authorized;
- M61 remains the sole active execution milestone;
- no M61 acceptance criterion is changed;
- no downstream RT milestone is promoted to active work.

After acceptance, individual RT slices still require explicit roadmap authorization and their own design/implementation gates where architecture or significant behavior changes.

## 8. Decision

**Proposed. Owner approval required.**
