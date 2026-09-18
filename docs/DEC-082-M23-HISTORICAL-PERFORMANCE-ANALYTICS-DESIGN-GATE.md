# DEC-082 — M23 Historical Performance Analytics Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M23

## Purpose

M22 compares two persisted analysis snapshots. M23 adds a strictly descriptive performance metric over the same persisted snapshots so the system can answer:

> What price change was observed between two completed analysis snapshots?

This capability measures observed historical price movement. It does not predict future returns, evaluate a trading strategy, or recommend an investment decision.

## Problem

The project now preserves and compares historical analytical snapshots, including the current price contained in each snapshot's `EntryContext`.

Without a dedicated performance boundary, consumers may start calculating price returns in dashboards, reports, or ad-hoc scripts. That would duplicate financial semantics outside the application layer.

## Accepted Boundary

```
Historical Snapshot A
        +
Historical Snapshot B
        ↓
CalculateSnapshotPerformance
        ↓
Descriptive Performance Metrics
        ↓
HTTP / Dashboard consumers
```

The capability is read-only and operates only on persisted snapshots. It never executes fresh analysis.

## Accepted Decisions

### 1. Measurement

M23 calculates:

- absolute price change;
- percentage price change.

Given a valid before price (P_b) and after price (P_a):

```
price_change = P_a - P_b

price_change_percent = ((P_a - P_b) / P_b) * 100
```

The calculation uses domain `Decimal` values.

### 2. Snapshot Selection

The caller selects the two snapshots explicitly by UUID, matching M22.

Both snapshots must belong to the same stock.

The caller-selected direction remains authoritative:

- `before` is the baseline;
- `after` is the comparison point.

Snapshot dates do not silently reorder the request.

### 3. Missing Prices

If either snapshot has no `EntryContext.current_price`, performance cannot be calculated.

The application returns an explicit unavailable result rather than inventing a value or using another field as a substitute.

### 4. Zero Baseline

If the before price is zero, percentage performance is undefined.

The capability returns an explicit unavailable percentage rather than dividing by zero.

The absolute price change remains available when both prices exist.

### 5. Read-Only Behavior

M23:

- does not execute analysis;
- does not mutate persisted snapshots;
- does not change scoring/classification;
- does not persist derived performance metrics;
- does not introduce a database schema change.

### 6. Financial Scope

M23 measures price movement only.

It does not include:

- dividends;
- splits or corporate-action adjustments;
- transaction costs;
- taxes;
- slippage;
- benchmark returns;
- risk-adjusted returns;
- annualization;
- portfolio allocation;
- trade execution;
- forward-looking prediction.

Those require separate domain decisions and data requirements.

### 7. Presentation Boundary

API and dashboard consumers receive the performance read model. They must not recalculate the percentage or duplicate the Decimal arithmetic.

## Alternatives Considered

### Calculate in the Dashboard

Rejected because it would duplicate financial semantics in the presentation layer.

### Add Performance Fields to Historical Snapshots

Rejected because the metrics are derived from two snapshots and should not become mutable/persisted snapshot state.

### Build a Full Portfolio Performance Engine

Deferred because it requires positions, fills, costs, corporate actions, cash flows, and portfolio semantics that M23 does not need.

### Use Adjusted Returns From an External Provider

Deferred because that would introduce provider-specific historical adjustment semantics and additional data requirements.

## TDD Acceptance Criteria

- two snapshots with prices produce the correct absolute change;
- two snapshots with prices produce the correct percentage change;
- Decimal arithmetic is preserved;
- caller-selected before/after direction is preserved;
- cross-symbol snapshots are rejected;
- missing before snapshot is reported explicitly;
- missing after snapshot is reported explicitly;
- missing current price produces unavailable performance;
- zero before price produces unavailable percentage without failing absolute change;
- no fresh analysis is executed;
- no persistence mutation occurs;
- identical snapshot IDs are rejected;
- API/dashboard consume the read model without recalculating metrics.

## Scope Boundary

Deferred:

- forward-looking signal outcome evaluation;
- benchmark comparison;
- dividend-adjusted total return;
- transaction-cost modeling;
- portfolio performance;
- risk-adjusted metrics;
- predictive analytics;
- automated trading;
- AI-generated performance interpretation.

## Design Gate Decision

**Accepted. Implementation is authorized for the M23 MVP defined above.**

The implementation should be a pure/read-side application capability over the existing historical snapshot repository, with API/dashboard integration only after the application contract is established and tested.
