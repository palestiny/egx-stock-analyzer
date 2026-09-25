# M61 — Mansa Markets Historical Source Validation

**Status:** Candidate; not accepted for the frozen M61 dataset.
**Updated:** 2026-09-25
**Decision boundary:** DEC-130

## Purpose

Validate whether Mansa Markets can supply the market OHLCV portion of the bounded M61 historical dataset without weakening provenance, reproducibility, or licensing requirements.

## Current documented capability

Mansa currently documents:

- EGX as a supported exchange.
- Per-stock daily history through `GET /api/v1/markets/exchanges/{exchange_code}/stocks/{ticker}/history`.
- Explicit `from`, `to`, `limit` (maximum 20,000), and `order` parameters.
- Daily `date`, `open`, `high`, `low`, `close`, `adj_close`, and `volume` fields, plus response metadata.
- Egypt historical depth back to 1995.
- Per-stock history as a Pro plan capability.
- A separate Fundamentals Suite, but the published material does not establish Egyptian point-in-time financial-snapshot coverage required by M61.

References:
- https://mansaapi.com/docs
- https://mansaapi.com/methodology

## Required authenticated probe

Do not place API keys in GitHub, documentation, commits, issues, logs, or chat.

For each M61 symbol:

`COMI, EGAL, SWDY, ETEL, EAST, TMGH, PHDC, FWRY, EFID, HRHO`

Probe:
- exchange: `EGX`
- requested period: 2020-01-01 through 2025-12-31
- order: `asc`
- limit: 20,000

The 2020 start intentionally includes more than the 2021-2025 evaluation window so the required warm-up can be measured from real observations rather than assumed.

## Probe evidence to preserve

For every symbol record outside Git where licensing requires it:

1. request parameters;
2. acquisition timestamp;
3. exact source symbol;
4. raw response artifact, if storage is permitted;
5. raw SHA-256;
6. response count;
7. first/last returned date;
8. duplicate-date findings;
9. missing-session findings;
10. null/invalid OHLCV findings;
11. price-unit semantics;
12. `close` vs `adj_close` behavior;
13. corporate-action observations;
14. mapping to the internal Stock identity.

## Acceptance gates

Mansa market data can proceed toward M61 dataset acceptance only if:

- all ten symbols resolve unambiguously;
- coverage supports the 252-observation warm-up plus 2021-2025 evaluation window;
- no unexplained gaps or duplicate observations remain;
- price-unit semantics are deterministic;
- corporate-action treatment is explicitly preserved as-published or transformed under a separately documented rule;
- raw-response preservation/replay is legally permitted for the intended research artifact;
- source/licensing terms permit the intended internal backtest storage and use;
- the transformed artifact passes the existing M61 dataset validator.

## Licensing boundary

Mansa's licensing documentation distinguishes application caching from redistribution. It explicitly requires API keys to remain confidential and distinguishes caching from building a stored copy of the provider dataset.

M61 must therefore obtain explicit confirmation before treating API responses as a long-lived immutable research archive. Internal research/backtesting storage is not assumed to be prohibited, but it is also not inferred to be permitted merely from API access.

Reference:
- https://mansaapi.com/licensing

## Financial-data boundary

Mansa documents a Fundamentals Suite with fiscal-period financial figures and source-document URLs. That does not establish the Egyptian point-in-time `available_at` evidence required by DEC-130.

Therefore Mansa market history and M61 financial snapshots remain separate acceptance gates.

## Decision

**Do not integrate Mansa into production yet.**

The next executable action is an authenticated ten-symbol probe if/when a valid Mansa key and permitted access are available. Until then, keep Mansa as a documented acquisition candidate and continue evaluating EGX.news / institutional alternatives for a legally storable frozen artifact.

No Strategy v0 behavior changes are authorized by this document.
