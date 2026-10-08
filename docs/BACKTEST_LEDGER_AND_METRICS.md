# Backtest Ledger and Metric Semantics

The initial deterministic backtest runner records a single-symbol, single-timeframe replay with at most one open position.

## Ledger contract

- Each completed trade records the decision and fill timestamps, reference and fill prices, entry/exit commissions, exit reason, gross/net return, allocated notional, fractional quantity, and net P&L.
- Entry notional is the realized equity immediately before the entry. Position quantity is notional divided by actual entry fill price.
- Net P&L is allocated notional multiplied by the cost-adjusted trade return. Entry commission is included in net return and also exposed as a separate audit field; it must not be subtracted a second time from net P&L.
- Realized equity changes only when a position exits. An open position at the end of the dataset contributes a separately labeled unrealized mark-to-market estimate, including estimated adverse exit slippage and exit commission.
- An unfilled decision is recorded with a reason; it is not silently dropped or counted as a completed trade.

## Metrics

- `completed_trades`: completed exits only.
- `unfilled_decisions`: recorded entry decisions that did not produce a position.
- `win_rate`: winning completed trades divided by completed trades; zero when there are no completed trades.
- `cumulative_net_return`: final equity (including estimated unrealized P&L for a terminal open position) minus initial capital, divided by initial capital.
- `max_drawdown`: maximum peak-to-subsequent-equity decline divided by the prior peak, measured on the bar-level equity curve. Initial capital is the starting peak.
- `exposure_bars`: number of bars during which the engine held a position, including the entry bar even if an exit also occurs within that bar.
- `total_bars`: number of validated bars in the run.
- `time_in_market_ratio`: `exposure_bars / total_bars`; this is a coarse bar-count proxy, not exact elapsed-time exposure for irregular sessions or gaps.

All arithmetic is Decimal-based. Display rounding must not feed back into the ledger or metrics. These metrics describe the supplied dataset and simulation assumptions only; they do not establish predictive skill or real-market execution quality.
