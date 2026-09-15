# DEC-024 — Trend Analyzer Input Context

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis

## Context

The first technical-analysis vertical slice is Trend Analysis. The analyzer needs explicit context for the stock and timeframe being analyzed while consuming historical `PriceBar` observations.

Two initial API shapes were considered:

```python
TrendAnalyzer.analyze(price_bars)
```

and:

```python
TrendAnalyzer.analyze(stock_id, timeframe, price_bars)
```

## Decision

Use the explicit-context API:

```python
TrendAnalyzer.analyze(stock_id, timeframe, price_bars)
```

The analysis context is therefore explicit rather than inferred only from the supplied observations.

## Rationale

### Explicit analysis scope

Technical analysis is defined for a Stock + Timeframe + historical analysis window. Making Stock and Timeframe explicit keeps the analyzer's scope visible at the call site.

### Validation of observation context

The analyzer can later verify that supplied observations belong to the requested stock and timeframe without changing its public API.

### Extensibility

Future analysis configuration may include additional parameters. The current API keeps the boundary explicit without introducing a context object before actual variation justifies one.

## Trade-offs

### `analyze(price_bars)`

Pros:
- smaller API
- less duplicated information
- convenient when all context is guaranteed by the collection

Cons:
- analysis scope is implicit
- empty or mixed observations make the intended context ambiguous
- future scope/configuration becomes less explicit

### `analyze(stock_id, timeframe, price_bars)`

Pros:
- explicit analysis scope
- easier future consistency checks
- aligns directly with the Technical Analysis Result design

Cons:
- Stock and Timeframe can be duplicated because each `PriceBar` already carries them
- consistency checks must eventually define what happens when observations do not match the requested context

## Boundary

Do not introduce a `TechnicalAnalysisContext` or similar abstraction yet. Add such an abstraction only if real analytical configuration demonstrates that the explicit parameter list has become a meaningful variation point.

## Output Direction

`TrendAnalyzer` should produce trend evidence rather than directly produce a final BUY/WATCH/HOLD/AVOID decision.

### TrendEvidence shape

The first TDD implementation establishes `TrendEvidence` as an immutable Value Object containing only the trend conclusion:

```python
@dataclass(frozen=True)
class TrendEvidence:
    status: TrendStatus
```

`TrendAnalyzer.analyze(...)` returns `TrendEvidence` rather than a generic `TrendResult`.

The evidence object intentionally does not yet include confidence, swing points, explanation text, score, or other metadata. Those concerns will only be added if later analytical requirements justify them.

## Consequence

The first TDD API is:

```python
TrendAnalyzer.analyze(stock_id, timeframe, price_bars)
```

The test suite establishes deterministic behavior for rising, falling, sideways, and insufficient-history observations. The current implementation represents the trend conclusion as `TrendEvidence`.
