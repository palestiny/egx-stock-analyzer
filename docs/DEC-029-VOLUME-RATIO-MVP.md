# DEC-029 — Volume Ratio MVP

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis

## Context

Technical Analysis should expose independent, deterministic evidence before any scoring or signal-generation logic is introduced.

Trend, Support/Resistance, and Momentum already provide price-structure evidence. The next capability adds a volume dimension without interpreting volume as a BUY/SELL signal.

## Decision

The MVP will implement **Volume Ratio Evidence**.

### Formula

```text
Volume Ratio = Current Volume / Average Previous Volume
```

Where:

- Current Volume = volume of the latest `PriceBar`.
- Previous Volume = volumes from the preceding `lookback` bars.
- Average Previous Volume = arithmetic mean of those preceding volumes.

The analyzer receives `lookback` explicitly. No fixed lookback value is embedded in the domain logic.

## API

```python
VolumeAnalyzer.analyze(
    stock_id,
    timeframe,
    price_bars,
    lookback,
)
```

The analyzer assumes `price_bars` are ordered oldest-to-newest.

`stock_id` and `timeframe` remain explicit analysis context, consistent with the other technical analyzers. The MVP does not validate that every bar matches that context.

## Evidence

The MVP will expose immutable evidence containing:

- `status`
- `volume_ratio`

Conceptually:

```python
@dataclass(frozen=True)
class VolumeEvidence:
    status: VolumeStatus
    volume_ratio: Decimal | None = None
```

### Status

Status is descriptive and contains no arbitrary threshold:

- `ABOVE_AVERAGE` when ratio > 1
- `BELOW_AVERAGE` when ratio < 1
- `EQUAL_TO_AVERAGE` when ratio == 1
- `INSUFFICIENT_DATA` when fewer than `lookback + 1` bars are available
- `UNDEFINED` when the average previous volume is zero

## Why Ratio Instead of Raw Volume

Raw volume only describes the latest observation.

Volume Ratio provides comparative evidence against the stock's own recent volume history while remaining deterministic, explainable, and strategy-independent.

## Explicitly Out of Scope

This MVP does not implement:

- accumulation/distribution interpretation
- OBV
- Money Flow indicators
- Volume Profile
- volume acceleration
- arbitrary volume thresholds such as 1.5x
- BUY/SELL signals
- scoring
- confidence
- data-quality validation
- provider-specific rules

These may be considered later as separate design decisions if the analytical core requires them.

## Insufficient Data

The analyzer returns `INSUFFICIENT_DATA` when:

```text
len(price_bars) < lookback + 1
```

No conclusion is inferred from incomplete history.

## Zero Baseline

If the average of the previous volumes is zero, the ratio is mathematically undefined.

The analyzer returns `UNDEFINED` and does not fabricate a numeric ratio.

## Determinism

For the same ordered input observations and the same `lookback`, the analyzer must always return the same evidence.

## Immutability

`VolumeEvidence` is an immutable Value Object, consistent with the evidence types used by the other technical analyzers.

## Architectural Boundary

`VolumeAnalyzer` is an evidence-discovery component.

It does not decide whether high or low volume is good or bad, does not generate a trading signal, and does not participate in scoring.

Future accumulation/confirmation logic can consume this evidence without changing the responsibility of the MVP analyzer.

## TDD Acceptance Criteria

RED tests must cover:

1. volume above previous average → `ABOVE_AVERAGE`
2. volume below previous average → `BELOW_AVERAGE`
3. volume equal to previous average → `EQUAL_TO_AVERAGE`
4. exact ratio preservation
5. insufficient data
6. zero average previous volume → `UNDEFINED`
7. evidence immutability
8. deterministic repeated analysis
9. returned object is `VolumeEvidence`
