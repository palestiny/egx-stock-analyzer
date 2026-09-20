# DEC-027 — Support / Resistance Structural Levels

**Status:** Accepted  
**Milestone:** M4 — Technical Analysis

## Context

The Support / Resistance capability follows Trend Analysis.

The MVP needs a deterministic way to discover structural support and resistance levels without prematurely introducing level strength, clustering, zones, or trading decisions.

The project has already accepted the principle of **Simple MVP, Extensible Architecture** in DEC-026.

## Decision

The first Support / Resistance implementation will use structural swing points as single price levels.

```text
Swing Low  → Support Level
Swing High → Resistance Level
```

Every swing point discovered by the current project swing rule is eligible to become a structural level.

The MVP will not evaluate whether a level is strong or weak.

### Price Level Evidence

A discovered level is represented by immutable evidence containing:

```python
@dataclass(frozen=True)
class PriceLevelEvidence:
    price: Price
    timestamp: datetime
```

`stock_id` and `timeframe` are not repeated inside each `PriceLevelEvidence` because they are already part of the analysis context supplied to the analyzer.

### Result When Levels Are Limited

The analyzer will return the levels that it actually discovers.

A support or resistance collection may therefore be empty or contain only one level.

The MVP will **not** introduce an `INSUFFICIENT_DATA` status for Support / Resistance merely because there are few discovered levels.

The distinction between:

```text
Evidence discovered
```

and:

```text
Evidence sufficient for a later decision
```

belongs to later interpretation, scoring, or opportunity-detection responsibilities.

### Strength Evaluation Boundary

Level strength is explicitly deferred.

Future concerns such as:

- touches / retests
- recency
- reaction magnitude
- volume confirmation
- clustering
- tolerance
- zones

must not be embedded in the initial structural-level detector.

They may be introduced later through a separate Design Gate when real analytical requirements justify them.

## Alternatives Considered

### 1. Every Swing Becomes a Structural Level

Chosen for the MVP.

This is deterministic, simple, and preserves all discovered structural evidence.

### 2. Only Strong Swings Become Levels

Rejected for the MVP because deciding what makes a level strong would introduce additional analytical rules before their meaning and requirements are established.

### 3. Structural Levels Plus Strength Status

Deferred.

This would preserve the levels while also returning a strength assessment, but strength is not yet required by the current capability and would expand the result model prematurely.

## Trade-offs

### Benefits

- simple and deterministic
- easy to express through TDD
- preserves discovered structural evidence
- keeps detection separate from interpretation
- avoids premature strength formulas
- leaves room for future zones, clustering, and strength analysis

### Costs

- the MVP may produce many levels
- some discovered levels may be weak or not useful for trading decisions
- a later consumer must not assume that every structural level is automatically a strong trading level
- future strength evaluation may require additional domain concepts

These costs are accepted because the current capability is **structural level detection**, not trading decision generation.

## Consequences

The Support / Resistance analyzer should remain focused on discovering structural levels from the existing price structure.

Conceptually:

```text
PriceBars
   ↓
Swing Detection
   ↓
Structural Levels
   ↓
PriceLevelEvidence
   ↓
SupportResistanceEvidence
```

Later analysis may extend this flow:

```text
Structural Levels
   ↓
Strength / Context Analysis
   ↓
Scoring
   ↓
Opportunity Detection
```

No current implementation should assume that a structural level is itself a BUY, SELL, WATCH, or other trading signal.

## Revisit Conditions

Revisit this decision when:

- level strength becomes a current analytical requirement
- the number of levels becomes difficult to interpret
- clustering or tolerance becomes necessary
- zones become preferable to single levels
- historical evaluation shows that the current structural detection is inadequate
- multiple detection strategies become real requirements

Any such change should follow a new Design Gate rather than silently changing the MVP behavior.
