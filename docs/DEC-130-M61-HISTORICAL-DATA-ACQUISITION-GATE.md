# DEC-130 — M61 Historical Dataset Acquisition & Provenance Design Gate

**Status:** Proposed  
**Date:** 2026-09-24  
**Milestone:** M61 — Backtesting & Strategy Validation

## Purpose

DEC-129 established the physical dataset contract and loader. The remaining M61 risk is whether the real historical evidence used for Strategy v0 is sufficiently complete, reproducible, point-in-time safe, and provenance traceable.

## Problem

A deterministic backtest can still be invalid if market history has gaps or survivorship bias, financial values use later knowledge, revisions are silently replaced, corporate-action conventions are mixed, or the source cannot be identified and reproduced.

The dataset is therefore part of the evidence boundary of the backtest.

## Scope

In scope: source selection criteria, market-history coverage, point-in-time financial-history requirements, provenance, symbol mapping, missing-data policy, corporate-action treatment, survivorship-bias controls, and acceptance checks before Strategy v0 evaluation.

Out of scope: changing Strategy v0, changing backtest execution semantics, portfolio optimization, live provider failover, automated daily dataset acquisition, and trading execution.

## Proposed Decisions

### P1 — Immutable Evidence Snapshot

Once a real dataset version is accepted for evaluation, its files, manifest, source metadata, and checksums are immutable. A later refresh creates a new dataset version.

### P2 — Separate Market and Financial Provenance

Market observations and financial snapshots may come from different providers. Each artifact records provider/source, acquisition timestamp, source symbol, internal identity mapping, coverage, transformations, and licensing/usage notes where applicable.

### P3 — Point-in-Time Financial Evidence Is Mandatory

A financial record may be used for a decision date only when its available_at value is on or before that decision date. Later restatements must not overwrite earlier historical evidence unless modeled as a later revision.

### P4 — No Silent Corporate-Action Normalization

The dataset must declare whether OHLC values are raw or adjusted. One consistent convention must be used across an evaluation, and any transformation must be recorded and tested.

### P5 — Survivorship Bias Must Be Explicit

The evaluation universe must not silently mean stocks that exist today. Historical membership methodology and limitations must be documented.

### P6 — Missing Data Is Evidence

Missing observations, unavailable financial snapshots, suspensions, and symbol changes must be represented or reported. The acquisition process must not silently forward-fill values to manufacture coverage.

## Source Selection Criteria

### Market data

A candidate source must provide daily OHLCV, stable historical dates, sufficient coverage, identifiable symbol mapping, a documented adjustment convention, repeatable acquisition or preserved source artifacts, and acceptable usage rights.

### Financial data

A candidate source must provide period-end date, publication/availability date suitable for point-in-time use, revision identity when available, required fields for the production fundamental-analysis boundary, stable identity mapping, and reproducible provenance.

Convenience alone does not make a source authoritative.

## Initial Source Research

Current evidence shows multiple external EGX market-data sources exist:

- Yahoo Finance exposes historical daily data for EGX instruments such as GRCA.CA and the ^CASE30 index. citeturn0search13turn0search11
- StockAnalysis exposes historical daily data for EGX:EGAL and identifies S&P Global Market Intelligence as its data source. citeturn0search7
- EGX.news advertises downloadable historical daily EGX data for listed companies, including CSV delivery. citeturn0search5

This establishes candidate sources, not complete satisfaction of the M61 market plus financial point-in-time contract.

Yahoo's official documentation notes that historical-data downloads depend on instrument licensing and currently require Yahoo Finance Gold for CSV download. citeturn0search4

Therefore source acceptance requires a concrete coverage and provenance test.

## Proposed First Evaluation Scope

The first real evaluation should be deliberately bounded rather than claiming full-market validation. It must use a fixed symbol list, explicit start/end dates, sufficient warm-up history, documented exclusions, and an immutable dataset manifest.

A representative EGX subset may validate the backtest boundary before full-market expansion. This is an evaluation scope decision, not a claim that the strategy is validated for the entire EGX.

## Acceptance Checklist

Before Strategy v0 results are treated as historical evidence, verify:

1. Dataset manifest passes integrity checks.
2. Market and financial artifact counts/checksums match.
3. Required fields are complete or explicitly classified as unavailable.
4. Market timestamps are deterministic and timezone-safe.
5. Financial available_at never precedes period_end.
6. Point-in-time lookup never returns a record newer than the decision date.
7. Symbol mappings are explicit and deterministic.
8. Corporate-action convention is consistent and documented.
9. Missing/suspended periods are reported rather than fabricated.
10. Evaluation universe and membership limitations are documented.
11. Source/provider and acquisition provenance are recorded.
12. Dataset version is immutable once evaluation begins.
13. Reloading the same dataset reproduces identical inputs.
14. Strategy v0 runs through the existing production analysis boundary.
15. No future information enters a historical decision.

## Decisions Required Before Full Evaluation

The gate should be accepted only after committing to a bounded initial universe, concrete market-data source, concrete point-in-time financial source, source/licensing notes, evaluation period, warm-up requirement, and handling for symbol changes, suspensions, and missing observations.

Until then, fixture/infrastructure work may continue, but production Strategy v0 evaluation remains gated.

## Consequences

This gate prevents a technically correct backtester from being mistaken for scientifically valid historical evidence. It also keeps the dataset replaceable: changing a provider creates a new dataset version rather than changing the backtesting engine semantics.
