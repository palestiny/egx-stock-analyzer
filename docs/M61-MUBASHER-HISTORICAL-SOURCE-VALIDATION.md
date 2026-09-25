# M61 — Mubasher Historical Source Validation

**Status:** Candidate source; **NOT ACCEPTED** for the M61 production dataset.
**Updated:** 2026-09-24

## Purpose

Record the evidence found for Mubasher as a possible historical EGX OHLCV acquisition source without promoting it into the production/backtest dataset boundary.

## Evidence found

### Current EGX prices

Mubasher exposes a public EGX stock-prices page with price, change, turnover, volume, open, high, and low fields. This establishes current-market data exposure, but current data is not sufficient for M61 historical evaluation.

Reference: https://english.mubasher.info/countries/eg/stock-prices

### Historical API path

An independently published implementation in the Bhidy/financehub-api project contains a Mubasher-backed historical loader using:

`https://english.mubasher.info/api/symbol/a/EGX-{SYMBOL}/history?type=full`

The implementation expects a JSON structure containing `data.data` and maps the following fields:

- `t` → date
- `o` → open
- `h` → high
- `l` → low
- `c` → close
- `a` → adjusted close
- `v` → volume
- `ch` → change percentage

The same implementation obtains EGX symbols from a Mubasher screener endpoint and normalizes symbol values before requesting historical data.

Evidence reference: https://huggingface.co/spaces/Bhidy/financehub-api/blob/2973dec03f3f71e37306e286334dd0feaa03bf17/data_pipeline/market_loader.py

A dated commit also shows the same historical endpoint and response mapping in the source implementation:
https://huggingface.co/spaces/Bhidy/financehub-api/commit/4e0cd9d9cdf10dc5d0976f3bc25345e67f6f6f24

## What this proves

The evidence is strong enough to move Mubasher from an unspecified provider idea to a **concrete historical-source candidate** with a documented endpoint shape and OHLCV field mapping.

It does **not** prove that the endpoint is currently reachable from our acquisition environment, that `type=full` guarantees complete 2021–2025 history, or that the endpoint can be used reproducibly and legally for our frozen M61 dataset.

## Required validation before acceptance

1. Live controlled request for at least one cohort symbol (EGAL first).
2. Preserve the raw response unchanged with acquisition timestamp.
3. Verify the exact date range returned and whether pagination/range parameters are required.
4. Verify OHLCV completeness, duplicate behavior, ordering, nulls, and date semantics.
5. Verify the 252-observation warm-up requirement.
6. Repeat for all ten M61 cohort symbols:
   COMI, EGAL, SWDY, ETEL, EAST, TMGH, PHDC, FWRY, EFID, HRHO.
7. Establish source-symbol → internal Stock mapping and identify symbol changes.
8. Determine whether `c` and `a` represent raw/adjusted conventions and document the corporate-action policy before transformation.
9. Perform an independent cross-check on sampled dates/symbols.
10. Establish licensing/usage rights for preservation and internal backtesting.
11. Only after all checks pass, create the immutable raw/transformed artifacts and manifest required by DEC-130.

## Current decision

**Mubasher remains NOT ACCEPTED.**

No Mubasher response has been inserted into the production historical dataset, and no Strategy v0 result may depend on Mubasher data until the acceptance procedure passes.

## Important boundary

A third-party implementation calling an endpoint is evidence of historical API usage, not proof of current availability, completeness, provenance, or redistribution rights. Those properties must be independently validated for this project.
