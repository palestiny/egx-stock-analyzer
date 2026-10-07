# M61 Synthetic Feature Scenario Matrix

| Capability | Controlled scenario | Synthetic evidence |
|---|---|---|
| Trend | bull / bear | regime labels + OHLCV |
| Support / resistance | range + repeated reversals | deterministic price path |
| Breakout | range-to-bull transition | regime boundary |
| Pullback | bull after impulse | post-breakout sequence |
| Momentum | persistent drift | bull/bear |
| Mean reversion | sideways | range regime |
| Volatility | high-volatility regime | clustered shocks |
| Volume anomaly | injected volume spikes | event fixture |
| Crash Radar | crash regime | negative shocks + volume |
| Market Stress | cross-sectional shock | breadth + volatility + crash ratios |
| Market Stress | crash/high-volatility | regime + event fixture |
| Fundamental score | PIT snapshots | availability/revision metadata |
| Financial trend | annual snapshots | revenue/net-income sequence |
| Liquidity/solvency | current assets/liabilities | PIT snapshot |
| Correlation | peer relationships | deterministic coefficients |
| Alerts | BUY opportunity + Crash Radar | AlertCandidate + AlertEvent |
| Backtesting | full chronological bars | deterministic series |
| Costs/slippage | simulator configuration | existing M61 simulator |
| Risk metrics | synthetic trade paths | backtest outputs |
| Portfolio allocation | ten-symbol equal-weight cohort | position weights + cash reserve |
| Portfolio concentration | per-name cap | max single-name constraint |
| Portfolio performance | aligned multi-symbol returns | weighted portfolio return series |
| Portfolio risk | drawdown + volatility | deterministic portfolio metrics |
| Portfolio correlation | pairwise return series | average pairwise correlation |
| Robustness | repeated seeds | deterministic scenario generation |

## Rule

Synthetic results validate implementation and scenario behavior. They are not evidence of real EGX returns or predictive edge.

## Execution order

1. technical feature scenario tests
2. fundamental/PIT feature tests
3. scoring and opportunity classification
4. Crash Radar / Market Stress
5. alerts
6. strategy/backtest scenarios
7. portfolio/risk/Monte-Carlo
8. API integration
9. reproducible synthetic research report

Real historical evidence remains a separate acceptance gate.
