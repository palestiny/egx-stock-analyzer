# Market Breadth & Stress Pulse

## Purpose

Summarize the directional state of a caller-supplied EGX symbol universe from the latest saved analysis snapshots. This adds market-level context without requiring a new historical-data acquisition project.

## API

Authenticated endpoint: `GET /api/v1/market-intelligence/breadth-stress?symbols=COMI,EGAL,TMGH`

The response includes requested/analyzed counts, missing symbols, coverage, uptrend/downtrend counts, positive/negative momentum counts, above-average-volume count, bullish breadth, bearish pressure, and a 0–100 heuristic stress score. It also exposes `stress_components`, which returns the count, analyzed-universe share, and weighted score contribution for each of the three existing components. This is an additive response extension; the formula and legacy score remain unchanged.

## Stress score

- 50% weight: share of analyzed symbols classified as downtrend.
- 40% weight: share with negative momentum.
- 10% weight: share with negative momentum and above-average volume.
- Levels: calm (0–24), mixed (25–49), elevated (50–74), high (75–100).

Bullish breadth is the average of uptrend share and positive-momentum share. Bearish pressure is the average of downtrend share and negative-momentum share. Percentages and scores use only symbols with a saved analysis; coverage separately exposes missing symbols.


## Evidence metadata (Crash Radar v2, first increment)

The breadth-stress response additionally reports:

- `analysis_dates_by_symbol`: each analyzed symbol mapped to its persisted analysis calendar date, or `null` when the saved record has no usable date.
- `undated_symbols`: analyzed symbols whose saved record has no usable date.
- `analysis_date_status`: `CONSISTENT` when every requested symbol is analyzed and all analyzed records share one known date; `MIXED` when all requested symbols are analyzed and known dates differ; `PARTIAL` when at least one requested symbol is missing, or when some analyzed records are dated and others are undated; `UNKNOWN` when every requested symbol has a saved analysis but none has a usable analysis date.
- `latest_analysis_date`: latest known date among analyzed records, or `null` when no date is known.
- `methodology_version`: currently `stress-heuristic-v1`.

These fields describe the evidence available to the calculation; they do not prove that underlying market prices are current. Dates are calendar dates, so timestamps are normalized to their date component. Missing symbols remain distinct from analyzed-but-undated symbols. The existing score and its denominator remain unchanged: score percentages use analyzed symbols only. No freshness threshold, minimum-coverage policy, score suppression, or alerting policy is implied by these metadata fields. The `stress_components` values make the existing formula auditable: downtrend contributes up to 50 points, negative momentum up to 40, and negative momentum with above-average volume up to 10. `weight_points` are displayed to two decimal places; the final `stress_score` is rounded to the nearest integer, so displayed component points may sum to the unrounded score rather than the integer score. With no analyzed records, component contributions are `null` rather than zero.

### Interpretation examples

- Two requested symbols, both analyzed on the same known date: `CONSISTENT`.
- All requested symbols analyzed, but their known dates differ: `MIXED`.
- At least one requested symbol has no saved analysis, or an analyzed record is undated while other dates are known: `PARTIAL`.
- No analyzed record has a usable date: `UNKNOWN`.

The status is evidence transparency, not a confidence rating or trading signal. Consumers should display coverage and date status alongside the score and should not label a caller-supplied subset as the full EGX market.

## Limitations

This is a transparent heuristic, not a statistically calibrated crash predictor or trading signal. It summarizes saved analysis snapshots, which may be stale, and does not independently validate quotes, corporate actions, or the completeness of the EGX universe. The caller must pass a deliberate symbol universe; do not describe a partial list as the whole market.
