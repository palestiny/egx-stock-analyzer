# DEC-023 — Technical Analysis Result Design

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis

## Context

The project is now entering the Core Analytical Track. Technical Analysis must become a reusable domain capability that can incorporate multiple forms of technical evidence without coupling the model to a single indicator or calculation.

Potential evidence includes:

- trend
- support / resistance
- moving averages
- momentum
- volatility
- breakouts
- gaps
- volume / accumulation
- future analytical factors not yet identified

The first implementation must remain small, deterministic, and testable.

## Decision

`TechnicalAnalysisResult` represents the technical evidence produced for a defined stock, timeframe, and historical analysis window.

Conceptually:

```text
Stock
+ Timeframe
+ Analysis Window
+ Available Observations
        ↓
Technical Analysis
        ↓
Technical Analysis Result
        ├── technical evidence
        └── analysis outcome / sufficiency
```

The result is a **container of analytical evidence**, not the implementation of a specific indicator.

Individual analytical capabilities such as Trend, Support/Resistance, Momentum, or Volatility remain separate concerns. New capabilities can be added without redesigning the meaning of the overall result.

## Initial Capability

The first vertical slice will implement **Trend Analysis**.

This is an implementation starting point, not a commitment that Trend is the most important technical factor in the final strategy.

Future capabilities remain open:

```text
Trend
Support / Resistance
Moving Averages
Momentum
Volatility
Breakouts
Gaps
Volume / Accumulation
...
```

## Analysis Scope

Technical analysis is not Daily-only by domain design.

The result is associated with:

- Stock
- Timeframe
- an explicit historical analysis window

Daily remains the MVP timeframe because that is the currently established market-data foundation.

## Insufficient Data

A technical analysis must not manufacture a conclusion when the available observations are insufficient for the calculation.

Insufficient history is an analytical outcome, not automatically invalid market data.

The design must distinguish at least:

```text
Sufficient observations → analytical evidence
Insufficient observations → insufficient-data outcome
```

The exact representation of this outcome will be finalized through TDD before implementation.

## Determinism

For the same:

```text
Historical observations
+ analysis configuration
+ strategy/calculation version
```

the technical result must be deterministic and reproducible.

## Boundaries

`TechnicalAnalysisResult` does not own:

- external data acquisition
- provider rules
- data-quality assessment
- trading calendar rules
- scoring
- BUY/WATCH/HOLD/AVOID decisions
- alerts
- persistence
- UI

Scoring consumes technical evidence later. Signal generation consumes scoring and other analytical evidence later.

## Alternatives Considered

### Single Indicator Result
Reject. This would make the technical-analysis model dependent on one calculation and make future expansion awkward.

### One Large Technical Analyzer With Every Indicator
Reject. This would create a large, coupled domain service before the analytical requirements are understood.

### Generic Plugin/Strategy Framework Immediately
Reject for now. The project needs real analytical behavior first; abstraction will be introduced only where actual variation justifies it.

## Consequences

Positive:

- multiple technical factors can evolve independently
- the first implementation remains small
- analysis remains deterministic and testable
- future scoring can consume explainable evidence
- timeframe and historical-window semantics remain explicit

Trade-off:

- the exact internal shape of each evidence type will be discovered incrementally
- some abstractions may be introduced later when additional analytical capabilities are implemented

## Next Step

Proceed with TDD for the smallest useful **Trend Analysis** vertical slice.

Before implementation, define the domain meaning of Trend and its minimum required historical observations through tests.
