# M61 Free Historical Data Source Reassessment — 2026-10-20

## Purpose

Reassess no-cost paths for obtaining a real EGX daily-history artifact for the M61 Strategy v0 evaluation, without weakening the existing data acceptance gate.

## Current verified baseline

- Yahoo Finance candidates were rejected: the previous bounded probe identified mutual-fund instrument metadata and repeated OHLC/invalid-value findings. HTTP success and long coverage do not establish valid EGX equity data.
- The anonymous EGID history request returned HTTP 401. The public Swagger describes history endpoints, but public documentation is not proof of anonymous access or permission to retain and use the data.
- A deterministic synthetic dataset-to-backtest test passed. It validates software wiring only and must not be represented as historical strategy performance.
- EGX.news currently advertises full daily historical bars at USD 1 per stock; this is not a no-cost option.
- The EGXLytics/egxpy route is described by secondary documentation as using TradingView-backed tvDatafeed. Do not adopt it for automated backtesting without explicit authorization covering automated collection, local retention, and algorithmic research use.

## Newly identified candidate: EGXAPI

The public EGXAPI pricing page currently claims a free account includes full historical bars and a REST/WebSocket API:
https://www.egxapi.com/pricing/

This is a candidate to investigate, not an accepted source. The pricing page alone does not prove:
- that historical COMI bars can actually be retrieved for the required 2019-01-01 through 2025-12-31 window;
- that OHLCV is complete, correctly mapped to EGX instruments, and stable across corporate actions;
- that raw historical data may be retained locally and used for automated research/backtesting;
- that the service is operationally and legally suitable for this project.

The repository's earlier research flagged uncertainty in the legal center. Recheck the actual current Terms, Privacy, and any data-provider disclosures before collecting or persisting any price rows. Do not infer permission from a free price tier.

## Next bounded verification sequence

1. Inspect current legal terms and identify the legal entity/provider, data source, retention rights, algorithmic/non-display use, redistribution restrictions, and any exchange licensing requirements.
2. If the terms are sufficiently explicit, create an isolated metadata/contract probe first. Do not write market prices to disk during this stage.
3. Request or retrieve a small COMI history sample only after access and intended-use permissions are established.
4. Record HTTP status, schema, symbol identity, returned date range, row count, timezone, adjustment/corporate-action fields, and response checksum. Keep secrets out of logs.
5. If the contract and access checks pass, acquire the required COMI range and run the existing evidence intake. Do not expand to the ten-symbol cohort until COMI passes.
6. Market bars alone do not satisfy M61: point-in-time financial snapshots with publication/availability dates remain a separate acceptance requirement.

## Hard constraints

- No synthetic data in strategy-performance reporting.
- No unlicensed TradingView-backed extraction.
- No automatic acceptance based only on row count, HTTP 200, or superficially valid OHLC.
- No fabricated missing sessions, prices, corporate actions, or financial publication dates.
- If access or rights cannot be established, report M61 as blocked by source access rather than weakening validation.

## Decision

**EGXAPI is the next no-cost candidate to verify, not an approved provider.** No real-market performance result is authorized until both market and point-in-time fundamental evidence pass the existing acceptance gate.
