# Stock Regime & Risk Profile (Diagnostic)

## Purpose

Summarize one stock's trailing daily-price behavior. This is descriptive, not a buy/sell recommendation or a market-wide crash score.

## Analysis rules

- Requires at least 50 valid ordered daily bars. Shorter history returns explicit `insufficient_data` states and null metrics.
- Trend requires close above SMA20, SMA20 above SMA50, and SMA20 rising versus the preceding 20-session SMA20. The inverse defines downtrend; other cases are sideways.
- Realized volatility is the population standard deviation of simple close-to-close returns, annualized by the square root of 252 sessions.
- Volatility bands: low below 20%, moderate from 20% to below 40%, high at 40% or above.
- Drawdown is latest close divided by the maximum close in the supplied window, minus one. It is not portfolio or intraday drawdown.

## API and data limitations

The authenticated endpoint `GET /api/v1/market-intelligence/regime/{symbol}` requests approximately 550 calendar days from the configured Yahoo Finance adapter when a stock catalog and market-data provider are configured. It assesses raw observations and excludes observations that are not marked valid.

The response includes requested dates, source label, latest observation date, valid/excluded counts, trend, volatility, SMA20/SMA50, annualized realized volatility, drawdown, reasons, and `is_trading_signal: false`.

- Provider access occurs when the endpoint is called; this is not a real-time quote guarantee. Check the latest observation date.
- Source label identifies the adapter, not independent verification of source coverage or correctness.
- Gaps in source history, corporate actions, dividends, splits, and stale quotes are not independently validated here.
- Rules and volatility thresholds are deterministic heuristics, not a calibrated profitable strategy.
- This is stock-level only; market-wide breadth needs a defined universe and explicit coverage rules.

Passing CI validates software behavior, not investment performance.
