# DEC-133 — Market-Agnostic Multi-Market Capability Architecture

**Status:** Proposed — design gate for the post-M61 execution target  
**Date:** 2026-10-05  
**Repository:** palestiny/egx-stock-analyzer

## Context

The project began as an EGX Stock Analyzer. The current product direction is broader:

- achieve feature parity with the publicly documented EGXBot capability set;
- make analytical capabilities reusable across EGX, US, and future markets;
- avoid duplicating the same analysis/scanner/signal/portfolio code per market;
- support data-dependent capability availability without treating missing provider data as an application failure;
- preserve the current modular-monolith architecture;
- eventually support paper, assisted, semi-automatic, and fully automated trading through broker adapters.

The authoritative EGXBot benchmark is a capability reference, not an implementation or UI to copy. Publicly documented capabilities include stock reports, advanced technical engines, scanners, signals/targets/stops, portfolio intelligence, backtesting, alerts, live-market tooling, and AI-assisted research.

## Problem

A market-specific implementation would create duplication:

```
EGX Analysis
US Analysis
Saudi Analysis
...
```

The intended architecture is instead:

```
Market-Agnostic Capability Core
            ↓
      Market Adapters
            ↓
 EGX / US / Saudi / Future
```

The same domain/application capability must be able to consume normalized market observations regardless of exchange.

## Decision

### 1. Market is an adapter boundary, not a feature boundary

Analytical capabilities belong to the shared core.

Examples:

- technical analysis;
- SMC;
- Harmonic;
- Elliott;
- classical patterns;
- divergence;
- Gann;
- Fibonacci;
- scanners;
- signals;
- risk;
- portfolio analytics;
- backtesting;
- research;
- alerts.

Market adapters own market-specific facts and rules.

### 2. Data capabilities are explicit

Each market/data provider exposes a capability profile such as:

```text
historical_bars
realtime_quotes
trades
order_book
fundamentals
news
corporate_actions
short_data
options
```

A capability may be:

- AVAILABLE;
- PARTIAL;
- UNAVAILABLE;
- DEGRADED.

A missing provider capability must not cause the entire platform to fail.

### 3. Analysis engines declare requirements

Every capability declares the minimum evidence it requires.

Example:

```text
SMC
  requires: OHLCV

Order Flow
  requires: trades

Order Book Analysis
  requires: order_book

Fundamental Valuation
  requires: point-in-time fundamentals
```

The platform therefore returns explicit readiness metadata instead of silently producing incomplete analysis.

### 4. Canonical contracts are shared

Market-specific adapters translate external data into provider-neutral contracts.

Target contracts include:

- MarketIdentity;
- Instrument;
- MarketSession;
- PriceBar / market observation;
- Quote;
- Trade;
- OrderBook;
- FundamentalSnapshot;
- NewsContext;
- MarketCapabilities;
- AnalysisResult;
- ScannerQuery / ScannerResult;
- Signal;
- TradePlan;
- Alert;
- PortfolioPosition;
- PortfolioAnalytics;
- BacktestResult;
- ExecutionOrder;
- ExecutionReport.

### 5. Trading execution is a separate boundary

Analysis must never call a broker directly.

The intended flow is:

```
Market Data
    ↓
Analysis
    ↓
Scanner
    ↓
Signal
    ↓
Strategy / Decision
    ↓
Risk Gate
    ↓
Order Management
    ↓
Broker Adapter
    ↓
Execution
```

Execution modes are staged:

1. Alert only.
2. Paper trading.
3. Assisted execution — explicit user approval.
4. Semi-automatic execution — bounded automation.
5. Fully automated execution — only after explicit safety and operational gates.

No live automated execution is authorized by this design gate.

### 6. Risk gates are mandatory before live order submission

The execution boundary must validate, as applicable:

- signal validity;
- strategy state;
- instrument tradability;
- position sizing;
- buying power;
- maximum risk;
- daily loss limit;
- duplicate-order/idempotency protection;
- market/session state;
- price/slippage constraints;
- stop/target validity;
- order-state reconciliation.

A failed gate blocks the order.

## Non-Goals

This decision does not:

- claim every EGXBot feature is already implemented;
- claim every market exposes the same data;
- authorize live trading;
- select a final broker;
- select a final US or EGX market-data provider;
- require microservices;
- require a rewrite of the current domain model;
- copy EGXBot source code, UI, or proprietary implementation.

## Trade-offs

### Benefits

- one analytical implementation across markets;
- lower duplication;
- easier testing and backtesting;
- consistent signal and risk semantics;
- easier future market expansion;
- explicit data limitations;
- broker independence.

### Costs

- stronger canonical contracts are required;
- market rules must be modeled explicitly;
- data normalization becomes a first-class concern;
- some advanced features require market-specific evidence;
- execution introduces a substantially higher safety and operational burden.

## Acceptance Criteria

This gate should be accepted only when the repository has:

1. a complete master capability registry;
2. explicit market/provider capability modeling;
3. canonical market-neutral contracts identified;
4. clear ownership between domain/application/infrastructure;
5. a parity plan covering the documented EGXBot benchmark;
6. a staged execution architecture with live trading explicitly gated;
7. a post-M61 implementation sequence;
8. tests proving capability readiness does not silently fabricate unavailable data.

## Revisit Conditions

Revisit this decision if:

- a required capability cannot be expressed through market-neutral contracts;
- a market requires materially different domain semantics rather than merely different data;
- execution requirements justify a separate deployment boundary;
- regulatory or broker constraints materially change the execution architecture.
