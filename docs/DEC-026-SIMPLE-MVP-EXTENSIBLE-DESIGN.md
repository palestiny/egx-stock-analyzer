# DEC-026 — Simple MVP, Extensible Architecture

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis  

## Context

Support / Resistance is the next technical-analysis capability after Trend Analysis.

The MVP should remain simple enough to design, test, and understand without introducing speculative abstractions. At the same time, the project is expected to become more sophisticated as later analytical requirements emerge.

Examples of possible future requirements include:

- support/resistance zones instead of single levels
- level clustering
- level strength
- number of touches / retests
- recency
- volume confirmation
- different detection strategies
- additional contextual evidence

The architecture therefore needs to avoid two opposite problems:

1. building excessive abstractions before the variation is real
2. designing the MVP in a way that makes future evolution unnecessarily expensive

## Decision

We will follow the principle:

> **Simple MVP, Extensible Architecture.**

The current implementation should be the simplest design that satisfies the current requirement, while keeping responsibilities and boundaries clean enough that expected future complexity can be added without rebuilding the core analytical model.

We will achieve extensibility primarily through:

- clear responsibility boundaries
- small domain concepts with explicit meaning
- separation between detection and later interpretation/strength evaluation
- immutable evidence objects where appropriate
- avoiding provider, UI, persistence, or infrastructure concerns inside analytical domain logic

We will **not** introduce speculative abstractions merely because a future variation is possible.

Examples of abstractions that are intentionally deferred unless real variation justifies them:

- `ISupportDetector`
- `ILevelClusterStrategy`
- `IPriceZoneFactory`
- `IStrengthCalculator`

When a real second implementation, strategy variation, or meaningful complexity appears, the design will be reconsidered through a new Design Gate rather than pre-building an abstraction in advance.

## Alternatives Considered

### 1. Minimal implementation with no concern for future evolution

This would optimize only for the immediate MVP.

Rejected because later requirements could force unnecessary rewriting of the core model.

### 2. Build a highly abstract framework now

This would attempt to anticipate future analytical strategies and extension points.

Rejected because the future variation is not sufficiently known and speculative abstractions would increase complexity without current value.

### 3. Simple MVP with clean boundaries

Chosen because it provides the current capability with low complexity while preserving reasonable evolution paths.

## Trade-offs

### Benefits

- simpler current implementation
- easier TDD and review
- lower cognitive overhead
- less premature abstraction
- future complexity can be introduced where it is actually required
- analytical responsibilities remain easier to understand

### Costs

- the MVP is not guaranteed to accommodate every future requirement without refactoring
- some future changes may still require redesign
- extensibility is achieved through good boundaries rather than guaranteed plug-in points

This is intentional. Refactoring based on real evidence is preferred over speculative architecture.

## Design Gate Rule

For future technical-analysis decisions, ask:

1. What is the simplest design that satisfies the current requirement?
2. What future change is reasonably expected?
3. Can the current design accommodate that change through its existing boundaries?
4. What would become expensive to change later?
5. Is an abstraction actually justified now, or is separation of responsibilities sufficient?

## Consequences

The Support / Resistance MVP can remain structurally small while still being compatible with later evolution toward stronger and more contextual levels or zones.

The current decision does **not** finalize all Support / Resistance algorithm details. Those decisions continue through the current Design Gate and must be documented separately when accepted.

Any significant future change to the analytical structure should follow the project's normal flow:

```text
Design Question
    ↓
Alternatives
    ↓
Trade-offs
    ↓
Decision
    ↓
Documentation
    ↓
TDD
    ↓
Implementation
```

## Revisit Conditions

Revisit this decision when:

- multiple support/resistance detection strategies are actually required
- zones become necessary instead of single levels
- strength evaluation becomes part of the current analytical responsibility
- clustering or tolerance rules become sufficiently complex to justify a separate abstraction
- existing boundaries prove insufficient for a real requirement
