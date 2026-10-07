# Active Trading & Real-Time Scalping Intelligence

**Status:** Planned capability — architecture documentation only  
**Parent capability:** Market Intelligence  
**Execution authority:** `docs/ROADMAP.md`  
**Current active milestone:** M61 — Backtesting & Strategy Validation

## Purpose

Extend the platform so the same Market Intelligence core can support two distinct usage horizons:

- investment / swing / position-oriented analysis;
- real-time active trading and short-horizon scalping.

The capability must remain market-agnostic and provider-independent. EGX and US markets are market adapters, not separate analytical cores.

## Scope

The capability may eventually include:

1. real-time market-data ingestion;
2. normalized tick, trade, quote, and optional order-book contracts;
3. low-latency in-memory market state;
4. tick-level feature calculation;
5. market-wide momentum/opportunity scanning;
6. breakout, acceleration, abnormal-volume, liquidity, and microstructure signals;
7. versioned short-horizon strategies;
8. real-time alerts;
9. replay and tick-level backtesting;
10. paper trading;
11. human-in-the-loop hotkeys;
12. broker/execution adapters as a separately governed boundary.

## Architecture boundary

The intended flow is:

```
Market Data Provider
        ↓
Market Adapter
        ↓
Normalized Market Events
        ↓
Real-Time / Tick Engine
        ↓
Feature & Opportunity Intelligence
        ↓
Versioned Strategy
        ↓
Trade Plan
        ↓
Recommendation / Alert
        ↓
Human Action / Intent
        ↓
Safety / Execution Boundary
        ↓
Optional Execution Adapter
```

The real-time layer must not bypass the existing six-stage Decision & Trade Plan lifecycle established by DEC-133:

**Analytical State → Opportunity → Strategy Eligibility → Trade Plan → Recommendation → Human Action**

The Safety / Execution Boundary is not an additional lifecycle stage. It protects the Human Action stage and any subsequent execution path.

**Recommendation ≠ Order. Human Action ≠ Broker Order. Hotkey Intent ≠ Accepted Order.**

The deterministic protected path is:

**Recommendation → Human Action / Intent → Safety / Execution Boundary → validation / risk / state / freshness / idempotency / kill-switch checks → Execution Adapter → Broker.**

## Investment vs Active Trading

These are different strategy horizons over shared evidence and domain contracts.

A stock can simultaneously have:

- an investment state such as HOLD; and
- a short-horizon opportunity such as a momentum setup.

This is not a contradiction because strategy, horizon, risk, and objective differ.

## Data availability rule

Capabilities are conditional on trustworthy data.

Supported data classes must be explicit:

- required and available;
- required but provider-dependent;
- optional;
- unavailable;
- unknown.

Missing tick/order-book information must reduce capability/evidence, never be fabricated.

## Validation boundary

A real-time/scalping strategy is not considered authoritative merely because it is implemented.

Promotion requires validation appropriate to its time horizon, including as applicable:

- deterministic tests;
- historical replay;
- point-in-time controls;
- transaction costs and slippage;
- out-of-sample or walk-forward validation;
- robustness/sensitivity testing;
- paper/live operational validation;
- latency and data-quality measurement.

"Implemented" and "profitable" are separate states.

## Execution boundary

The initial target is human-in-the-loop decision support.

Hotkeys emit human-action intent and may accelerate a user-confirmed action, but they do not make the recommendation an order and do not authorize autonomous trading. Every hotkey intent is subject to the deterministic Safety / Execution Boundary, including freshness, integrity, risk, position state, duplicate protection, idempotency, and kill-switch checks.

Broker execution must be isolated behind an adapter and requires its own design/validation boundary. No UI, hotkey, AI component, strategy, or recommendation may bypass the Safety / Execution Boundary.

## Planned decomposition

The capability is expected to be designed and implemented through separately governed slices:

- RT-01 — Real-Time Market Data Architecture
- RT-02 — Tick Engine
- RT-03 — Real-Time Market Scanner
- RT-04 — Short-Horizon Strategy Framework
- RT-05 — Tick Replay & Backtesting
- RT-06 — Paper Trading
- RT-07 — Active Trading UI & Hotkeys
- RT-08 — Broker/Execution Adapter

These are planning identifiers, not current roadmap milestones.

## Governance

No RT implementation begins merely because this capability is documented.

Before implementation:

1. an architecture Design Gate must be proposed and accepted;
2. the relevant execution slice must be explicitly authorized by the single execution roadmap;
3. existing capabilities and decisions must be mapped before adding new code;
4. each significant behavior must follow the project engineering execution rule.

The current active milestone remains M61. Documenting this capability does not authorize RT implementation or change M61 acceptance semantics.
