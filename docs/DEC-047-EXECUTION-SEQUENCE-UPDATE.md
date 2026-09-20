# DEC-047 — Execution Sequence Update

**Status:** Accepted  
**Date:** 2026-09-15

## Decision

The roadmap execution order is updated to reflect the work that has actually been completed without changing the architecture or previously accepted milestone designs.

The project has completed the following additional vertical slices:

- M8 — Backtesting MVP
- M11 — Reporting & Alerts MVP
- M9 — Data Quality MVP
- M3 — Data Acquisition MVP

The next planned milestone is M10 — Automation.

## Why the Sequence Changed

The original roadmap intentionally deferred Data Quality and Data Acquisition until the analytical core was understood. During implementation, M8 and M11 were completed before the reliability/acquisition track was resumed. This did not change the core domain model or invalidate the accepted M8/M9/M11 designs.

M9 was then implemented before M3 so that externally acquired observations could pass through the already-defined Data Quality boundary before becoming `PriceBar` instances.

M3 was completed only after the provider-neutral acquisition boundary, raw observation model, quality assessment, and raw-observation-to-PriceBar conversion were defined.

## Current Acquisition Boundary

```text
Application
    ↓
MarketDataProvider
    ↓
Yahoo Finance Adapter
    ↓
RawPriceBarObservation
    ↓
DataQualityAssessor
    ↓
VALID observations
    ↓
PriceBarFactory
    ↓
PriceBar
    ↓
Analysis
```

## Important Constraint

This decision does **not** make Yahoo Finance the permanent production provider. Yahoo Finance remains a development/integration adapter behind the provider boundary.

It also does not weaken Data Quality rules. During the live COMI smoke test, Yahoo returned observations that violated OHLC consistency. Those observations were correctly classified as `INVALID` and were excluded from `PriceBar` creation. The smoke test was updated to verify this boundary rather than requiring every external observation to be valid.

## Consequence

The roadmap now reflects the actual completed state. Future sequence changes must still be deliberate and documented rather than introduced implicitly.
