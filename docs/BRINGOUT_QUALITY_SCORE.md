# Breakout Quality Score (Diagnostic)

## Scope
The existing authenticated endpoint `GET /api/v1/market-intelligence/breakouts` already detects candidate/confirmed levels from saved analysis snapshots. This document defines an interpretable quality score for that existing feature.

## Proposed score
- Trigger status: 30 points if price has crossed the reference level; 20 points if it is only a candidate near the level.
- Trend alignment: 25 points when the existing technical trend agrees with the breakout direction.
- Volume confirmation: 25 points when the saved analysis reports above-average volume.
- Underlying stock-quality contribution: up to 20 points, proportional to the existing 0–100 stock-quality score.

The result is capped at 100. The score ranks evidence completeness, not expected return or probability of success. Candidate and confirmed are status labels; neither is a forecast.

## Data caveats
The scanner uses the latest saved analysis result, not necessarily a live quote. The score cannot correct stale inputs or unadjusted corporate actions. A confirmed threshold crossing can still reverse; no backtest validation has yet established predictive value for this score.
