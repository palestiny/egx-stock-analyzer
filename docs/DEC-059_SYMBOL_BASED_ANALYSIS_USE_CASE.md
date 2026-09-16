# DEC-059 — Symbol-Based Stock Analysis Use Case

## Decision

Add `RunStockAnalysisBySymbol` as a thin application-level orchestration boundary between an external symbol and the existing stock analysis use case.

Flow:

`symbol + as_of → StockCatalog → Stock → RunStockAnalysis`

## Responsibilities

`RunStockAnalysisBySymbol` only:

- resolves the symbol through `StockCatalog`
- rejects an unknown symbol
- delegates the resolved `Stock` to `RunStockAnalysis`

It does not:

- fetch market data
- fetch fundamentals
- perform analysis or scoring
- persist results
- handle HTTP
- know how stocks are stored or resolved

## Why

The existing `RunStockAnalysis` correctly works with a domain `Stock` entity. External callers, however, naturally provide a symbol. Resolving that symbol belongs at an application boundary rather than in the domain or inside the analysis pipeline.

The first implementation uses `InMemoryStockCatalog`. This keeps M12 small while allowing the catalog implementation to be replaced later without changing the analysis orchestration.

## Deferred

- HTTP trigger/wiring
- production stock master source
- persistent stock catalog
- multi-stock daily orchestration
- authentication and authorization
