# Stock Regime & Risk Profile (Diagnostic)

## Purpose

This domain feature summarizes one stock's trailing daily-price behavior. It is a descriptive input for later API/UI work, not a buy/sell recommendation and not a market-wide crash score.

## Current rules

- Requires at least 50 ordered daily bars. Shorter history returns explicit `insufficient_data` states and null metrics.
- Trend is `uptrend` only when the latest close is above SMA20, SMA20 is above SMA50, and SMA20 is above the preceding 20-session SMA20. The inverse conditions define `downtrend`; all other cases are `sideways`.
- Realized volatility is the population standard deviation of simple close-to-close returns, annualized by the square root of 252 sessions.
- Volatility bands are low below 20%, moderate from 20% to below 40%, and high at 40% or above.
- Drawdown is latest close divided by the maximum close in the supplied window, minus one. It is not portfolio drawdown or intraday drawdown.

## Data and limitations

- The caller is responsible for supplying one stock, one timeframe, strictly chronological bars, and an appropriate trailing window.
- The analyzer rejects mixed stocks/timeframes, unordered or duplicate timestamps, and non-positive closing prices.
- No adjustment for dividends, splits, corporate actions, stale quotes, or data-provider quality is performed here.
- Volatility thresholds and moving-average rules are initial deterministic heuristics. They have not been calibrated or validated as a profitable strategy.
- This is stock-level only. A market-wide Crash Radar requires a defined symbol universe, common observation dates, coverage rules, and explicit missing-data handling.

## Validation

Deterministic tests cover rising, falling, flat, insufficient, unordered, and mixed-stock inputs. CI is the verification gate; do not treat the feature as integrated into API/UI until a separate integration change is reviewed.
