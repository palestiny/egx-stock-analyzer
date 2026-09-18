# DEC-071 — M13 Durable Analysis State Boundary

**Status:** Accepted  
**Date:** 2026-09-18

## Context

The first API/dashboard slice initially stored analysis results in `InMemoryAnalysisResultStore`.

That implementation was appropriate for controlled development and vertical-slice validation, but it lost analysis results when the process stopped. M13 therefore established a persistence boundary before durable operation could be considered.

## Decision

Introduce a persistence design boundary for analysis results before implementing a concrete database technology.

The persisted application state must preserve the information required by the existing reporting and alert read-side contracts:

- stock symbol / stock identity reference;
- completed analysis result;
- analysis date;
- the analytical values already represented by `StockAnalysisResult`;
- enough state to reconstruct the existing report and alert projections.

The persistence layer will be an infrastructure concern behind the existing `AnalysisResultStore` application-facing contract.

The current application and domain layers must not depend directly on a database library.

## Boundary

```text
API / Dashboard
      ↓
Application
      ↓
AnalysisResultStore
      ↓
Persistence Adapter
      ↓
Persistent Store
```

The existing `InMemoryAnalysisResultStore` remains useful for unit tests and lightweight development tests.

## Non-Goals

This decision does not yet introduce:

- authentication or authorization;
- user-specific portfolios or watchlists;
- a trade/order database;
- market-data warehousing;
- historical chart storage;
- a distributed database;
- database-driven scheduling;
- a specific vendor or deployment platform.

## Persistence Contract

The existing `AnalysisResultStore` contract is the starting application boundary.

Persistence must preserve the semantic distinction between:

```text
analysis result
+
analysis date
```

and must not recompute analytical values when reading them back.

Read-side report and alert composition remains in the existing application/domain reporting boundaries.

## Alternatives Considered

### Continue with in-memory storage

Advantages:
- zero infrastructure;
- simple local development.

Trade-off:
- state is lost on process restart;
- unsuitable for durable operation.

### Introduce a database directly into application/domain code

Not selected because it would couple business/application behavior to a persistence technology and weaken the existing modular boundary.

### Define the persistence boundary first

Selected because it lets the project decide what must be durable before choosing database technology.

## Consequences

The next implementation gate should define:

- concrete persistence technology;
- schema/storage model;
- serialization strategy for domain analytical results;
- repository/adapter responsibilities;
- migration/versioning approach;
- transaction semantics;
- failure behavior;
- test strategy;
- local development setup.

No database dependency should be introduced until that implementation gate is accepted.

## Revisit Conditions

Revisit this decision if:

- analysis results are intentionally made ephemeral;
- a different durable storage requirement replaces the current result-store model;
- the system moves to a service architecture with an external persistence contract.


## Implementation Status

DEC-072 implements this boundary with `SQLiteAnalysisResultStore` behind `AnalysisResultStore`. The default infrastructure composition now uses the SQLite implementation, while the in-memory implementation remains available for isolated tests and explicit composition. Persistence acceptance and integration validation are recorded in DEC-072.