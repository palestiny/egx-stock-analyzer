# M61 — External CSV Evidence Intake

## Purpose

Use `tools/m61_vendor_csv_evidence_inspector.py` immediately after downloading a provider's daily OHLCV CSV. It is a pre-ingestion report only: it does not modify the source file, normalize or adjust prices, infer EGX holidays, certify licensing, or accept a dataset.

## Example

```powershell
python -m tools.m61_vendor_csv_evidence_inspector .\COMI.csv --symbol COMI --provider "EGX.news" --source-reference "provider order/delivery reference" --report .\COMI-inspection.json
```

The report records the exact raw-file SHA-256, byte count, row counts, detected headers, coverage, duplicate/out-of-order dates, OHLCV validation findings, and the remaining acceptance gates. Keep the original downloaded artifact unchanged.

A report with zero row errors and validation findings is still only `CANDIDATE_ONLY`. The user must separately verify retention/use terms and price-adjustment semantics, reconcile missing sessions and symbol identity, and acquire point-in-time financial snapshots with publication/availability dates. Do not use this report alone to create an accepted M61 manifest or make strategy-performance claims.

## Current acquisition blocker

EGX.news publicly advertises full daily historical OHLCV CSV for $1 per stock. For the initial ten-symbol cohort, that is a stated market-data price of $10 before any taxes/fees, subject to checkout confirmation and licensing terms. This quote does not cover point-in-time financial snapshots. No purchase or source acceptance is implied by this document.

Source: https://www.egx.news/en/our-data
