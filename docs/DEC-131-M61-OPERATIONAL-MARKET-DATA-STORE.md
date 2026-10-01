# DEC-131 — M61 Operational Market-Data Store & Conflict Durability

**Status:** Implemented — verification pending CI  
**Milestone:** M61 — Backtesting & Strategy Validation

## Decision

Operational market data is persisted behind an application-facing OperationalMarketDataStore port. The infrastructure implementation is SQLite-specific and is not imported by application services.

A successful provider acquisition is persisted as one acquisition record plus its observations. Each persisted observation carries the acquisition identity that produced it.

## Conflict semantics

Observation identity is:

- stable stock_id;
- timeframe;
- observation timestamp.

An incoming observation with the same identity is idempotent when every stored value matches.

If any value differs:

1. the original observation is never overwritten;
2. the acquisition is durably marked conflicted;
3. a MarketDataConflictEvent is durably recorded;
4. the event stores the observation identity, existing acquisition identity, incoming acquisition identity, existing observation, incoming observation, and detection time;
5. the service raises MarketDataConflictError after the durable event has been committed.

This makes the conflict observable after process restart instead of only being an in-memory exception.

## Transaction boundary

The SQLite adapter owns the persistence transaction. A successful acquisition and its observations commit together.

For a conflict, the adapter commits the conflicted acquisition plus conflict event, then raises. It does not partially persist new observations from that acquisition.

## Why SQLite now

SQLite is already the repository's established operational persistence mechanism. The decision does not prevent a future PostgreSQL adapter because the application boundary is storage-agnostic.

## Explicit non-goals

- final production database selection;
- provider fallback;
- raw-artifact storage;
- corporate-action adjustment;
- EGX session-calendar implementation;
- immutable M61 dataset acceptance.

## Acceptance evidence

Required tests:

1. acquisition and observations survive store recreation;
2. identical duplicate remains idempotent;
3. conflicting duplicate never overwrites the original;
4. conflict event survives store recreation;
5. conflict event links existing and incoming acquisition identities;
6. conflicted acquisition status is durable;
7. provider coverage failures remain durably recorded.

**Gate condition:** all deterministic unit and integration tests pass in CI.
