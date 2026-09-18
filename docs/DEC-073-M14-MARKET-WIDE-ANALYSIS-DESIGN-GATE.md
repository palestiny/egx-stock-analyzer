# DEC-073 — Market-Wide Analysis Capability Design Gate

**Status:** Accepted  
**Date:** 2026-09-18  
**Milestone:** M14

## Context

The current system can execute analysis for an individual stock symbol and can persist the latest completed result per symbol.

The project's stated purpose, however, is broader than single-symbol analysis: the system should eventually analyze the EGX stock universe consistently and expose the resulting opportunities.

The current architecture already contains important building blocks:

```
StockCatalog
    ↓
RunStockAnalysisBySymbol
    ↓
RunStockAnalysis
    ↓
AnalysisInputAssembler
    ↓
DailyMarketAnalysis
    ↓
AnalysisResultStore
```

The next capability should extend the application around these existing boundaries rather than move market-wide orchestration into the domain or dashboard.

## Problem

There is currently no explicitly designed application capability whose responsibility is:

> Take a defined stock universe for a given analysis date, execute analysis across that universe, preserve per-stock success/failure semantics, and expose an aggregate execution result.

This creates an important design question before implementation:

- What exactly constitutes the analysis universe?
- Who owns selection and ordering?
- What happens when some stocks fail?
- What does a market-wide run mean when data is unavailable for one symbol?
- Should one failure stop the entire run?
- How should the aggregate run be represented?
- What relationship should exist between market-wide execution and the existing per-symbol use case?

## Desired Outcome

Introduce a market-wide analysis application capability that can:

1. obtain a defined stock universe;
2. execute the existing stock-analysis capability for each stock;
3. preserve the existing per-stock domain/application rules;
4. distinguish aggregate execution state from individual stock outcomes;
5. persist successful per-stock results through the existing `AnalysisResultStore` boundary;
6. make partial success and failure explicit;
7. remain independent from HTTP, dashboard, provider-specific APIs, and notification delivery.

## Scope of This Design Gate

This gate covers only the application-level market-wide execution boundary.

### In scope

- stock-universe input/selection contract;
- orchestration ownership;
- per-stock execution semantics;
- aggregate execution semantics;
- partial failure behavior;
- interaction with `RunStockAnalysis`;
- interaction with `AnalysisResultStore`;
- testability;
- deterministic execution behavior.

### Explicitly out of scope

- ranking opportunities;
- watchlists;
- historical result browsing;
- new persistence schema;
- notification delivery;
- authentication;
- dashboard changes;
- provider failover;
- distributed workers;
- concurrency/scaling;
- trading decisions;
- portfolio allocation;
- AI-based selection.

Those capabilities require separate design decisions.

## Current Architectural Boundary

The intended direction is:

```
Market-Wide Application Use Case
          ↓
Stock Universe / Catalog
          ↓
RunStockAnalysis
          ↓
AnalysisInputAssembler + Analysis Pipeline
          ↓
AnalysisResultStore
```

The market-wide capability should orchestrate existing application capabilities rather than duplicate their analysis logic.

## Alternatives Considered

### A — Add a `run_all()` method to `RunStockAnalysis`

**Idea:** Extend the existing single-stock use case so it accepts one or many stocks.

**Trade-offs:**

- fewer application classes;
- but weakens the single-stock use-case boundary;
- introduces two orchestration responsibilities into one component;
- makes the existing use case harder to reason about and test.

**Current assessment:** Not selected for the initial design direction.

### B — Create a dedicated market-wide application use case

Conceptually:

```
RunMarketAnalysis
    ↓
StockCatalog
    ↓
RunStockAnalysis
```

**Trade-offs:**

- explicit responsibility;
- preserves the single-stock boundary;
- easy to test aggregate semantics independently;
- introduces one additional application component.

**Current assessment:** Preferred candidate for further design.

### C — Put market-wide orchestration in the scheduler

**Idea:** The scheduler directly discovers stocks and executes analysis.

**Trade-offs:**

- convenient for the scheduled path;
- couples scheduling to business execution semantics;
- prevents manual/API callers from reusing the same market-wide capability;
- makes testing harder.

**Current assessment:** Not selected.

### D — Put orchestration in the dashboard/API

**Idea:** The client calls the single-symbol endpoint repeatedly.

**Trade-offs:**

- simple client implementation;
- creates transport-level orchestration;
- duplicates workflow knowledge in clients;
- poor fit for scheduled/background execution;
- makes partial failure semantics a client concern.

**Current assessment:** Not selected.

## Open Questions

These must be answered before implementation:

1. **Universe source:** Should the first MVP accept an explicit list of stocks, use `StockCatalog`, or introduce a separate universe abstraction?
2. **Failure semantics:** Should the aggregate execution be `COMPLETED`, `PARTIALLY_COMPLETED`, or `FAILED` when only some symbols fail?
3. **Ordering:** Is deterministic catalog ordering required?
4. **Empty universe:** What should happen when the requested universe is empty?
5. **Persistence:** Should successful stocks be persisted immediately as they complete, or only after the aggregate run finishes?
6. **Retry ownership:** Should existing per-stock retry semantics remain entirely inside `RunStockAnalysis`?
7. **Execution identity:** Should the aggregate run have its own execution identity separate from the existing per-stock execution?
8. **Concurrency:** The first MVP should remain sequential unless evidence establishes a need for concurrency.

## Proposed Invariants

The design should preserve these invariants unless evidence changes them:

1. One stock failure must not silently erase successful results for other stocks.
2. Per-stock analysis rules remain owned by the existing single-stock capability.
3. Market-wide orchestration must not calculate technical/fundamental scores itself.
4. Provider-specific behavior must remain behind infrastructure boundaries.
5. Successful per-stock persistence remains behind `AnalysisResultStore`.
6. Aggregate status must be derived from explicit per-stock outcomes.
7. The first implementation should be deterministic and sequential.

## TDD Acceptance Shape

Before implementation, tests should establish behavior for at least:

- empty universe;
- one-stock success;
- multiple-stock success;
- one failure with other successes;
- all stocks failing;
- unknown/missing stock handling;
- deterministic execution ordering;
- successful result persistence;
- reuse of existing single-stock analysis behavior;
- aggregate execution result semantics.

## Accepted Decisions

### 1. Universe Source

The M14 MVP accepts an explicit ordered list of stock symbols as its input universe.

The market-wide use case resolves each symbol through the existing StockCatalog. A separate StockUniverse abstraction is not introduced yet because the current problem is orchestration, not reusable universe-management behavior.

### 2. Aggregate Failure Semantics

The aggregate result uses states distinct from the existing per-stock ExecutionState:

- COMPLETED — all requested stocks completed successfully, including the empty-universe no-op case.
- PARTIALLY_COMPLETED — at least one stock completed and at least one stock failed.
- FAILED — all requested stocks failed.

Individual stock outcomes remain available. An unknown symbol is an individual stock failure rather than an abort of the entire run.

### 3. Deterministic Ordering

Execution is sequential and follows the caller-provided symbol order. The use case does not sort implicitly.

Duplicate normalized symbols are rejected before execution to prevent ambiguous repeated work.

### 4. Empty Universe

An empty universe is a valid no-op and returns COMPLETED with zero successes and zero failures.

### 5. Persistence Timing

Successful per-stock analysis is persisted by the existing RunStockAnalysis capability immediately when that stock completes. The market-wide use case does not introduce aggregate persistence.

Therefore, earlier successful results remain available when a later stock fails.

### 6. Retry Ownership

Per-stock retry behavior remains owned by RunStockAnalysis and its existing retry boundary. RunMarketAnalysis does not duplicate retry policy, backoff, or provider-specific failure classification.

A stock is failed for the aggregate result only after the existing single-stock capability has exhausted its retry semantics and reports failure.

### 7. Execution Identity

The market-wide run has its own aggregate execution identity, separate from individual stock execution identities.

M14 does not persist aggregate execution history; the identity exists to distinguish one market-wide invocation and support future observability.

### 8. Concurrency

The M14 MVP remains sequential. Concurrency is deferred because the current requirement is deterministic orchestration, not throughput optimization, and concurrency would introduce additional decisions around ordering, provider limits, failure isolation, and observability.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M14 MVP defined here.**

The implementation boundary is:

```
RunMarketAnalysis
      ↓
StockCatalog
      ↓
RunStockAnalysis
      ↓
AnalysisResultStore
```

RunMarketAnalysis owns only market-wide orchestration and aggregate result semantics. It must not calculate analytical scores, classification, support/resistance, or provider-specific behavior.

## TDD Acceptance Criteria

- empty universe returns COMPLETED with zero outcomes;
- one-stock success returns COMPLETED;
- multiple stocks execute in the exact supplied order;
- one failure with other successes returns PARTIALLY_COMPLETED;
- all stocks failing returns FAILED;
- unknown symbols become individual failures without aborting later symbols;
- duplicate normalized symbols are rejected before execution;
- successful stocks remain persisted when a later stock fails;
- existing per-stock retry behavior is reused;
- the aggregate run receives a distinct execution identity;
- no analytical calculation is introduced into the market-wide orchestration layer.

## Consequences if Accepted

If this gate is accepted, the likely implementation boundary becomes:

```
RunMarketAnalysis
      ↓
StockCatalog
      ↓
RunStockAnalysis
      ↓
AnalysisResultStore
```

The API, dashboard, scheduler, ranking, and notification layers remain consumers of this application capability rather than owners of market-wide analysis semantics.

## Revisit Conditions

Revisit this gate if:

- the stock-universe model changes materially;
- persistent historical analysis becomes the next requirement;
- concurrency becomes an operational requirement;
- distributed execution becomes necessary;
- the scheduler requires different execution semantics;
- the analysis pipeline can no longer be safely reused per stock.
