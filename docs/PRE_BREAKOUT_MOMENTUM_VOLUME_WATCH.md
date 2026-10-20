# Pre-breakout Momentum + Volume Watchlist

## Endpoint

Use the authenticated endpoint:

`GET /api/v1/market-intelligence/scanners/technical?symbols=COMI,EGAL&scanner_id=pre-breakout-momentum-volume`

The existing `trend-momentum-volume` scanner remains unchanged. The new scanner returns stocks whose latest saved analysis has:
- positive rate-of-change momentum;
- volume at least 1.5 times the preceding average used by the existing volume analyzer; and
- a current price still below the nearest resistance, no more than 5% below it.

The response includes the momentum percentage, volume ratio, resistance price, percentage distance to resistance, and the evidence criteria. Results are ordered by volume expansion, then momentum, then existing stock-quality score.

## Interpretation and limitations

This is a **watchlist**, not a buy signal. Volume expansion can reflect selling or one-off events; this scanner only checks the existing technical evidence and does not prove accumulation or predict future returns. It uses the latest saved analysis result, which can be stale. Corporate actions, liquidity constraints, spread, and point-in-time data completeness are not independently verified. A price crossing resistance belongs to the existing breakout scanner, not this pre-breakout list.

The 1.5x and 5% thresholds are initial operational heuristics, not empirically optimized values. Validate out of sample across multiple EGX symbols and periods before relying on them.
