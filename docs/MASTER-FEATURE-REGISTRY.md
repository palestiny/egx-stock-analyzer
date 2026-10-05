# Master Feature Registry — Market Intelligence Platform

**Status:** Working registry  
**Date:** 2026-10-05  
**Benchmark:** Publicly documented EGXBot capabilities  
**Target:** Market-agnostic capability parity + extensions

## Purpose

This is the master checklist for the product direction.

The registry separates:

- **Benchmark capability** — what the reference product publicly documents;
- **Current state** — what the current repository already has;
- **Target** — what this project intends to provide;
- **Data dependency** — whether a market/provider may limit availability.

The registry is intentionally broader than the current EGX-only implementation. It is not a claim that all rows are implemented today.

## Status Vocabulary

| Status | Meaning |
|---|---|
| IMPLEMENTED | Production capability exists in current main |
| PARTIAL | Foundation exists but important behavior is missing |
| MISSING | Not yet implemented |
| DATA-DEPENDENT | Capability is implemented/planned but requires market/provider evidence |
| PLANNED | Explicit future target |
| VERIFIED | Acceptance evidence exists for the stated scope |

## A. Research & Stock Analysis

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Brief stock report | PARTIAL | IMPLEMENTED | Low |
| Full technical report | PARTIAL | IMPLEMENTED | OHLCV |
| Fundamental report | PARTIAL | IMPLEMENTED | Fundamentals |
| Stock quality | IMPLEMENTED | IMPLEMENTED | Fundamentals + market data |
| Entry quality | IMPLEMENTED | IMPLEMENTED | Market data |
| Opportunity classification | IMPLEMENTED | IMPLEMENTED | Market data |
| Fair-value / valuation evidence | PARTIAL | IMPLEMENTED | Point-in-time fundamentals |
| Multi-timeframe analysis | PARTIAL | IMPLEMENTED | Multiple timeframes |
| Explainable analysis evidence | PARTIAL | IMPLEMENTED | Analysis inputs |

## B. Advanced Technical Engines

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Trend | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Momentum | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Volume | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Support / Resistance | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Fibonacci | PARTIAL | IMPLEMENTED | OHLCV |
| Breakout detection | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Classical chart patterns | PARTIAL | IMPLEMENTED | OHLCV |
| Divergence | MISSING | IMPLEMENTED | OHLCV |
| SMC | MISSING | IMPLEMENTED | OHLCV |
| Harmonic | MISSING | IMPLEMENTED | OHLCV |
| Elliott | MISSING | IMPLEMENTED | OHLCV |
| Gann | MISSING | IMPLEMENTED | OHLCV |
| Fractal analysis | MISSING | IMPLEMENTED | OHLCV |
| Volunacci | MISSING | IMPLEMENTED | OHLCV/volume |
| Time analysis | MISSING | IMPLEMENTED | OHLCV + calendar |
| Multi-timeframe confluence | MISSING | IMPLEMENTED | Multiple timeframes |

## C. Market Scanning

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Technical scanner | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Momentum scanner | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Sector scanner | IMPLEMENTED | IMPLEMENTED | Universe + sector data |
| Breakout scanner | IMPLEMENTED | IMPLEMENTED | OHLCV |
| Fibonacci opportunity scanner | PARTIAL | IMPLEMENTED | OHLCV |
| Smart scanner | PARTIAL | IMPLEMENTED | Multiple evidence types |
| Pattern scanner | MISSING | IMPLEMENTED | OHLCV |
| Liquidity scanner | PARTIAL | IMPLEMENTED | Quote/trade data |
| Whale / large-trade scanner | MISSING | IMPLEMENTED | Trades/order-flow |
| Leaders / laggards | IMPLEMENTED | IMPLEMENTED | Quotes |
| Intraday scanner | MISSING | IMPLEMENTED | Intraday data |
| Cross-market scanner | MISSING | IMPLEMENTED | Multiple markets |

## D. Signals & Trade Plans

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Canonical signal | PARTIAL | IMPLEMENTED | Analysis evidence |
| Entry zone | PARTIAL | IMPLEMENTED | Signal strategy |
| Invalidation | PARTIAL | IMPLEMENTED | Signal strategy |
| Target(s) | PARTIAL | IMPLEMENTED | Signal strategy |
| Stop loss | PARTIAL | IMPLEMENTED | Risk/strategy |
| Trailing stop | MISSING | IMPLEMENTED | Live/polling data |
| Signal lifecycle | MISSING | IMPLEMENTED | Persistent signal state |
| Signal tracking | MISSING | IMPLEMENTED | Historical observations |
| Outcome measurement | PARTIAL | IMPLEMENTED | Price history |
| Signal quality / confidence | PARTIAL | IMPLEMENTED | Evidence model |
| Strategy versioning | PARTIAL | IMPLEMENTED | Versioned strategy |
| Signal notifications | PARTIAL | IMPLEMENTED | Notification channel |

## E. Portfolio Intelligence

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Position tracking | PARTIAL | IMPLEMENTED | Trades/positions |
| P&L | PARTIAL | IMPLEMENTED | Prices + fills |
| Portfolio health | MISSING | IMPLEMENTED | Portfolio + market data |
| Risk / concentration | PARTIAL | IMPLEMENTED | Positions |
| Sector exposure | MISSING | IMPLEMENTED | Classification |
| Market exposure | MISSING | IMPLEMENTED | Market identity |
| Rotation context | MISSING | IMPLEMENTED | Sector/market data |
| Position verdict | MISSING | IMPLEMENTED | Signals + portfolio |
| Screenshot import | MISSING | PLANNED | OCR/AI |
| What-if simulation | MISSING | IMPLEMENTED | Portfolio model |
| Daily briefing | MISSING | IMPLEMENTED | Market + portfolio data |

## F. Backtesting & Strategy Research

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Deterministic backtest engine | IMPLEMENTED | IMPLEMENTED | Historical data |
| Leakage-safe financial input | IMPLEMENTED | IMPLEMENTED | Point-in-time data |
| Dataset provenance | IMPLEMENTED | IMPLEMENTED | Dataset metadata |
| Trade-level evaluation | PARTIAL | IMPLEMENTED | Historical data |
| Aggregate performance | PARTIAL | IMPLEMENTED | Historical data |
| Walk-forward testing | MISSING | IMPLEMENTED | Historical data |
| Parameter sensitivity | MISSING | IMPLEMENTED | Historical data |
| Monte Carlo robustness | MISSING | IMPLEMENTED | Backtest results |
| Strategy comparison | MISSING | IMPLEMENTED | Backtest results |
| Reproducible research run | PARTIAL | IMPLEMENTED | Versioned inputs |

## G. Alerts & Notifications

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Alert candidate | IMPLEMENTED | IMPLEMENTED | Analysis |
| Alert lifecycle | PARTIAL | IMPLEMENTED | Persistence |
| Push notifications | MISSING | IMPLEMENTED | Channel/provider |
| Telegram | MISSING | PLANNED | Telegram provider |
| Email | MISSING | PLANNED | Email provider |
| Web notifications | PARTIAL | IMPLEMENTED | Web app |

## H. Live / Intraday Market Intelligence

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Live quotes | PARTIAL | IMPLEMENTED | Realtime provider |
| Market Watch | MISSING | IMPLEMENTED | Realtime quotes |
| Order Book / Level 2 | MISSING | IMPLEMENTED | Level 2 |
| Time & Sales | MISSING | IMPLEMENTED | Trades |
| Price aggregation | MISSING | IMPLEMENTED | Trades/order book |
| Liquidity pulse | MISSING | IMPLEMENTED | Quotes/trades |
| Intraday opportunity lifecycle | MISSING | IMPLEMENTED | Intraday data |
| Market session state | MISSING | IMPLEMENTED | Exchange calendar |

## I. AI Research & Decision Support

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| AI stock research | MISSING | IMPLEMENTED | Analysis tools |
| AI market scan | MISSING | IMPLEMENTED | Scanner |
| AI portfolio analysis | MISSING | IMPLEMENTED | Portfolio |
| AI risk sizing | MISSING | IMPLEMENTED | Risk engine |
| AI what-if | MISSING | IMPLEMENTED | Portfolio/backtest |
| Evidence-aware answers | MISSING | IMPLEMENTED | Provenance |
| Daily AI briefing | MISSING | IMPLEMENTED | Market/news/portfolio |
| AI tracked ideas | MISSING | IMPLEMENTED | Signal lifecycle |

## J. Trading Automation

| Capability | Current | Target | Dependency |
|---|---|---|---|
| Order intent | MISSING | IMPLEMENTED | Strategy + risk |
| Order validation gates | MISSING | IMPLEMENTED | Market/broker state |
| Paper trading | MISSING | IMPLEMENTED | Simulated execution |
| Assisted execution | MISSING | IMPLEMENTED | Broker adapter |
| Semi-automatic execution | MISSING | IMPLEMENTED | Broker + safeguards |
| Fully automated execution | MISSING | IMPLEMENTED behind explicit gate | Broker + safeguards |
| Order idempotency | MISSING | IMPLEMENTED | Durable order state |
| Fill reconciliation | MISSING | IMPLEMENTED | Broker execution reports |
| Position reconciliation | MISSING | IMPLEMENTED | Broker + portfolio |
| Kill switch | MISSING | IMPLEMENTED | Operational control |
| Daily loss limit | MISSING | IMPLEMENTED | Risk engine |
| Slippage controls | MISSING | IMPLEMENTED | Quotes/fills |
| Execution audit trail | MISSING | IMPLEMENTED | Durable audit |

## K. Platform / Cross-Market

| Capability | Current | Target | Data dependency |
|---|---|---|---|
| Market identity | PARTIAL | IMPLEMENTED | Exchange metadata |
| Instrument identity | PARTIAL | IMPLEMENTED | Instrument catalog |
| Market adapter | MISSING | IMPLEMENTED | Provider |
| Market capability profile | MISSING | IMPLEMENTED | Provider |
| Exchange calendar | MISSING | IMPLEMENTED | Market rules |
| Currency / timezone | PARTIAL | IMPLEMENTED | Market metadata |
| Corporate actions | PARTIAL | IMPLEMENTED | Corporate-action provider |
| Provider abstraction | PARTIAL | IMPLEMENTED | Provider |
| Multi-market watchlist | MISSING | IMPLEMENTED | Market registry |
| Cross-market comparison | MISSING | IMPLEMENTED | Normalized data |

## L. EGXBot Benchmark Notes

The benchmark list is based on the public EGXBot product/guide reviewed during the architecture audit. It should be treated as a feature reference, not as proof of internal implementation details.

Documented benchmark areas include:

- Telegram bot reports and notifications;
- EGX Terminal;
- Market Watch;
- professional charts;
- order book;
- Time & Sales;
- scanners;
- Fibonacci opportunities;
- SMC;
- Harmonic;
- classical patterns;
- Elliott;
- divergences;
- Gann;
- Volunacci;
- time analysis;
- signals with targets/stops/trailing behavior;
- signal tracking and deals;
- portfolio analysis;
- risk sizing;
- backtesting;
- AI research/market scans;
- AI portfolio analysis;
- daily briefings;
- what-if analysis.

For exact benchmark claims, use the current official EGXBot guide rather than this registry as the external source.

## Completion Rule

A capability is not considered complete merely because a class exists.

For each capability we require:

1. domain contract;
2. application orchestration;
3. infrastructure/data readiness where required;
4. deterministic tests;
5. integration tests where appropriate;
6. explainable output;
7. capability-readiness status;
8. documentation;
9. CI verification;
10. acceptance evidence.

The target is **full capability parity plus market-neutral reuse**, not a feature-count race.
