# DEC-076 — M17 Market Universe & All-Market Execution Design Gate

**Status:** Accepted  
**Date:** 2026-09-18  
**Milestone:** M17 — Market Universe & All-Market Execution

## Context

M14 established market-wide execution, but its MVP requires the caller to provide an explicit symbol list. M16 established a market opportunity read view, also using an explicit symbol list.

The product now needs a first-class way to ask the application to operate on the configured EGX universe without making the API, dashboard, or scheduler responsible for discovering symbols.

## Problem

Without an explicit universe-discovery boundary, future callers could duplicate catalog enumeration, hard-code EGX symbols in the API or dashboard, couple scheduling to stock-selection rules, or create different universes for execution and opportunity views.

## Desired Outcome

M17 establishes a deterministic universe contract that:

1. exposes the configured stock symbols through the existing stock catalog boundary;
2. creates a stable universe snapshot for one market-wide execution;
3. reuses RunMarketAnalysis without changing its per-stock semantics;
4. keeps transport, scheduling, and dashboard layers out of universe discovery;
5. provides a future foundation for scheduled full-market analysis.

## Accepted Decisions

### 1. Universe Ownership

Extend the existing StockCatalog contract with:

symbols() -> tuple[str, ...]

The catalog already owns stock identity lookup. Adding enumeration keeps identity and universe membership together without introducing a speculative second StockUniverse abstraction.

A separate universe abstraction remains unnecessary until membership becomes independently persisted, filtered, or user-configurable.

### 2. Deterministic Ordering

StockCatalog.symbols() returns a deterministic normalized tuple. InMemoryStockCatalog preserves constructor stock order and normalizes symbols.

Market-wide execution receives that tuple as its universe snapshot and therefore remains deterministic.

### 3. Snapshot Semantics

A market-wide invocation captures the catalog symbols once before execution begins. Changes to the catalog during execution are outside the M17 contract and must not alter the current run.

### 4. Unknown Symbols

The catalog is the source of the execution universe, so a normal catalog snapshot contains resolvable symbols. RunMarketAnalysis retains its existing unknown-symbol failure behavior because it remains reusable for explicit caller-provided universes.

### 5. Execution Boundary

Introduce an application capability:

RunConfiguredMarketAnalysis

It obtains the current catalog symbol snapshot and delegates execution to RunMarketAnalysis.

It owns no retry, analysis, scoring, ranking, persistence, or provider logic.

### 6. HTTP Boundary

M17 adds a command endpoint:

POST /api/v1/market-analysis

The endpoint triggers the configured-market execution capability and returns the aggregate execution result.

It does not accept a symbol list. Explicit ad-hoc symbol lists remain supported by the underlying M14 use case.

The endpoint does not trigger ranking or notifications.

### 7. Scheduler Boundary

The scheduler remains a trigger mechanism only. Future scheduled full-market analysis will call RunConfiguredMarketAnalysis; it will not enumerate symbols itself.

M17 does not add recurring scheduling behavior.

### 8. Dashboard Boundary

M17 does not add new dashboard behavior. The dashboard remains a presentation client and does not discover or hard-code the market universe.

### 9. Persistence

No new persistence schema is introduced. Successful stock results continue to be persisted by the existing single-stock capability.

### 10. Concurrency

Execution remains sequential. Concurrency is still deferred until evidence requires throughput optimization and its ordering, provider-limit, and failure semantics receive a separate design gate.

## Application Boundary

RunConfiguredMarketAnalysis
          ↓
StockCatalog.symbols()
          ↓
RunMarketAnalysis
          ↓
RunStockAnalysis
          ↓
AnalysisResultStore

## TDD Acceptance Criteria

### Catalog

- symbols are returned normalized;
- symbol ordering is deterministic;
- duplicate catalog symbols cannot produce an ambiguous universe.

### Application

- configured market analysis captures the catalog snapshot once;
- empty configured universe completes as a no-op;
- execution delegates the exact snapshot to RunMarketAnalysis;
- existing per-stock failure semantics are preserved;
- no ranking or analytical calculation is introduced.

### API

- POST /api/v1/market-analysis invokes the configured execution capability;
- successful execution returns aggregate execution state and per-stock success/failure metadata;
- execution failure is represented without exposing internal stack traces;
- the endpoint does not accept or require a symbol list.

## Non-Goals

M17 does not introduce:

- user-configurable watchlists;
- historical universes;
- exchange membership synchronization;
- live exchange constituent feeds;
- recurring schedules;
- concurrency;
- ranking changes;
- dashboard ranking changes;
- notifications;
- portfolio allocation;
- trading execution;
- AI-based stock selection.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M17 MVP defined here.**

M17 is an orchestration and universe-discovery extension. It does not modify the analytical brain, M14 market execution semantics, M15 ranking, or M16 read-side view contract.

## Revisit Conditions

Revisit this design if the universe becomes independently persisted, user-configurable, exchange-synchronized, filtered by strategy, or required to vary by tenant/account.
