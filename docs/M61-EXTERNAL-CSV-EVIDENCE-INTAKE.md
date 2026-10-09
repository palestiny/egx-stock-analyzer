# M61 — External CSV Evidence Intake

## Purpose

Use `tools/m61_vendor_csv_evidence_inspector.py` immediately after downloading a provider's daily OHLCV CSV. It is a pre-ingestion report only: it does not modify the source file, normalize or adjust prices, infer EGX holidays, certify licensing, or accept a dataset.

## Example

```powershell
python -m tools.m61_vendor_csv_evidence_inspector .\COMI.csv --symbol COMI --provider "EGX.news" --source-reference "provider order/delivery reference" --report .\COMI-inspection.json
```

The report records the exact raw-file SHA-256, byte count, row counts, detected headers, coverage, duplicate/out-of-order dates, OHLCV validation findings, and the remaining acceptance gates. Keep the original downloaded artifact unchanged.

A report with zero row errors and validation findings is still only `CANDIDATE_ONLY`. The user must separately verify retention/use terms and price-adjustment semantics, reconcile missing sessions and symbol identity, and acquire point-in-time financial snapshots with publication/availability dates. Do not use this report alone to create an accepted M61 manifest or make strategy-performance claims.

## Build a canonical candidate package

After a real market CSV and a separately sourced point-in-time financial snapshot CSV are available, use `tools/m61_build_candidate_dataset.py` to preserve the source bytes and create the schema-v3 candidate package. The financial input must already use exactly these columns: `period_end,available_at,revenue,net_income,current_assets,current_liabilities,revision`; dates are ISO calendar dates, and `available_at` must not precede `period_end`.

Example PowerShell invocation (replace the stock UUID, source references, dates, and license notes with verified values; the output directory must not already exist):

```powershell
python -m tools.m61_build_candidate_dataset `
  --market-csv .\COMI.csv `
  --financial-csv .\COMI-financial-snapshots.csv `
  --output-dir .\m61-candidates\COMI-v1 `
  --symbol COMI `
  --stock-id "<COMI internal Stock UUID>" `
  --dataset-version "candidate-2026-10-09-001" `
  --market-provider "<market provider>" `
  --market-source-reference "<delivery URL or order reference>" `
  --market-acquired-at "2026-10-09T12:00:00+03:00" `
  --market-licensing-notes "status=unverified; evidence_reference=unknown; permitted_uses=; redistribution=prohibited" `
  --corporate-action-convention "raw-as-published" `
  --financial-provider "<financial source>" `
  --financial-source-reference "<delivery URL or order reference>" `
  --financial-acquired-at "2026-10-09T12:00:00+03:00" `
  --financial-licensing-notes "status=unverified; evidence_reference=unknown; permitted_uses=; redistribution=prohibited"
```

The tool preserves both inputs under `raw/`, records SHA-256 hashes, normalizes daily session dates to Cairo, validates the generated canonical artifacts, and emits `candidate_report.json` with `CANDIDATE_ONLY`. It does not adjust prices or approve licensing. The example intentionally uses unverified licensing notes; do not change them to `status=verified` unless the referenced terms were actually reviewed.

Run the authoritative intake gate separately:

```powershell
python -m tools.m61_comi_evidence_intake .\m61-candidates\COMI-v1
```

The intake must reject candidates with insufficient warm-up, missing point-in-time financial availability years, or unverified licensing. A candidate package is not a dataset acceptance decision.

## Current acquisition blocker

EGX.news publicly advertises full daily historical OHLCV CSV for $1 per stock. For the initial ten-symbol cohort, that is a stated market-data price of $10 before any taxes/fees, subject to checkout confirmation and licensing terms. This quote does not cover point-in-time financial snapshots. No purchase or source acceptance is implied by this document.

Source: https://www.egx.news/en/our-data
