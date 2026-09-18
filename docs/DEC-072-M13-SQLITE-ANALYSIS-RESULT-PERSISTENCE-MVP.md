# DEC-072 — SQLite Analysis Result Persistence MVP

**Status:** Accepted  
**Date:** 2026-09-18

## Context

DEC-071 established that completed analysis results must eventually survive process restarts, while remaining behind the application-facing `AnalysisResultStore` boundary.

The current system is a modular monolith with a local development workflow. The first durable persistence slice should therefore minimize operational dependencies while preserving a clear replacement boundary.

`StockAnalysisResult` is a composed domain/application result containing multiple nested analytical value objects. Reconstructing it requires preserving the complete computed result rather than storing only the dashboard fields.

## Decision

Use **SQLite** as the first concrete persistence implementation for analysis results.

Use the Python standard-library `sqlite3` driver for the MVP rather than introducing an ORM or database-specific framework.

Persist each completed analysis as:

- stock symbol / stock identity reference;
- analysis date;
- serialization format/version;
- serialized `StockAnalysisResult` payload.

The serialized payload will be produced and consumed by an explicit infrastructure serializer/mapper. Python object pickling is not allowed as the persistence format.

The existing `AnalysisResultStore` remains the application-facing abstraction. The SQLite adapter is infrastructure-only.

## Boundary

```text
Application
    ↓
AnalysisResultStore
    ↓
SQLiteAnalysisResultStore
    ↓
Serializer / Mapper
    ↓
SQLite
```

## Why SQLite for the MVP

- zero separate database server;
- included with Python;
- transactional storage;
- persistent across application restarts;
- suitable for the current modular-monolith/local deployment model;
- easy to replace behind the existing store boundary if scale or deployment requirements change.

## Serialization Contract

The persistence format must be explicit and versioned.

The serializer must preserve the semantic values needed to reconstruct the complete `StockAnalysisResult`, including nested:

- technical analysis;
- fundamental analysis;
- technical/fundamental scores;
- stock quality;
- entry context and entry quality;
- opportunity classification.

Domain types remain unaware of SQLite and serialization implementation details.

A schema/payload version is stored with each record so future changes can be handled deliberately rather than silently misinterpreting old data.

## Write Semantics

A completed analysis is persisted as one logical store operation.

The write must not expose a partially persisted result to readers.

For the current `get(symbol)` / `get_record(symbol)` contract, the MVP keeps the latest record per symbol. Historical analysis storage is explicitly deferred.

## Read Semantics

`get(symbol)` returns the reconstructed `StockAnalysisResult` or `None`.

`get_record(symbol)` returns the reconstructed result together with its persisted `analysis_date`, or `None`.

Report and alert application services remain unchanged and continue composing read-side projections from the store.

## Failure Semantics

Persistence failures must not be converted into fake analytical results.

The persistence adapter should surface a clear infrastructure/application error. HTTP mapping of such failures will be handled separately at the API boundary if required by the implementation.

Corrupt or unsupported payload versions must fail explicitly rather than being silently ignored or partially reconstructed.

## Tests

The implementation must include:

1. save/get round-trip for a representative `StockAnalysisResult`;
2. preservation of `analysis_date`;
3. latest-record replacement for the same symbol;
4. missing symbol returns `None`;
5. persistence across a store re-instantiation using the same SQLite file;
6. explicit handling of unsupported payload versions;
7. report projection works from a persisted result;
8. alert projection works from a persisted result;
9. existing in-memory store tests remain unchanged;
10. integration coverage verifies analysis → persistent store → report/alert read-side flow.\n11. API-level integration coverage verifies report and alert projections after SQLite store recreation.

## Non-Goals

This MVP does not introduce:

- historical result browsing;
- market-data persistence;
- user accounts;
- authentication/authorization;
- portfolios/watchlists;
- database migrations framework;
- ORM;
- distributed database;
- cloud database;
- scheduler durability;
- trade execution persistence.

## Trade-offs

### SQLite + explicit JSON-style serialization

Advantages:
- simple deployment;
- explicit persistence contract;
- low dependency count;
- complete result reconstruction;
- clear path to later storage replacement.

Costs:
- serializer maintenance is required as domain result types evolve;
- the MVP is not optimized for analytical querying inside the stored payload;
- SQLite is not being selected as a universal future scaling solution.

### ORM

Not selected for the first slice because the project does not yet need relational query complexity, and an ORM would introduce an additional abstraction before the persistence model is understood.

### Pickle

Rejected because it is Python-specific, not a stable explicit data contract, and inappropriate as the durable format for a system expected to evolve.

## Consequences

The SQLite adapter and explicit serializer are implemented behind `AnalysisResultStore`, wired into infrastructure composition, with the in-memory implementation preserved for tests. Store-level and API-level integration tests verify persistence across store recreation.

The API/report/dashboard contracts should remain unchanged.

The local application can restart and still serve the latest completed analysis report from SQLite when the full infrastructure composition is used.

## Revisit Conditions

Revisit the storage technology when deployment topology, concurrency, data volume, query requirements, or operational requirements exceed the SQLite MVP's intended scope.
