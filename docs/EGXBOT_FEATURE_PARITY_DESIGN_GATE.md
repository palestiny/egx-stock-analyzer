# EGXBot Feature Parity — Design Gate

**Status:** Proposed implementation boundary  
**Date:** 2026-10-04  
**Repository:** palestiny/egx-stock-analyzer

## Objective

Expand EGX Stock Analyzer into a professional EGX research and decision-support platform with functional coverage comparable to the current public EGXBot product, while preserving this project's explainability, deterministic testing, provider-neutral boundaries, and no-broker-execution rule.

The target is feature parity by capability, not a copy of EGXBot's implementation or UI.

## Capability Inventory

The current public EGXBot documentation exposes three surfaces: Telegram bot, live terminal, and AI assistant.

### Market and discovery
- market overview / EGX pulse
- gainers / losers
- leaders and laggards
- sectors and sector rotation
- liquidity pulse
- smart and technical scanners
- Fibonacci opportunity scanner
- breakout scanner
- whale / large-flow detection
- global indices
- FX, gold and commodities
- market news

### Stock research
- brief stock report
- full technical analysis
- financial/fundamental report
- fair-value estimate
- candlestick charts
- support/resistance
- trend state
- risk analysis
- multi-timeframe analysis
- price targets
- stop-loss planning
- scenario analysis

### Advanced technical analysis
- Fibonacci
- divergence
- chart patterns
- Harmonic patterns
- Smart Money Concepts
- Elliott-wave analysis
- Gann/time-cycle analysis
- fractal analysis
- volume/order-flow analysis
- EGX Sniper-style confluence analysis

### Intraday / market microstructure
- live market watch
- order book / market depth
- time & sales
- price-level buy/sell aggregation
- intraday signals
- session opportunities
- liquidity monitoring

### Signals and alerts
- structured buy/sell signals
- entry
- TP1/TP2/TP3
- stop-loss
- signal lifecycle
- unusual volume
- breakout
- multi-indicator confluence
- pattern/Fibonacci state-change alerts
- price alerts
- push/Telegram notifications

### Portfolio
- holdings
- broker-trade recording
- average cost
- market value
- P&L
- concentration
- sector exposure
- portfolio health score
- portfolio risk score
- per-position verdict
- EGX30 context
- sector rotation impact
- what-if analysis
- daily pre-market portfolio briefing
- screenshot portfolio import

### Strategy research
- backtesting
- stock comparison
- bounded rule testing
- tracked ideas
- signal track record
- model portfolio
- copy-trading style notifications without automatic execution

### AI research assistant
- natural-language stock research
- market scans
- portfolio questions
- what-if questions
- Arabic/English symbol and intent understanding
- explainable evidence references
- persistent portfolio context

## Architectural Decision

Do not turn the current modular monolith into microservices.

Keep:

```
React / API / future Telegram adapter
          ↓
Application capabilities
          ↓
Domain analytical engines
          ↓
Provider-neutral ports
          ↓
Market / financial / news / notification infrastructure
          ↓
SQLite first; replaceable durable infrastructure
```

New capabilities must remain independently testable and must not leak provider-specific logic into domain rules.

## Capability Model

Introduce a capability-oriented application layer. Each feature family owns its orchestration but reuses shared domain primitives.

Core capability families:

1. market_intelligence
2. stock_research
3. technical_analysis
4. fundamental_analysis
5. signals
6. alerts
7. portfolio
8. scanners
9. market_microstructure
10. news
11. strategy_research
12. ai_assistant
13. notifications

No capability may silently execute a real broker order.

## Data Readiness Rule

A feature is not implemented merely because a calculation exists.

Every capability must declare:
- required data;
- freshness requirement;
- historical requirement;
- provider/source;
- quality contract;
- missing-data behavior;
- explainability payload;
- deterministic test fixture;
- live/external integration status.

Order-book features, for example, cannot be marked production-ready using daily OHLCV data.

## Canonical Signal Contract

All actionable analytical signals use one canonical structure:

```
Signal
  symbol
  direction
  status
  generated_at
  timeframe
  entry_zone
  invalidation / stop
  targets[]
  confidence
  risk_score
  evidence[]
  strategy_id
  strategy_version
  data_timestamp
```

A signal is informational. It never implies broker execution.

## Portfolio Boundary

Portfolio analysis remains separate from execution.

The portfolio layer owns:
- positions;
- lots/trades;
- average cost;
- realized/unrealized P&L;
- exposure;
- concentration;
- risk;
- analysis snapshots.

Broker integrations, if introduced later, require a separate execution/security design gate.

## AI Boundary

AI is an interface and reasoning assistant, not the source of market truth.

AI may interpret requests, select approved analytical tools, summarize deterministic results, compare scenarios, and explain evidence.

AI may not invent prices, override deterministic risk rules, fabricate missing data, claim backtest performance without an accepted dataset, or execute trades.

## Delivery Strategy

Implement vertical slices rather than a giant rewrite.

### Phase A — Foundation
- capability registry/contracts
- shared signal model
- market snapshot/read model
- scanner query contract
- alert contract
- portfolio analytics contract
- feature readiness metadata

### Phase B — High-value parity
- market overview
- stock full report
- support/resistance + trend
- Fibonacci
- scanners
- signals
- alerts
- portfolio + P&L
- stock comparison
- financial report + fair value

### Phase C — Advanced analysis
- divergence
- chart patterns
- Harmonic
- SMC
- Elliott
- Gann
- fractals
- multi-timeframe confluence

### Phase D — Intraday
- market watch
- order book
- time & sales
- price aggregation
- liquidity pulse
- intraday signal lifecycle

### Phase E — Intelligence
- news
- sector rotation
- global markets
- AI assistant
- portfolio screenshot import
- daily briefing
- what-if analysis

### Phase F — Research validation
- strategy comparison
- bounded backtesting
- track record
- model portfolio
- reproducibility reports

## Non-Goals

This gate does not authorize automatic broker execution, guaranteed investment advice, unsupported real-time data claims, accepting current M61 historical performance without real evidence, copying proprietary EGXBot source code, or replacing the current domain architecture wholesale.

## Acceptance Rule

A feature is **Implemented** only when:
1. design/contract exists;
2. deterministic tests exist;
3. application boundary is wired;
4. API/UI behavior is covered where applicable;
5. data readiness is explicitly classified;
6. documentation states limitations;
7. CI passes.

A feature is **Production Ready** only when its required external data source and operational behavior are verified.

## First Implementation Slice

The first slice is capability foundation + canonical Signal contract + feature-readiness metadata. This creates the common platform needed by scanners, alerts, advanced analysis, and AI without prematurely implementing provider-specific integrations.
