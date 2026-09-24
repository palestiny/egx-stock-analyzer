# M61 — Historical Dataset Acquisition Status

**Status:** Acquisition boundary accepted; real dataset not yet accepted for evaluation.  
**Decision:** DEC-130  
**Updated:** 2026-09-24

## Purpose

This document records the concrete acquisition state after DEC-130. It is an operational checkpoint, not a substitute for the immutable dataset manifest.

## Evaluation cohort

The first bounded cohort is:

- COMI
- EGAL
- SWDY
- ETEL
- EAST
- TMGH
- PHDC
- FWRY
- EFID
- HRHO

Evaluation window: **2021-01-01 through 2025-12-31**.

Warm-up requirement: **252 prior trading observations** before the first evaluated decision date.

## Required evidence package

An accepted dataset version must contain, or point to preserved immutable artifacts containing:

1. Daily market OHLCV for the cohort and required warm-up period.
2. Point-in-time financial snapshots required by the production fundamental-analysis boundary.
3. Source/provider identity for every artifact.
4. Acquisition timestamp.
5. Source symbol to internal Stock identity mapping.
6. Coverage start/end and row counts.
7. Declared corporate-action convention.
8. Missing/suspension findings.
9. Symbol-change findings and evidence.
10. Exclusions and explicit reasons.
11. SHA-256 checksums.
12. Licensing/usage notes.

## Source status

### Primary market provenance — EGX

The Egyptian Exchange public site exposes market-watch data, listed-company information, disclosures, financial-statements areas, and index information. The site is therefore the designated primary provenance source where the required historical artifact can be obtained and preserved.

Current verification does **not** establish that the complete 2021–2025 daily OHLCV artifact for all ten symbols is publicly downloadable in a reproducible bulk form. This remains an acquisition task, not an assumption.

Reference: https://beta.egx.com.eg/en/market/market-watch

### Secondary market cross-check — Yahoo Finance

Yahoo Finance documents historical price data and supports custom historical ranges. Its current help documentation states that CSV download requires Yahoo Finance Gold and that some instruments do not expose downloads because of licensing restrictions. Yahoo also states that information supplied through the service must not be redistributed.

Therefore Yahoo is retained as a **secondary validation/cross-check source**, not as an automatically redistributed dataset source.

References:
- https://help.yahoo.com/kb/sln2311.html
- https://help.yahoo.com/kb/SLN2310.html

### Primary financial provenance — EGX disclosures / financial statements

Historical financial evidence must come from EGX-published disclosures or financial-statement publications where the publication/availability date can be established. A later-known value without a defensible point-in-time availability date is not eligible for Strategy v0 evaluation.

## Acquisition acceptance procedure

For each source artifact:

1. Preserve the original source artifact without modification.
2. Record source URL/reference, acquisition timestamp, provider, and source symbol.
3. Record the mapping to the internal stock identity.
4. Record the artifact's raw checksum.
5. Transform only into the accepted M61 CSV schema.
6. Record transformation rules and corporate-action convention.
7. Compute the transformed artifact checksum.
8. Validate row count, ordering, duplicates, timestamps, decimal representation, and coverage.
9. Validate missing/suspension periods without forward-filling.
10. Validate financial available_at against every historical decision date.
11. Freeze the manifest and artifact checksums.
12. Only then authorize Strategy v0 evaluation against that dataset version.

## Current blocker

The software-side dataset contract and loader are already implemented and protected by deterministic fixtures. The remaining blocker is **real historical evidence acquisition with acceptable provenance and usage rights**.

We must not manufacture or silently substitute historical data merely to unblock the backtest. A dataset version becomes evaluable only after the evidence package above passes validation.

## Next executable step

Acquire the first real market and financial source artifacts for the ten-symbol cohort, preserve them outside Git when their size or licensing requires it, and produce the immutable M61 manifest. Then run the repository's existing historical-dataset validation before any Strategy v0 evaluation.

## Non-goals

This checkpoint does not:

- change Strategy v0;
- change backtest semantics;
- add ranking or optimization;
- add live trading;
- silently normalize corporate actions;
- create a new persistence model;
- claim full-EGX historical validity.
