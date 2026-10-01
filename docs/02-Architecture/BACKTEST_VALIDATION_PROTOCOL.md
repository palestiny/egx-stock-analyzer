# Backtesting Validation Protocol

**Status:** Design gate — Strategy v0 performance is not yet validated.

## Objective

Prove that a backtest is temporally correct, reproducible, and based on an accepted historical dataset before using its results as evidence.

## Point-in-time rules

For a signal evaluated at bar index t:

- Strategy input may contain bars through t only.
- The signal may use information available at the timestamp represented by bar t.
- Entry execution is on a later bar; the current implementation uses the next bar open.
- Exit decisions are evaluated from information available at the decision bar and execute on the following bar open.
- Future bars must never be present in strategy input.

These rules must be covered by regression tests, not only by code inspection.

## Dataset integrity

An accepted dataset must have:

- stable symbol identity
- explicit source and acquisition metadata
- immutable/versioned artifact identity
- deterministic checksum
- documented date coverage
- strictly ordered timestamps
- duplicate detection
- missing-session handling rules
- OHLC consistency checks
- volume validity checks
- corporate-action convention
- documented treatment of delistings, symbol changes, and survivorship

## Reproducibility

A backtest record must identify:

- repository commit
- strategy ID and version
- configuration
- dataset version/checksum
- symbol/date range
- runtime/dependency state
- transaction-cost and slippage assumptions

Repeated execution against the same immutable inputs must produce the same result.

## Evaluation protocol

Do not optimize parameters on the evaluation period.

The validation plan should separate:

1. development/training period
2. validation period
3. untouched out-of-sample evaluation period

For time-series strategies, prefer chronological or walk-forward evaluation over random shuffling.

## Metrics

Win rate alone is insufficient. Record at least:

- completed/open trades
- cumulative net return
- average net return
- maximum drawdown
- volatility/risk-adjusted measures where appropriate
- exposure/time in market
- turnover and transaction-cost impact
- sample size

Metrics must be interpreted with the dataset period and assumptions attached.

## Acceptance gate

Strategy v0 may be described as validated only when:

1. the historical dataset passes its provenance/integrity gate;
2. point-in-time regression tests pass;
3. repeated runs are deterministic;
4. costs/slippage are explicitly configured;
5. out-of-sample evaluation is defined and untouched during development;
6. results are reproducible from recorded inputs.

A successful backtest is evidence about the tested historical scenario. It is not proof of future profitability.
