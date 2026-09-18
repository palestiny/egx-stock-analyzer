# M17 — Market Universe & All-Market Execution MVP Completion

**Milestone:** M17  
**Design Gate:** `docs/DEC-076-M17-MARKET-UNIVERSE-EXECUTION-DESIGN-GATE.md`  
**Status:** Complete  
**Date:** 2026-09-18

## Outcome

M17 establishes the first application-owned configured-market universe and all-market execution path.

The implemented flow is:

```
POST /api/v1/market-analysis
        ↓
RunConfiguredMarketAnalysis
        ↓
StockCatalog.symbols()
        ↓
RunMarketAnalysis
        ↓
RunStockAnalysis
        ↓
AnalysisResultStore
```

## Implemented

- `StockCatalog.symbols() -> tuple[str, ...]` provides a deterministic normalized universe snapshot.
- `InMemoryStockCatalog` preserves constructor order and rejects duplicate symbols.
- `RunConfiguredMarketAnalysis` captures the catalog snapshot once and delegates to `RunMarketAnalysis`.
- `POST /api/v1/market-analysis` triggers configured-market execution.
- API transport returns execution identity, aggregate state, successful stocks, failed stocks, and failure reasons.
- Existing M14 sequential execution and partial-failure semantics remain unchanged.
- Existing per-stock retry and persistence boundaries remain unchanged.
- Runtime composition exposes the configured-market capability.
- Focused catalog, application, API, contract, runtime, and composition tests were added.

## Validation

PR #15, `feat: implement M17 market universe and all-market execution`, was merged into `main` after GitHub Actions Run #349 completed successfully for implementation head `b5b420923490109ccb8307c2ce00b32691d06f6a`.

The merge commit is:

```
d084b953e28a10f0a211333b252fd5003b2f20ca
```

## Contract Preserved

M17 does not modify:

- stock-level analytical calculations;
- M14 aggregate execution semantics;
- M15 opportunity ranking;
- M16 opportunity read-side behavior;
- persistence schema;
- scheduler behavior;
- dashboard analytical responsibilities;
- concurrency;
- notification delivery;
- trading execution;
- AI-based stock selection.

## Deferred

The following remain outside M17:

- recurring full-market scheduling;
- exchange constituent synchronization;
- independently persisted universes;
- user-configurable universes/watchlists;
- universe filtering by strategy;
- concurrency and distributed execution;
- provider failover;
- portfolio allocation;
- trading execution;
- AI-based stock selection.

## Completion Decision

M17 is complete for its accepted MVP scope.

The next milestone must be opened through a new design gate rather than expanding M17 opportunistically.
