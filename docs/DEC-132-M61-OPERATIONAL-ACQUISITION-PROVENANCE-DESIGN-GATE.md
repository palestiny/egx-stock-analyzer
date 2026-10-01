# DEC-132 — M61 Operational Acquisition Provenance Design Gate

**Status:** Proposed  
**Date:** 2026-09-28  
**Milestone:** M61 — Backtesting & Strategy Validation

## Purpose

DEC-131 established the operational market-data store boundary. This gate defines how each external acquisition is recorded so the system can answer:

- what provider was queried;
- which source symbol and stable stock identity were involved;
- what range was requested;
- what range was actually returned;
- when acquisition started and completed;
- whether the acquisition succeeded or failed;
- how many rows were received;
- whether a preserved raw artifact can be linked by hash.

## Decisions

### D1 — Acquisition is a first-class provenance record

Every provider acquisition that is actually attempted for a missing operational range produces one AcquisitionRecord.

A request fully satisfied by the local store produces no provider acquisition record.

### D2 — Requested and actual coverage are separate

The record preserves both requested and observed coverage. The system must not claim that a provider returned the requested range merely because the request was made.

### D3 — Failure is durable evidence

Incomplete provider coverage and provider/runtime failures are recorded as failed acquisitions before the exception is propagated to the caller.

A failed acquisition never makes missing market sessions appear covered.

### D4 — Stable stock identity plus source symbol

The record stores the stable internal stock_id and the source-facing symbol separately. This preserves explicit identity mapping and supports future symbol-change handling.

### D5 — Raw artifact hash is optional at this layer

The operational acquisition boundary may attach a preserved raw-artifact SHA-256 when the provider contract permits preservation. The absence of a hash does not mean the acquisition was successful without provenance; it means no preserved raw artifact is linked yet.

### D6 — Operational provenance is separate from immutable M61 dataset provenance

Operational acquisition records explain how the mutable operational store was populated. They do not mutate or replace the immutable M61 evaluation dataset or its manifest.

## Acceptance Tests

1. Successful acquisition creates one successful provenance record.
2. The record contains provider, source symbol, stable stock identity, requested range, actual range, timestamps, and row count.
3. A fully covered local request creates no new acquisition record.
4. Incomplete provider coverage creates a failed provenance record and persists no incomplete market coverage.
5. Provider/runtime failure creates a failed provenance record and does not falsely mark the range as covered.
6. Raw artifact hash remains optional until artifact preservation is wired to the operational acquisition path.

## Non-goals

- Selecting the final production provider.
- Choosing PostgreSQL versus SQLite.
- Implementing raw-artifact storage.
- Defining corporate-action adjustment methodology.
- Implementing the EGX trading calendar.
- Building automatic provider fallback.

## Exit Criteria

This gate can move to accepted when the COMI operational slice has the provenance tests above passing in the project test suite and the persistence boundary can query acquisition history without coupling analysis to the external provider.
