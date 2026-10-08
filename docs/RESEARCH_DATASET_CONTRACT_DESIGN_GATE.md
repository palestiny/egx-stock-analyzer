# Research Dataset Contract & Evaluation Semantics — Design Gate

**Status:** Proposed implementation boundary
**Date:** 2026-10-07
**Repository:** palestiny/egx-stock-analyzer

## Objective

Define the minimum canonical contract required for historical strategy research before implementing a backtesting engine.

The contract must make dataset provenance, temporal ordering, execution timing, data quality, and evaluation semantics explicit so later research cannot silently introduce look-ahead bias or misleading performance claims.

## Scope

This gate covers canonical historical market bars; source and dataset provenance; timestamp and ordering semantics; market-session semantics; data-quality classification; research eligibility; execution/fill semantics; same-bar target/invalidation ambiguity; fees and slippage; corporate-action/price-adjustment policy; deterministic reproducibility metadata; and the boundary between descriptive track record and backtest evidence.

This gate does not authorize a live data provider, broker execution, or performance claims from current M61 acquisition work.

## Canonical Historical Bar Contract

A research bar contains normalized symbol, timeframe, open/high/low/close, volume, source timestamp, ingestion timestamp, source/provider identity, dataset/version identity, and adjustment status.

Prices and volume are numeric values; timestamps must be timezone-aware. The research layer must not infer missing values from neighboring bars.

## Temporal Semantics

At evaluation time T, a strategy may use only information whose source timestamp is at or before T. A signal generated from bar T cannot consume any future bar.

Bars for one symbol/timeframe are evaluated in ascending source timestamp order. Duplicate timestamps are not silently accepted. Out-of-order data is invalid for deterministic research until normalized.

The dataset must identify the market/session convention used by its bars. A provider adapter may map provider timestamps into the canonical market timezone, but the strategy engine must not guess the timezone.

## Data Quality

Research input is classified as VALID, MISSING, PARTIAL, DUPLICATE, CONFLICT, or STALE.

Only VALID observations are eligible for ordinary deterministic evaluation. A gap is not automatically a zero-return observation.

## Execution Semantics

The initial supported fill model is NEXT_OPEN: signal decision uses information available at bar T; entry occurs at the next eligible bar open; if the next bar is unavailable, the signal remains unevaluated rather than being filled using future or synthetic information.

Future execution models such as close, limit, or stop fills require explicit gap and trigger rules.

## Same-Bar Ambiguity

With OHLCV-only data, a bar can touch both target and invalidation without revealing which happened first. The default conservative policy is INVALIDATION_FIRST. If both are touched in the same bar and no finer-grained evidence exists, evaluation records invalidation.

Higher-resolution data may use an explicitly verified event-ordering policy.

## Costs

Research evaluation supports explicit commission/fees and slippage. Defaults must never be silently assumed when reporting performance. Cost configuration belongs to evaluation configuration and is included in reproducibility metadata.

## Price Adjustment

Adjusted and unadjusted prices are not interchangeable. A dataset must declare its adjustment policy. A research run must reject mixed adjustment states for the same evaluation series unless a dedicated corporate-action transformation contract exists.

Corporate-action handling remains a future gate.

## Reproducibility

A research run is identified by dataset/version, provider/source, strategy ID/version, parameter snapshot, evaluator version, execution model, ambiguity policy, cost configuration, and adjustment policy.

The same inputs and versions must produce the same deterministic evaluation result.

## Evidence Boundary

SignalOutcomeRecord and track-record analytics describe outcomes recorded by the application. They are not a substitute for a historical backtest.

A backtest result may be treated as research evidence only when the dataset satisfies this contract, temporal eligibility is enforced, execution semantics are explicit, ambiguity policy is explicit, costs are explicit, provenance/version metadata is preserved, and deterministic tests cover the evaluator.

No real-EGX performance conclusion is authorized from synthetic fixtures.

## Acceptance Criteria

This gate is PASS when:
1. canonical research data objects exist;
2. invalid temporal/data-quality states are rejected deterministically;
3. execution and ambiguity policies are explicit types/contracts;
4. reproducibility metadata is represented;
5. tests cover future-data rejection, duplicate/out-of-order handling, next-open semantics, same-bar ambiguity, and cost configuration;
6. documentation clearly separates track record from backtest evidence.

Only after PASS should the backtesting engine be implemented.
