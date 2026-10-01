# DEC-133 — M61 Final Validation Gate

**Status:** Implemented — awaiting real evidence  
**Milestone:** M61 — Backtesting & Strategy Validation

## Purpose

Define the final acceptance boundary for M61 after the immutable ten-symbol dataset has been accepted and Strategy v0 has been evaluated.

This gate validates **research reproducibility and evidence completeness**. It does not declare a strategy profitable, unprofitable, or suitable for investment.

## Final Gate Inputs

An M61 final-evaluation package must contain:

1. An accepted immutable dataset manifest.
2. Market and point-in-time financial artifacts referenced by that manifest.
3. Raw-source evidence and checksums.
4. Cohort coverage for COMI, EGAL, SWDY, ETEL, EAST, TMGH, PHDC, FWRY, EFID, HRHO.
5. Evaluation window 2021-01-01 through 2025-12-31.
6. At least 252 pre-evaluation market observations per evaluated stock.
7. Explicit adjustment convention.
8. Explicit missing/suspension/symbol-change findings.
9. Explicit licensing/retention notes.
10. Deterministic Strategy v0 evaluation output.
11. Trade-level output linked to strategy id/version and dataset version.
12. Aggregate metrics derived from the trade-level output.
13. A reproducibility record proving that re-running the same dataset/version/configuration produces the same evaluation result.

## Acceptance Rules

The final gate is **PASS** only when every required evidence input exists, validates, and is internally consistent.

The gate does not apply a profitability threshold. Performance is reported as an observed result of the declared dataset, strategy version, configuration, costs, and slippage.

The gate must remain **BLOCKED** when real evidence is absent. Repository fixtures cannot satisfy the final gate.

## Required Sequence

`real acquisition → dataset acceptance → Strategy v0 evaluation → trade/aggregate review → reproducibility run → final gate`

## Current Boundary

The software-side final gate machinery may be merged and tested before external evidence exists. That does not change M61 status.

Current status remains:

**BLOCKED — real immutable historical evidence is required.**

Once evidence is available, the final gate is the last step; no architecture expansion is required merely to reach it.
