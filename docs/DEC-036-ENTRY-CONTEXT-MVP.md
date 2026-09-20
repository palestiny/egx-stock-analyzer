# DEC-036 — Entry Context MVP

**Status:** Accepted  
**Milestone:** M7 — Signal / Opportunity Detection

## Context

Stock Quality answers whether the stock's fundamental and technical evidence is favorable. It does not answer whether the current price represents an attractive entry.

Support and resistance were intentionally excluded from Technical Score and reserved for Entry Quality. The current Support/Resistance capability discovers structural levels without assigning strength or trading meaning.

Before defining BUY/WATCH/HOLD/AVOID rules, the system needs a deterministic representation of the current price's structural context.

## Decision

The first M7 slice will produce **Entry Context**, not a BUY/SELL decision.

Given the latest PriceBar and discovered structural levels, the system will identify:

- current price
- nearest structural support below or equal to current price
- nearest structural resistance above or equal to current price

The result is immutable and deterministic.

If no surrounding level exists, the corresponding value is `None`.

## Explicitly Excluded

- support/resistance strength
- clustering
- tolerance or zones
- percentage-distance thresholds
- Entry Quality score
- BUY/SELL/WATCH/HOLD/AVOID
- stop loss
- targets
- risk/reward
- ranking
- strategy-specific weights

## Reasoning

This keeps three responsibilities separate:

```text
Structural Detection
        ↓
Entry Context
        ↓
Entry Quality / Opportunity Rules
```

The current structural-level detector already preserves discovered levels. Entry Context only interprets their spatial relationship to the latest price.

## TDD Acceptance Criteria

1. Latest close is preserved as current price.
2. Nearest support below current price is selected.
3. Nearest resistance above current price is selected.
4. Levels on the wrong side of the current price are ignored.
5. Missing support or resistance produces `None` rather than a guessed level.
6. Result is immutable.
7. Repeated analysis is deterministic.
