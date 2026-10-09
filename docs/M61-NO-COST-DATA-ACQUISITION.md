# M61 — No-cost market-data acquisition path

**Decision:** use a no-payment discovery path first. Do not block engineering progress on a paid API or CSV order.
**Status:** exploratory tooling only; no market or financial source is accepted by this document.
**Updated:** 2026-10-09

## Constraints

- No paid subscriptions, API plans, or data purchases are required to run the exploratory probe below.
- A free endpoint is not automatically a legally reusable dataset. Source terms, retention, research use, and redistribution must be reviewed independently.
- The probe cannot supply point-in-time financial statements. Market bars and financial snapshots remain separate evidence tracks.
- Do not use a candidate response to claim a profitable strategy, accepted M61 dataset, or production-ready analytics.

## First path: Yahoo chart endpoint (diagnostic only)

The repository already depends on `yfinance`, and Yahoo chart history can be queried without a paid Yahoo Finance Gold CSV download flow. The new probe uses the public chart endpoint directly so it can preserve exact response bytes and checksums when the operator explicitly opts in.

The tool:
- checks the fixed ten-symbol cohort using `.CA` ticker candidates;
- requests daily observations from 2019-01-01 through 2025-12-31, including dividend/split event metadata;
- records source timezone and refuses to normalize dates if timezone metadata is missing or invalid;
- keeps raw close and adjusted close separate;
- validates OHLCV, duplicates, ordering, the 252-session warm-up, and 2021–2025 calendar-year coverage;
- records a response checksum and exact byte count;
- defaults to not persisting source responses; `--preserve-raw` is an explicit local opt-in that writes exact JSON bytes plus a normalized candidate CSV;
- always labels output `CANDIDATE_ONLY`, marks terms unverified, and forbids Strategy v0 eligibility.

### PowerShell

From the repository root:

```powershell
python -m tools.m61_free_market_probe --output-dir .\artifacts\m61-free-probe
```

This runs a non-persisting probe and writes only the report. To explicitly preserve the responses and candidate CSVs locally for inspection:

```powershell
python -m tools.m61_free_market_probe --output-dir .\artifacts\m61-free-probe --preserve-raw
```

The output directory must be empty or absent. The tool refuses to overwrite a non-empty evidence directory.

## Second path: EGID/EGX public feed

The public EGID Swagger UI lists date-range and symbol-history operations. That makes it a worthwhile no-cost source to test next, but the exact request/response schema, historical depth, reproducibility, and storage/use rights are still unverified. Do not write an adapter from endpoint names alone and do not infer that an endpoint is free for archival use merely because Swagger is public.

Reference: https://ticker.egidegypt.com/index.html

## Financial evidence without a paid vendor

Use dated issuer/EGX disclosure documents and issuer investor-relations archives as candidate evidence. For each value, retain the document URL/reference, period end, public availability date, statement type, currency/unit, revision status, and source checksum when retention is permitted. A period-end date is not a substitute for `available_at`. This is a bounded manual-evidence path, not a claim that all ten stocks already have complete point-in-time coverage.

## Acceptance gate remains closed

The no-cost path is allowed to produce candidate artifacts and validation findings, but the accepted dataset still requires:
1. complete cohort and 252-session warm-up coverage;
2. no unresolved invalid bars, duplicates, identity mismatches, or unexplained gaps;
3. explicit adjustment/corporate-action semantics;
4. source and retention/use rights reviewed against the actual intended use;
5. point-in-time financial snapshots with defensible availability dates;
6. immutable artifacts, checksums, transformation manifest, and reproducible Strategy v0 evaluation.

If free sources cannot satisfy a gate, record the exact gap and exclude that claim or strategy input. Do not fabricate missing observations or silently upgrade a candidate to accepted.
