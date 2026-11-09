# DEC-138 — Completed Daily OHLC Swing Opportunity Observation Semantics

**Status:** Accepted by owner
**Date:** 2026-11-07

## Context

The opportunity lifecycle requires deterministic target/invalidation evaluation against daily market observations. A daily close alone can hide an intraday range crossing, while OHLC data cannot reveal the order in which levels were touched within the same candle.

## Decision

1. Evaluate Swing opportunity target/invalidation transitions only from a **completed daily OHLC candle**. An incomplete/currently forming candle is ineligible.
2. A target is reached when the completed candle's **High is greater than or equal to the target level**.
3. An invalidation/stop level is reached when the completed candle's **Low is less than or equal to the invalidation level**.
4. If the same completed candle touches both the target and invalidation levels, record **invalidation first**. This is the conservative deterministic policy because OHLC does not establish intrabar price ordering.
5. Persist the source candle identity and timestamp, source/provider provenance, OHLC values, evaluation-policy version, and resulting transition/event identity so replay and audit can explain the result.
6. Reprocessing the same source candle must be idempotent. A later correction to source OHLC must not silently rewrite an already-recorded lifecycle event; it must follow an explicit correction/reconciliation path and retain the original evidence.

## Boundaries and unresolved items

- This decision does not define the EGX session calendar, provider-specific candle completion guarantees, freshness thresholds, or correction authority. Those remain separate data-eligibility gates.
- This decision does not define hypothetical entry-price basis, gap/slippage accounting, expiry duration, or revised-opportunity lineage.
- Daily OHLC monitoring is not intraday/live monitoring and does not imply broker execution or realized trade P&L.
- No signal-generation, scoring, target, or invalidation-level calculation is changed by this decision.
