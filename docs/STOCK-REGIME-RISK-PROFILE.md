# Stock Regime & Risk Profile (Diagnostic)

## Purpose

This feature summarizes one stock's trailing daily-price behavior. It is descriptive, not a buy/sell recommendation and not a market-wide crash score.

## Analysis rules

- Requires at least 50 valid ordered daily bars. Shorter history returns explicit `insufficient_data` states and null metrics.
- Trend is `uptrend` only when the latest close is above SMA20, SMA20 is above SMA50, and SMA20 is above the preceding 20-session SMA20. The inverse conditions define `downtrend`; all other cases are `sideways`.
- Realized volatility is the population standard deviation of simple close-to-close returns, annualized by the square root of 252 sessions.
- Volatility bands are low below 20%, moderate from 20% to below 40%, and high at 40% or above.
- Drawdown is latest close divided by the maximum close in the supplied window, minus one. It is not portfolio drawdown or intraday drawdown.

## API integration

The authenticated endpoint `GET /api/v1/market-intelligence/regime/{symbol}` is wired through the application composition root when a stock catalog and market-data provider are configured. It requests approximately 550 calendar days of daily history from the configured Yahoo Finance adapter, assesses raw observations, excludes observations that are not marked `valid`, then calculates the profile.

The response includes the requested date range, source label, latest observation date, valid/excluded counts, trend, volatility, SMA20/SMA50, annualized realized volatility, drawdown, reasons, and `is_trading_signal: false`. Unknown symbols return 404; missing endpoint configuration returns 503. The source label identifies the configured adapter, not independent verification of Yahoo's coverage or correctness.

## Data and limitations

- Provider access occurs when the endpoint is called; it is not a guarantee of real-time quotes. The latest observation date must be checked before interpreting results.
- Invalid or suspect observations are excluded using the existing quality assessor. Gaps in the source history are not independently proven to be complete market-session coverage by this endpoint.
- No adjustment for dividends, splits, corporate actions, or stale quotes is performed here.
- Volatility thresholds and moving-average rules are initial deterministic heuristics. They have not been calibrated or validated as a profitable strategy.
- This is stock-level only. A market-wide Crash Radar requires a defined symbol universe, common observation dates, coverage rules, and explicit missing-data handling.

## Validation

Deterministic domain and application tests cover trend calculations, insufficient history, data-quality exclusions, provenance, and unknown symbols. Passing CI validates software behavior, not investment performance.
