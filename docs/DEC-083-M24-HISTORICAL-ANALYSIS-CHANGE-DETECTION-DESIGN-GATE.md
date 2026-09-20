# DEC-083 — M24 Historical Analysis Change Detection Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M24

## Purpose

M20 introduced immutable historical analysis snapshots, M21 exposed history, M22 compares two snapshots, and M23 calculates descriptive price performance.

The remaining concrete gap is **change detection**: the system can show that values differ, but it does not yet expose a stable application-level description of *which analytical dimensions changed*.

M24 establishes a read-only change-detection capability over persisted snapshots.

The capability is descriptive. It identifies observed changes between two completed snapshots; it does not decide whether a change is good, bad, significant, actionable, or worth notifying about.

## Problem

Without a dedicated boundary, future alerting, reporting, or dashboard code may independently inspect snapshot fields and invent change semantics.

That would duplicate business semantics across consumers and make later notification behavior inconsistent.

M24 therefore creates one application-level change-detection contract that downstream consumers can reuse.

## Accepted Boundary

```
Persisted Snapshot A
        +
Persisted Snapshot B
        ↓
CompareAnalysisSnapshots
        ↓
DetectAnalysisChanges
        ↓
Immutable Change Set
        ↓
API / Dashboard / Future Alert Consumers
```

The capability is read-only and never executes fresh analysis.

## Accepted Decisions

### 1. Change Detection Is Descriptive

A change means that a defined persisted analytical field differs between the selected snapshots.

M24 detects whether these dimensions changed:

- opportunity classification;
- technical score;
- fundamental score;
- stock quality score;
- entry quality score;
- current price;
- nearest support;
- nearest resistance.

The detector does not assign positive/negative meaning.

### 2. Reuse M22 Comparison Semantics

M24 consumes the existing snapshot-comparison contract rather than reading persistence independently or duplicating snapshot validation.

Therefore it inherits:

- explicit before/after snapshot IDs;
- same-stock validation;
- different-snapshot validation;
- missing-snapshot errors;
- caller-selected before/after direction.

### 3. Null Semantics

For optional price-based fields:

- both values absent → no change;
- both values present and equal → no change;
- one absent and one present → changed;
- both values present and different → changed.

This makes availability transitions observable without fabricating numeric deltas.

### 4. Change Identity

Each detected dimension is represented by a stable enum/value rather than a free-form string.

The result contains an ordered immutable collection of detected changes.

Ordering is deterministic and follows the declared dimension order in the application contract.

### 5. Empty Change Set

If every supported dimension is unchanged, the capability returns an empty change set.

This is a valid result, not an error.

### 6. No Significance Thresholds

M24 does not introduce thresholds such as:

- score changed by N points;
- price moved by N%;
- classification changed only in certain directions.

Any significance or notification policy requires a later design gate.

### 7. No Notification Delivery

M24 does not send email, Telegram, WhatsApp, push notifications, or any other notification.

It only produces a reusable change read model.

### 8. No Persistence

Detected changes are derived from persisted snapshots and are not stored as a new persistence model.

### 9. No Prediction or Recommendation

M24 does not predict future movement, recommend an action, or evaluate whether a detected change is favorable.

## Alternatives Considered

### Let Each Consumer Inspect Snapshot Deltas

Rejected because API, dashboard, and future alerting consumers would duplicate the same change semantics.

### Add Change Flags to Historical Snapshots

Rejected because a change is a relationship between two snapshots, not intrinsic state of either snapshot.

### Add Threshold-Based Alert Rules Immediately

Deferred because significance thresholds and notification policy are separate product/domain decisions.

### Build Change Detection Inside the Scheduler

Rejected because scheduling should trigger business capabilities, not own analytical comparison semantics.

## TDD Acceptance Criteria

- identical supported values produce no change;
- a changed classification is detected;
- each numeric score dimension detects changes independently;
- current price detects changes;
- support/resistance detect changes;
- missing-to-present optional price fields are detected as changes;
- present-to-missing optional price fields are detected as changes;
- both-missing optional price fields produce no change;
- detected changes have deterministic ordering;
- identical snapshot IDs are rejected through the existing comparison boundary;
- cross-symbol snapshots are rejected through the existing comparison boundary;
- missing snapshots are reported through the existing comparison boundary;
- no fresh analysis is executed;
- no persistence mutation occurs;
- no significance threshold or notification delivery is performed.

## Scope Boundary

### In Scope

- application-level change detection;
- immutable change read model;
- deterministic change ordering;
- reuse of M22 comparison semantics;
- unit tests.

### Deferred

- significance thresholds;
- change severity;
- BUY/WATCH/HOLD/AVOID transition policy beyond descriptive detection;
- notification delivery;
- notification deduplication;
- alert throttling;
- watchlists;
- user-specific subscriptions;
- predictive interpretation;
- AI-generated interpretation;
- portfolio/trading behavior;
- persistence of detected changes.

## Design Gate Decision

**Accepted. Implementation is authorized for the M24 MVP defined above.**

The implementation should remain a pure/read-side application capability over the existing snapshot comparison boundary.
