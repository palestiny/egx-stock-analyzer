# Research Evaluation Semantics

This module defines deterministic primitives for historical evaluation; it is not a complete backtester.

- Decisions use a bar only after its close is available.
- `NEXT_OPEN` fills at the next bar open; the decision bar cannot fill itself.
- Long entries pay adverse slippage upward; short entries pay adverse slippage downward.
- Exits pay adverse slippage against the position.
- Commission is charged on both entry and exit notionals.
- If a bar reaches target and invalidation, `INVALIDATION_FIRST` wins.
- A gap through invalidation exits at the bar open when the open is already beyond the stop; otherwise exit at the stop. The result is still an OHLC approximation, not tick-level execution.
- Bars with non-VALID quality cannot be evaluated.
- A missing next bar yields no fill (`None`), never a fabricated fill.

Returns are expressed relative to entry notional and include entry/exit slippage and commissions. This primitive does not model market impact, partial fills, exchange fees by tier, taxes, or liquidity constraints.
