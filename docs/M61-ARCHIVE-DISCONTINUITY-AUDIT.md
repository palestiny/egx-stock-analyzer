# M61 Archive Price-Discontinuity Audit

This standard-library-only helper flags large close-to-close moves or overnight gaps in the normalized historical OHLCV archive. It complements the forward-return diagnostic by surfacing bars that may need source and corporate-action review.

## Run locally

```powershell
python tools/m61_archive_discontinuity_audit.py --input data/normalized/yahoo/daily_prices_ohlc_validated.csv.gz --output artifacts/m61-discontinuity-audit.json
```

The default threshold is an absolute move of 20% (0.20 as a fraction). Override it with `--threshold 0.15` if a more sensitive review is required.

## Output

The JSON report includes:
- usable unique row and symbol counts;
- rejected and duplicate-row counts;
- each flagged symbol/date, previous close, current OHLCV, close-to-close change, and overnight gap;
- flag counts by symbol; and
- explicit limitations.

## Interpretation rules

- A flag is a review candidate, **not proof of bad data**. Real price moves, corporate actions, source conventions, or date/session issues can all produce large discontinuities.
- The tool does not adjust, remove, or repair prices.
- The report does not independently validate data-provider rights, completeness, symbol mapping, or corporate-action treatment.
- Review flagged observations against authoritative exchange/company announcements and a second source before using affected periods in strategy validation.
- This tool is a data-quality aid only; it does not alter production opportunity ranking.
