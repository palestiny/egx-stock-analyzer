# Comprehensive Technical & News Intelligence — Design Gate

**Status:** Design proposal; implementation not started  
**Milestone:** Proposed follow-on to M61, not a replacement for M61  
**Branch:** `design/comprehensive-technical-news-analysis`  
**Scope:** EGX equities, daily analysis first, multi-timeframe extensions when source coverage supports them

## 1. Goal

Extend EGX Stock Analyzer from isolated technical signals into an explainable, multi-evidence analysis workspace that combines:

1. price/volume structure and market regime;
2. classic indicators and moving averages;
3. Japanese candlestick patterns;
4. Fibonacci retracements/extensions and swing structure;
5. Elliott Wave candidate counts;
6. support/resistance and breakout/failure context;
7. company disclosures, corporate actions, macroeconomic news, and reputable financial news;
8. an evidence-based scenario report, risk levels, invalidation conditions, and optional alert candidates.

The system must explain the evidence and uncertainty. It must not claim that any one tool predicts the market or that a composite score guarantees a profitable trade.

## 2. Current baseline and boundaries

The current repository already has technical/fundamental analysis, scoring, explainable technical scanners, a saved-snapshot dashboard, a stock regime/risk endpoint (including SMA20/SMA50, realized volatility and observed drawdown), and a backtest simulator. The pre-breakout scanner is a watchlist, not a buy signal, and may use a stale saved analysis snapshot.

This design must reuse the current domain-first modular monolith and existing application/domain/infrastructure boundaries. It must not bypass authenticated API access, existing stock-data quality checks, persistence contracts, or source-provider abstraction. The current M61 historical-data acceptance blocker remains active; this feature must not be used to imply that a strategy has been validated.


## 2.1 Verified code inventory (reviewed on 2026-10-26)

The current `main` source tree was inspected before proposing implementation:

- `app/domain/technical_analysis/trend.py`: detects higher/lower swing highs and lows; it is a structural swing-trend classifier, not a moving-average indicator engine.
- `app/domain/technical_analysis/support_resistance.py`: returns pivot-low support and pivot-high resistance evidence from adjacent bars; it does not yet cluster zones, score touches, or calculate Fibonacci levels.
- `app/domain/technical_analysis/momentum.py`: computes rate of change over a supplied lookback.
- `app/domain/technical_analysis/volume.py`: current volume evidence is a separate component.
- `app/domain/technical_analysis/orchestrator.py` composes trend, support/resistance, momentum, and volume into `TechnicalAnalysisResult`.
- `app/domain/market_data/price_bar.py` supplies timezone-aware OHLCV bars, and `app/domain/market_data/data_quality_assessor.py` is an existing quality boundary to preserve.
- The separate stock-regime diagnostic already exposes SMA20/SMA50 and risk statistics, but it is not a general indicator registry and does not establish that SMA200 is available in the core technical-analysis result.
- The inspected `app/domain/technical_analysis` tree contains no dedicated news/event, candlestick-pattern, Fibonacci, or Elliott Wave module at this baseline.

**Implication:** the first increment is not “turn on all indicators”; it is to define a small, testable indicator evidence contract and calculate SMA/EMA values from validated, chronologically ordered bars, including explicit warm-up/insufficient-history states. Reuse existing data-quality and domain boundaries rather than duplicating or silently changing the stock-regime endpoint.

## 3. Proposed capability catalogue

### 3.1 Trend, averages, and momentum

Initial daily indicators, subject to valid history and data-quality checks:

- SMA 20, 50, 100, and 200; explicitly requested SMA50/SMA200 are first-class.
- EMA 9, 20, 50, and 200.
- Price-versus-average state, average slope, crossovers, and separation/extension from averages.
- RSI (14), MACD (12,26,9), ADX/DMI (14), ATR (14), Bollinger Bands (20,2), Stochastic (14,3,3), CCI (20), and Ichimoku components.
- Volume versus rolling baselines, OBV and MFI when reliable volume exists.
- VWAP only for intraday data with suitable session bars; never fabricate it from daily bars.
- Multi-timeframe summaries (daily/weekly/monthly) only when the aggregation is reproducible and sufficient history is available.

Indicator definitions, warm-up periods, missing-bar behavior, price-adjustment assumptions, and rounding must be explicit and tested. A missing or invalid input yields an unavailable state with a reason, not a guessed value.

### 3.2 Price action, levels, and Fibonacci

- Swing pivots and support/resistance zones from reproducible rules, with source bars and lookback windows.
- Breakout, retest, rejection, failed breakout, gap, and range context.
- Fibonacci retracement levels (commonly 23.6%, 38.2%, 50%, 61.8%, 78.6%) and extension levels, calculated from explicitly identified swing endpoints.
- Show the selected high/low, dates, timeframe, direction, method, and alternative plausible anchors when swing selection is ambiguous.
- Do not present a Fibonacci line as support/resistance unless price behavior supplies corroborating evidence.
- Volume profile/fixed-range volume distribution is deferred until suitable price/volume granularity and a defensible methodology are available.

### 3.3 Japanese candlesticks

Recognize common single-, two-, and three-candle patterns, including doji, hammer/inverted hammer, shooting star, bullish/bearish engulfing, harami, piercing/dark-cloud cover, morning/evening star, and three-soldiers/three-crows patterns where definitions can be made deterministic.

Each detection must expose the exact candle dates/OHLC, body/shadow ratios, pattern rule, preceding trend/context, nearby levels, volume context, and whether a later candle confirmed or invalidated it. A candle name alone is never a trading signal. Pattern definitions and tolerances must be unit-tested against positive, negative, edge, and malformed fixtures.

### 3.4 Elliott Wave

Provide **candidate wave counts**, not an asserted objective truth:

- detect and display candidate swing sequences and degree/timeframe;
- show primary and alternate counts when more than one interpretation is plausible;
- state rule checks, assumptions, confidence/ambiguity, key invalidation level, and data coverage;
- separate mechanically verifiable Elliott constraints from analyst judgment;
- never hide competing counts merely to produce a confident conclusion.

Elliott labeling is subjective and especially vulnerable to hindsight. It must remain a separately identified analysis module and must be evaluated for reproducibility before its output contributes to a composite score.

### 3.5 News and event intelligence

Build a provider-neutral news/disclosure ingestion boundary. Candidate source classes, in priority order:

1. official EGX disclosures and company announcements;
2. company investor-relations releases and official corporate-action notices;
3. relevant Egyptian macroeconomic / regulatory announcements (including CBE and government sources);
4. reputable financial news providers with permitted access and retention terms.

Before integrating a specific source, document availability, licensing/terms, attribution requirements, rate limits, update latency, coverage, language, and historical archive limitations. Do not scrape or redistribute content in violation of source terms. Store article metadata and short factual summaries where permitted, with source URL and attribution; avoid storing full article text unless licensed.

Each news item should retain:
- provider/source and canonical URL;
- published time, timezone, retrieved time, and first-seen time;
- language, headline, permitted excerpt/summary, and article fingerprint for deduplication;
- affected company/symbols and entity-match confidence;
- event category (earnings/results, dividends, rights/splits, acquisitions, contracts, management, litigation/regulatory, macro/rates/FX, sector, market-wide, rumor/unverified);
- evidence-backed direction/impact assessment, uncertainty, and the supporting source text or citation;
- event validity/expiry and revision/correction state.

Distinguish **published time** from **retrieved time**. Backtests must only expose information that was actually public by the simulated decision time. Late articles, corrected headlines, undated items, and sources without trustworthy timestamps must be excluded from point-in-time strategy tests or marked ineligible.

News sentiment is not sufficient by itself. Prefer event classification and factual extraction first; keep sentiment/LLM interpretation as a separately scored, cited and uncertainty-aware layer. The system must not invent facts, causality, price targets, or company associations. Conflicting reports remain visible as conflicts.

### 3.6 Cross-evidence report

For a stock and analysis timestamp, return a structured report with:

- data coverage, latest market bar, source, freshness, adjustment status, missing sessions, and data-quality warnings;
- market/sector regime where available;
- trend and moving-average structure;
- momentum, volatility, volume/liquidity and risk diagnostics;
- support/resistance zones, Fibonacci anchors/levels, candle detections, and Elliott candidate counts;
- relevant news/events with source links and publication timestamps;
- bullish/base/bearish scenarios, each with supporting and conflicting evidence;
- conditional entry area only if rules and data support it, invalidation/stop reference, target zones, risk/reward assumptions, and expected horizon;
- evidence freshness, uncertainty/confidence by component, and reasons a component is unavailable;
- explicit separation between observed facts, deterministic calculations, heuristic interpretations, and AI-generated summaries.

The report must be allowed to say “insufficient evidence”, “conflicting evidence”, or “no setup”. It must not force a buy/sell label.

## 4. Composite scoring policy

Do not immediately combine every tool into one opaque score. First publish component-level evidence and independent scores.

If a composite is later justified:
- version the formula and parameters;
- normalize components without allowing unavailable inputs to silently become zero or neutral;
- avoid double-counting correlated indicators (e.g., SMA cross, MACD, and trend may describe the same underlying move);
- separate technical setup quality, market regime, liquidity/execution risk, data quality, and news/event risk;
- use explicit penalties/blocks for stale bars, unresolved corporate actions, insufficient history, suspension, and material unresolved news;
- show the contribution of every component;
- validate on immutable datasets with point-in-time news, fees/slippage, survivorship and corporate-action controls, disjoint time-based holdouts, and symbol-level breakdowns before using scores to rank opportunities.

No threshold or weight is accepted as predictive merely because it sounds plausible. M61's historical dataset acceptance gate remains a prerequisite for credible strategy-performance claims.

## 5. Proposed architecture

Keep the modular monolith and add bounded capabilities behind existing application/domain/infrastructure boundaries:

- **Market data normalization and quality:** normalized bars, freshness, gaps, corporate-action/adjustment status, provenance.
- **Technical indicators:** deterministic calculation services with versioned parameters.
- **Price-structure analysis:** pivots, zones, Fibonacci anchors and price-action events.
- **Candlestick pattern registry:** deterministic rules and evidence objects.
- **Elliott candidate analyzer:** separate, explicitly heuristic module with alternate counts.
- **News provider adapters:** source-specific acquisition, rate limits, attribution and timestamp normalization.
- **News/event domain:** deduplication, entity linking, event taxonomy, point-in-time eligibility and evidence references.
- **Analysis orchestration:** combines component results without letting one module mutate another's facts.
- **Report/query layer:** authenticated, read-oriented API and dashboard presentation.
- **Persistence:** explicit versioned schemas; raw source facts and normalized analysis remain distinguishable.
- **Alerts:** later consumer of validated, versioned analysis outputs; Telegram delivery must not be coupled into indicator calculations.

Do not add a new database, queue, broker, or external LLM dependency without a separate trade-off and operational design gate. Start with current storage/provider abstractions unless implementation evidence shows they cannot satisfy retention, query, or reliability needs.

## 6. Phased delivery plan

### Phase A — Data contracts and indicator foundation
- Inventory current bar schema, data-quality assessor, provider capabilities, historical persistence and API conventions.
- Define indicator result/evidence contracts, lookback requirements, warm-up and missing-data semantics.
- Implement/test SMA200 and EMA/indicator calculations in small TDD increments, reusing SMA20/SMA50 behavior where valid.
- Add data freshness and corporate-action warnings to the analysis output.

### Phase B — Price action and chart-pattern evidence
- Implement deterministic swing pivots and support/resistance zones.
- Implement Fibonacci levels tied to identified swings.
- Implement a small, tested candlestick registry; expand coverage only after semantics are stable.
- Add multi-timeframe summaries after daily behavior is accepted.

### Phase C — News ingestion and event context
- Compare sources by legal access, cost, EGX coverage, timestamps, history and reliability.
- Start with official disclosures and provider adapters; persist metadata and event evidence.
- Add company/entity linking, deduplication, source links, timestamps and event categories.
- Build a current-news report before using news in historical backtests.
- Add point-in-time news snapshots only when publication timestamps and retention rights are sufficient.

### Phase D — Scenario report and dashboard
- Present component-level evidence, contradictory evidence, alternative scenarios, data freshness, and invalidation levels.
- Do not silently change existing scanner ranking or existing opportunity scores.
- Show stale/missing data and unavailable components explicitly.

### Phase E — Elliott Wave candidates
- Prototype a deterministic swing-based candidate generator with alternate counts.
- Measure inter-run reproducibility and compare to manually reviewed examples.
- Keep it advisory and outside composite scoring until validated.

### Phase F — Research validation and alerts
- Add point-in-time backtests for component rules and combined rules.
- Include costs, liquidity constraints, corporate actions, data gaps, and disjoint holdouts.
- Only then consider composite scoring and Telegram alerts with entry zone, targets, invalidation, horizon, evidence, and timestamp.

## 7. Acceptance criteria

The design is ready for implementation only when:
- [ ] Existing API and dashboard behavior remains backward compatible.
- [ ] Every metric and pattern has deterministic, documented semantics and tests.
- [ ] Every output is traceable to input bars/events, timestamps, source, and rule version.
- [ ] Insufficient/stale/invalid data never produces fabricated levels or confidence.
- [ ] Elliott outputs include alternatives and invalidation rules.
- [ ] News summaries have source links, publication times, entity-match evidence and uncertainty.
- [ ] Point-in-time tests prevent look-ahead leakage from both price data and news.
- [ ] Corporate-action and suspicious-price discontinuity warnings are visible.
- [ ] Composite scores are explainable and not enabled as predictive claims before holdout validation.
- [ ] Authentication, ownership boundaries, persistence versioning, observability and failure handling follow existing project conventions.
- [ ] A provider/source decision record covers cost, legal rights, coverage, reliability and fallback behavior.
- [ ] No existing scanner or ranking is silently altered.

## 8. Main risks and mitigations

| Risk | Mitigation |
|---|---|
| Too many indicators create conflicting signals | Show component evidence; account for correlation; do not force a single answer |
| Elliott Wave subjectivity | Alternate counts, rule checks, invalidation levels, separate confidence |
| News latency or timestamp errors | Preserve published/retrieved/first-seen times; exclude ineligible data from backtests |
| Incorrect company/news matching | Confidence thresholds, human-review state, canonical company identities |
| Unadjusted bars distort levels and returns | Corporate-action status, anomaly warnings, data acceptance gate |
| Data-provider cost or license restrictions | Source evaluation before adapter selection; store only permitted content |
| Overfit weights and thresholds | Immutable datasets, walk-forward/disjoint holdouts, costs and per-symbol reporting |
| AI-generated false claims | Cite source evidence, preserve original facts, uncertainty and conflict handling |
| Performance/operational growth | Bounded adapters, caching/retention policies and a separate scale gate if needed |

## 9. Decisions and open items

### Recommended defaults
- Daily time frame first; weekly/monthly summaries after aggregation tests.
- Official disclosures first for news, then a replaceable reputable news adapter selected after a source/terms review.
- Deterministic indicators and candle patterns before AI interpretation.
- Elliott Wave stays advisory and separate.
- Component evidence before any composite score.
- No strategy score or Telegram recommendation becomes active until validated and explicitly reviewed.

### Open items to resolve during implementation design
- Exact market/news provider(s), pricing, terms and historical archive.
- Whether any existing upstream source provides trustworthy adjusted bars and corporate-action history.
- Exact candle-pattern definition library and tolerance policy.
- Whether news analysis uses a local/model-neutral NLP port, an external model, or rules first.
- Historical-news dataset availability and permissible retention.
- Desired analysis refresh cadence and latency budget.
- Which report elements are included in the first dashboard slice.

## 10. Status

**Design gate status: PROPOSED — core calculation and several integration slices are implemented on open PR branches; end-to-end release is incomplete.**

PR #350 (`feature/technical-indicator-foundation`) has passed all five CI jobs on its latest reviewed head (run #40368474901), including VWAP input-validation tests after correcting a weighted-average expectation. It supplies SMA/EMA, Wilder RSI, MACD, Bollinger Bands, ATR, Stochastic, CCI, OBV, MFI, directional movement/ADX, Ichimoku components, selected candle patterns, Fibonacci retracements/extensions, and session-scoped VWAP. PR #355 integrates indicator evidence into analysis/API and PR #357 adds the dashboard chart; an updated PR #355 head is under a fresh CI run after the stack was refreshed, so its earlier failures must not be treated as cleared until the current run passes.

PR #359 provides confirmed swing-point detection with right-bar confirmation and has a passing CI run for its latest reviewed head. PR #360 adds a broader deterministic candlestick registry (including engulfing, harami, piercing/dark-cloud, morning/evening star, and three-soldier/crow patterns); its current refreshed head is under CI review. PR #354 now builds deterministic five-wave impulse candidates from alternating confirmed swing points, records rule violations and truncated-fifth warnings, and exposes a wave-2 invalidation boundary. It passed CI on its latest reviewed head. This is still not a complete Elliott interpretation engine: corrective-wave alternatives, broader alternate-count generation/ranking, chart annotations, and historical validation remain open.

PR #353 contains point-in-time news-event metadata and durable SQLite storage/querying; PR #361 adds a provider-neutral ingestion orchestration port and has passed CI. No live news source has yet been selected, licensed, configured, or verified, and company matching/event impact interpretation are not complete. The Telegram opportunity-delivery chain (PRs #346, #348, #349, #351, #352, and #358) and session opportunity ledger (PR #356) have passing CI on their reviewed heads, but remain open and have not been released as a complete end-to-end product.

Before release, refresh and verify every dependent PR against its latest base, consolidate API/dashboard changes, validate full Telegram lifecycle and server-side entitlements end-to-end, connect the finalized session calendar/report flow, select and verify licensed news providers, complete the owner dashboard/personal portfolio and payment reconciliation design, and pass accepted historical backtesting. M61 historical-data acceptance remains a release blocker for profitability/performance claims. All listed PRs remain proposals until reviewed and explicitly approved for merge; CI success alone does not constitute release acceptance.
