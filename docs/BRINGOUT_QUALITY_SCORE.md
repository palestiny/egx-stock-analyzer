# Breakout Quality Score (Diagnostic)

## Scope
The existing authenticated endpoint `GET /api/v1/market-intelligence/breakouts` detects candidate and confirmed levels from saved analysis snapshots. This document describes the evidence-quality score used by that feature.

## Score components
- **Trigger status:** 30 points when price has crossed the reference level; 20 points when it is only a candidate near the level.
- **Trend alignment:** 25 points when the existing technical trend agrees with the breakout direction.
- **Volume confirmation:** 25 points when the saved analysis reports above-average volume.
- **Underlying stock-quality contribution:** up to 20 points, proportional to the existing 0–100 stock-quality score.

The result is capped at 100. The score ranks evidence completeness, not expected return or probability of success. Candidate and confirmed are status labels; neither is a forecast.

## Data caveats
The scanner uses the latest saved analysis result, not necessarily a live quote. The score cannot correct stale inputs or unadjusted corporate actions. A confirmed threshold crossing can still reverse; no out-of-sample backtest has established predictive value for this score. Treat it as an explainability aid, not a standalone buy/sell recommendation.

## Verification
The implementation's current CI run passed all five workflow jobs on 20 October 2026. Passing software tests validates implementation behavior, not investment performance.
