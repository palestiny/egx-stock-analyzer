# Backtest Engine — Design Gate

**Status:** Proposed; implementation not yet authorized  
**Date:** 2026-10-09  
**Repository:** palestiny/egx-stock-analyzer

## Decision to be made

Build a deterministic, single-symbol historical backtest runner on top of the Research Dataset Contract and the evaluation/fill primitives. Keep the first version deliberately narrow; do not claim a strategy is profitable or ready for live use.

## Existing foundation

- Canonical `ResearchBar` includes OHLCV, source/ingestion timestamps, provider, dataset version, quality, and adjustment status.
- `ResearchRunConfig` records dataset/provider/strategy/evaluator identities, execution and ambiguity policies, adjustment policy, and cost rates.
- Evaluation primitives support NEXT_OPEN entry, adverse slippage, commission, gap handling, and INVALIDATION_FIRST same-bar ambiguity.
- These primitives are not yet a sequential portfolio/backtest engine.

## Proposed v1 scope

1. **Single-symbol, one-timeframe replay.** Consume one homogeneous, ordered series. Multi-symbol portfolios, intraday tick replay, optimization, and parallel execution are out of scope.
2. **Point-in-time strategy interface.** At index *i*, strategy input may contain only bars up to and including *i*. The runner—not strategy code—owns iteration and the next-open fill boundary.
3. **Explicit position lifecycle.** At most one open position per run; long/short direction is explicit; entry decisions, fills, exits, and terminal states are recorded as immutable events.
4. **No fabricated fills.** An entry decision at the final bar remains unfilled. Missing/invalid bars fail closed or stop the run with a typed reason; never silently bridge gaps.
5. **Deterministic exits.** Use the existing fill semantics, including invalidation-first when OHLC cannot establish intrabar ordering. Do not inspect a future bar to choose an exit.
6. **Cost-aware accounting.** Record reference price, fill price, slippage, entry and exit commissions, gross/net trade returns, and aggregate equity change separately. Do not silently use zero costs in any report presented as a realistic estimate.
7. **Reproducible run manifest.** Persist the exact run config, parameter snapshot/hash, dataset identity/version, first/last source timestamps, evaluator version, and stable run ID. Same manifest and input must produce identical ordered events and metrics.
8. **Auditable results.** Include trades, unfilled decisions, skipped/failed reasons, equity curve, and summary metrics with metric definitions. No result should omit failed or unfilled cases from the audit trail.

## Anti-lookahead rules (hard requirements)

- Strategy evaluation at bar *i* cannot access bars after *i*.
- A decision on bar *i* cannot fill at that bar's close; NEXT_OPEN means the next eligible bar's open.
- No backward/forward filling, synthetic bars, or using ingestion time as a substitute for source event time.
- All data must pass quality, homogeneous-series, ordering, duplicate, adjustment, and point-in-time validation.
- A test must deliberately mutate future bars and prove earlier decisions/fills remain unchanged.
- A test must prove the final-bar signal has no fill.
- Corporate actions, survivorship bias, delisted-symbol coverage, and point-in-time fundamentals are not solved by this v1; results must disclose these limitations.

## Accounting and metric definitions

- Define the return denominator and entry/exit fee treatment before implementation; reconcile trade-level net returns with equity accounting.
- Keep gross and net returns distinct. Include transaction costs in net results.
- Report at minimum: completed trades, unfilled decisions, win rate, gross/net cumulative return, max drawdown, and exposure/time-in-market. Define edge cases such as zero trades and zero drawdown.
- Do not annualize results without a documented time basis and calendar/session convention.
- Metrics must be computed from the recorded equity/trade ledger, not independently reconstructed from rounded display values.

## Data and run validity

- Reject a run when `ResearchRunConfig` does not match bar provider, dataset version, or adjustment state.
- Missing or non-VALID bars must not be treated as ordinary flat returns. The run must return a clear invalid/partial status and reason.
- Require an explicit timezone/session convention before making session-sensitive claims. No inferred Egyptian exchange calendar is permitted.
- Synthetic fixtures validate mechanics only; they cannot establish real-EGX performance.

## Required tests before implementation is considered complete

1. Future-data mutation does not alter earlier signals or fills.
2. Next-open timing, including final-bar no-fill.
3. Same-bar target/invalidation ambiguity and gap-through-stop behavior.
4. Costs affect net results and ledger reconciliation is exact within Decimal arithmetic.
5. Duplicate, out-of-order, mixed-series, mixed-adjustment, future, and non-VALID input rejection.
6. Reproducibility: identical inputs/config yield identical event sequence and metrics.
7. Zero-trade, no-entry, terminal-open-position, and invalid/partial dataset outcomes.
8. Long and short direction cases.
9. Property or invariant tests for equity and position lifecycle (no overlapping positions in v1; no exit before entry; one terminal exit per opened position).

## Explicit non-goals

- Broker integration or trade execution.
- Claims of predictive accuracy or profitability.
- Live provider certification or acceptance of Tradeglob data.
- Tick/order-book simulation, market impact, partial fills, taxes, tiered exchange fees, or liquidity modeling.
- Strategy parameter optimization, walk-forward validation, or machine-learning training.

## Acceptance gate

**PASS** only when the runner has a documented point-in-time interface, immutable ledger, exact cost accounting, deterministic manifest/results, explicit invalid/partial outcomes, and all required tests above pass in CI.

Before implementation, review the unresolved choices below and agree the contract.

## Open decisions

1. **Position policy:** one position at a time (recommended) vs. multiple simultaneous positions.
2. **Terminal open position:** mark to market at the last valid close (recommended, labeled unrealized) vs. leave open without including it in realized returns.
3. **Invalid data mid-run:** fail the whole run (recommended for v1) vs. return partial results with an explicit invalid/partial status.
4. **Signal protocol:** strategy emits a typed entry/exit intent with stop/target levels (recommended) vs. the engine infers trades from indicator values.
5. **Persistence:** return immutable result objects first (recommended) vs. persist run/trade records immediately. Persistence should follow only after result schema is stable.

## Recommendation

Approve the narrow v1 boundary above. Implement only after the design decisions are accepted; keep strategy generation, execution simulation, accounting, and presentation as separate responsibilities.
