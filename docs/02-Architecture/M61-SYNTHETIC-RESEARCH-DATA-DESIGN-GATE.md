# M61 Synthetic Research Data — Design Gate

Status: Accepted for development and deterministic feature validation
Scope: Synthetic research data only; not historical market evidence.

## Purpose

M61 is blocked from evidence-backed historical conclusions by the absence of an accepted real historical dataset. Development must not stop because of that external dependency.

The repository therefore provides a deterministic synthetic market harness for exercising analytical features, backtesting semantics, stress logic, application integration, controlled edge cases, and repeatable research experiments.

## Boundary

Synthetic data is development/test evidence only. It is never accepted as real historical evidence. The existing M61 historical-dataset loader, provenance chain, COMI intake, and immutable real-dataset gate remain unchanged.

## Required properties

Every generated dataset has a fixed scenario identity, recorded seed, deterministic output, stable internal stock identities, timezone-aware timestamps, valid OHLCV relationships, multiple market regimes, stress periods, indicator warm-up capacity, and no live-provider dependency.

## Initial controlled regimes

- bull trend
- bear trend
- sideways/range
- high volatility
- crash/stress

The generator also introduces controlled volume expansion and heavy-tail shocks so volume, volatility, anomaly, stress, and risk features can be exercised.

## Validation rule

A passing synthetic test proves implementation behavior only. It does not prove that an observed EGX pattern occurs with the same frequency in reality, that a strategy has positive expected return in EGX, or that synthetic Sharpe, win rate, drawdown, or profit is a real-market estimate.

Current research likewise treats synthetic financial series as a controlled testing/stress tool and emphasizes regime shifts, tail behavior, chronology, and out-of-sample validation rather than treating synthetic results as market proof.

## Next slices

1. scenario-level feature fixtures
2. synthetic point-in-time financial snapshots
3. market-index and sector correlation fixtures
4. controlled anomaly/event fixtures
5. strategy/backtest scenario suite
6. risk, portfolio, and Monte-Carlo scenarios
7. feature coverage matrix
8. synthetic research report export