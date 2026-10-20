# Market Breadth & Stress Pulse

## Purpose

Summarize the directional state of a caller-supplied EGX symbol universe from the latest saved analysis snapshots. This adds market-level context without requiring a new historical-data acquisition project.

## API

Authenticated endpoint: `GET /api/v1/market-intelligence/breadth-stress?symbols=COMI,EGAL,TMGH`

The response includes requested/analyzed counts, missing symbols, coverage, uptrend/downtrend counts, positive/negative momentum counts, above-average-volume count, bullish breadth, bearish pressure, and a 0–100 heuristic stress score.

## Stress score

- 50% weight: share of analyzed symbols classified as downtrend.
- 40% weight: share with negative momentum.
- 10% weight: share with negative momentum and above-average volume.
- Levels: calm (0–24), mixed (25–49), elevated (50–74), high (75–100).

Bullish breadth is the average of uptrend share and positive-momentum share. Bearish pressure is the average of downtrend share and negative-momentum share. Percentages and scores use only symbols with a saved analysis; coverage separately exposes missing symbols.

## Limitations

This is a transparent heuristic, not a statistically calibrated crash predictor or trading signal. It summarizes saved analysis snapshots, which may be stale, and does not independently validate quotes, corporate actions, or the completeness of the EGX universe. The caller must pass a deliberate symbol universe; do not describe a partial list as the whole market.
