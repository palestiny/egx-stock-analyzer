# EGX Stock Analyzer — Project Blueprint

## 1. Project Identity

**Project Name:** EGX Stock Analyzer

**Project Type:** Automated Egyptian Exchange (EGX) Stock Analysis System

**Architecture Direction:** Modular Monolith

**Primary Goal:**
Build a reliable, explainable, and extensible system that automatically collects Egyptian Exchange stock data, analyzes it, evaluates opportunities, and produces actionable signals and reports.

---

## Project State & GitHub Synchronization

GitHub is the source of truth for the project's current state.

At the beginning of every development session, the project documentation
must be reviewed to understand:

- What the system is
- Why it is being built
- How it is being built
- Current architectural decisions
- Current milestone
- Completed work
- Open decisions
- Known risks
- Lessons learned

The primary documents to review are:

- PROJECT_BLUEPRINT.md
- PROJECT_RULES.md
- ENGINEERING_RULES.md
- ROADMAP.md
- DECISION_LOG.md
- LESSONS_LEARNED.md

### Synchronization Rule

Whenever a meaningful piece of work is completed and reaches a stable state,
it should be committed and pushed to GitHub.

The expected development cycle is:

Design
→ Test
→ Implement
→ Review
→ Refactor
→ Document
→ Commit
→ Push
→ Update Project State

GitHub should remain synchronized with the actual project state throughout
development rather than being updated only at major releases.

### Session Start Rule

Every new development session should begin by checking the project state
from GitHub before implementing new work.

The goal is to ensure that development continues from the documented state
rather than relying only on memory or previous conversation history.

---

# 2. Vision

The system is intended to become an automated decision-support platform for analyzing Egyptian Exchange stocks.

The system should be able to:

1. Collect market data.
2. Preserve and organize historical observations.
3. Evaluate data quality.
4. Perform technical analysis.
5. Perform fundamental analysis.
6. Evaluate momentum, liquidity, catalysts, and risk.
7. Calculate explainable scores.
8. Detect potential investment opportunities.
9. Generate signals and reports.
10. Support historical backtesting.
11. Eventually provide dashboards and automated alerts.

The system is **not intended to blindly predict the future**.

Its purpose is to transform market data into structured, explainable evidence that can support investment decisions.

---

# 3. Core Philosophy

The project follows these principles:

### 3.1 Data First

Reliable analysis depends on reliable data.

The system must distinguish between:

- Data received from an external source.
- Data accepted and stored by the system.
- Data whose quality has been evaluated.
- Data used by analysis.

External data should not automatically be treated as truth.

---

### 3.2 Explainability

Every important analytical result should have an understandable reason.

A signal such as:

```text
BUY
```

should eventually be explainable through factors such as:

```text
Technical Score: 26/30
Fundamental Score: 21/25
Momentum Score: 13/15
Liquidity Score: 12/15
Catalyst Score: 7/10
Risk Score: 4/5

Total: 83/100
```

The system should answer:

> "Why did the system produce this signal?"

---

### 3.3 Domain First

The core business/domain model should not depend directly on:

- FastAPI
- PostgreSQL/SQL Server
- External market-data providers
- UI frameworks
- AI providers
- Specific infrastructure technologies

Infrastructure should support the domain rather than define it.

---

### 3.4 AI Is a Tool, Not the Core

Artificial Intelligence may be introduced where it provides real value.

Examples may include:

- News interpretation.
- Catalyst detection.
- Financial document analysis.
- Classification.
- Anomaly detection.
- Natural-language reporting.

However, the fundamental architecture must remain functional without depending on a specific AI provider.

The system must be designed so that an AI component can be replaced without rewriting the core domain.

---

### 3.5 Automation

The long-term system flow is:

```text
Collect
   ↓
Validate / Assess Quality
   ↓
Analyze
   ↓
Score
   ↓
Rank
   ↓
Detect Opportunities
   ↓
Generate Report
   ↓
Send Alerts
```

Automation is a system capability, not the definition of the domain itself.

---

# 4. Problem Statement

Analyzing Egyptian Exchange stocks manually requires combining information from multiple sources and repeatedly performing similar analytical tasks.

The system aims to reduce this repetitive work by creating a consistent analytical pipeline.

The system should help answer questions such as:

- Which stocks currently have strong technical setups?
- Which stocks have strong fundamentals?
- Which stocks are gaining momentum?
- Which opportunities have acceptable risk?
- Why is one stock ranked above another?
- What changed compared with the previous analysis?
- How would the strategy have performed historically?

---

# 5. Target Outcome

The desired outcome is a system capable of producing results similar to:

```text
Stock: COMI

Signal: WATCH

Total Score: 72/100

Strengths:
- Strong medium-term trend
- Improving momentum
- High liquidity
- Healthy fundamentals

Risks:
- Price near resistance
- Risk/reward currently limited

Suggested Action:
Wait for confirmation / better entry
```

The exact scoring model and signal rules are **not yet final**.

---

# 6. Scope

## 6.1 In Scope

The project is expected to eventually include:

### Market Data

- Stock master data.
- OHLC data.
- Volume.
- Historical prices.
- Market observations.
- Data-source information.
- Data-quality assessment.

### Technical Analysis

Potential capabilities include:

- Trend detection.
- Support detection.
- Resistance detection.
- Moving averages.
- Momentum indicators.
- Volatility.
- Breakouts.
- Gaps.
- Technical patterns.

### Fundamental Analysis

Potential capabilities include:

- Revenue.
- Profitability.
- Earnings.
- Valuation.
- Debt.
- Growth.
- Financial ratios.
- Financial health.

### Scoring

A candidate scoring model currently under consideration:

| Category    |  Weight |
| ----------- | ------: |
| Technical   |      30 |
| Fundamental |      25 |
| Momentum    |      15 |
| Liquidity   |      15 |
| Catalysts   |      10 |
| Risk        |       5 |
| **Total**   | **100** |

This is a **working proposal**, not yet a final business rule.

---

### Signals

The system is expected to eventually support signals such as:

```text
BUY
WATCH
HOLD
AVOID
```

Additional information may include:

- Entry price.
- Stop loss.
- Target prices.
- Risk/reward ratio.
- Confidence/explanation.

The exact signal-generation rules remain to be designed.

---

### Historical Analysis

The system should eventually support:

- Backtesting.
- Historical signals.
- Strategy evaluation.
- Performance measurement.
- False-signal analysis.
- Risk analysis.

---

### Automation

The long-term system should automatically execute the analytical pipeline on a schedule.

---

### Reporting

The system should eventually generate:

- Daily market reports.
- Ranked stock lists.
- Opportunity reports.
- Alerts.
- Historical comparisons.

---

### API / Dashboard

These are later-stage capabilities.

The core domain must remain independent from the API and UI.

---

# 7. Out of Scope for the Initial Foundation

The following should not drive the initial architecture:

- Mobile application.
- Complex frontend.
- Automated trading execution.
- Broker integration.
- High-frequency trading.
- AI-first architecture.
- Complex microservices.
- Premature database optimization.
- Premature cloud infrastructure.
- Production-scale deployment before the domain is stable.

Automated trading execution may be considered in the future, but it is not part of the initial system foundation.

---

# 8. High-Level Architecture

The project is intended to follow a **Modular Monolith** architecture.

Conceptually:

```text
                    EGX Stock Analyzer
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       Domain          Application      Infrastructure
          │                │                │
          │                │                │
     Business Rules    Use Cases       External Systems
          │                │                │
          │                │        ┌───────┼────────┐
          │                │        │       │        │
          │                │      Market   Database  AI
          │                │      Data
          │                │
          └────────────────┴───────────────────────
```

The exact module boundaries will be refined during architecture design.

---

# 9. Initial Domain Direction

The domain currently contains the concept of:

```text
Stock
```

A stock represents a business entity traded on the Egyptian Exchange.

Current conceptual distinction:

```text
Stock
│
├── Internal Identity
│
├── Symbol
│
└── Name
```

The system also contains the concept of:

```text
Market Data
```

Market Data represents an observation received from an external market-data source.

Important architectural distinction:

```text
External Source
       ↓
Data Ingestion
       ↓
Market Observation
       ↓
Data Quality Assessment
       ↓
Analysis
```

The exact responsibilities of each component are still under design.

---

# 10. Market Data Philosophy

Market data is external information.

Therefore the system should avoid confusing:

```text
"Data received from provider"
```

with:

```text
"Data proven to be correct"
```

The architecture should allow the system to:

1. Preserve the received observation.
2. Evaluate its quality.
3. Detect suspicious or invalid observations.
4. Decide whether the observation can be used for a particular analysis.

The system should avoid silently destroying potentially useful external observations merely because they violate an assumption.

For example, price gaps may be legitimate market behavior and should not automatically be interpreted as data errors.

Detailed validation rules will be designed separately.

---

# 11. Major Future Modules

The following modules are candidates for the modular monolith:

```text
Stock Management
Market Data
Data Quality
Technical Analysis
Fundamental Analysis
Scoring
Signal Generation
Backtesting
Reporting
Alerts
Automation
```

These are architectural directions, not all committed implementation modules.

Each module must earn its existence through actual domain responsibility.

---

# 12. Analysis Pipeline

The target analytical pipeline is:

```text
                Market Data
                     │
                     ▼
              Data Quality
                     │
                     ▼
             Technical Analysis
                     │
                     ├──────────────┐
                     ▼              ▼
            Fundamental Analysis  Momentum
                     │              │
                     └──────┬───────┘
                            ▼
                       Scoring
                            │
                            ▼
                     Signal Generation
                            │
                            ▼
                         Ranking
                            │
                            ▼
                       Reporting
                            │
                            ▼
                         Alerts
```

The final pipeline may change as the domain becomes clearer.

---

# 13. Quality Requirements

The system should prioritize:

### Correctness

Business rules must be deterministic and testable.

### Explainability

Important decisions should have traceable reasons.

### Extensibility

New analytical strategies should be addable without rewriting unrelated modules.

### Replaceability

External providers and AI implementations should be replaceable.

### Testability

Domain logic should be testable without requiring:

- Database
- API server
- External market provider
- Network
- AI service

### Observability

The system should eventually make it possible to understand:

- What happened?
- When did it happen?
- Which data was used?
- Which rules were applied?
- What result was produced?

---

# 14. Testing Strategy

The project follows:

```text
RED
 ↓
GREEN
 ↓
REVIEW
 ↓
REFACTOR
```

Tests should be written around behavior rather than implementation details.

Priority:

```text
Domain Tests
    ↓
Application Tests
    ↓
Integration Tests
    ↓
Infrastructure Tests
    ↓
End-to-End Tests
```

The current project already has domain tests and the test suite is passing.

Current known baseline:

The exact test count is maintained by CI; this document does not hard-code a stale baseline.

---

# 15. Development Methodology

The project follows:

```text
UNDERSTAND
    ↓
MAP
    ↓
DESIGN
    ↓
DISCUSS TRADE-OFFS
    ↓
DECIDE
    ↓
TEST
    ↓
IMPLEMENT
    ↓
REVIEW
    ↓
REFACTOR
    ↓
DOCUMENT
    ↓
LEARN
    ↓
UPDATE THE MAP
```

No major architectural decision should be made merely because it is convenient to implement.

---

# 16. Design Gate

Before implementing a major concept, answer:

### Concept

What is it?

### Meaning

What does it represent in the business/domain?

### Responsibility

What is it responsible for?

### Non-Responsibility

What must it explicitly not do?

### Ownership

Who owns its state and behavior?

### Boundary

Which module does it belong to?

### Alternatives

What other designs were considered?

### Trade-offs

What do we gain and what do we sacrifice?

### Assumptions

What are we currently assuming?

### Open Decisions

What is still unknown?

### Committed Decisions

What have we explicitly decided?

Only after this gate should implementation begin.

---

# 17. Current Architecture Decisions

The following decisions are currently considered committed:

### Stock

- Stock is an Entity.
- Stock has an internal UUID identity.
- Stock symbol is an external/business identifier.
- Stock name is descriptive information.
- Symbols are normalized using trim + uppercase.
- Names are normalized using trim.
- `create()` generates a new UUID.
- `reconstitute()` restores an existing UUID.
- Entity equality is based on identity.

### Architecture

- The project is moving toward a Modular Monolith.
- Domain logic should remain independent from infrastructure.
- AI is not the core of the system.
- The system should prioritize explainability.

---

# 18. Current Open Decisions

The following decisions remain open and must not be treated as final:

### Market Data

- Exact ownership of market observations.
- Validation responsibilities.
- Data-quality model.
- Valid / suspect / invalid semantics.
- Handling conflicting providers.
- Handling missing observations.
- Duplicate observations.
- Timezone strategy.
- Market-session semantics.

### Scoring

- Exact scoring formulas.
- Normalization.
- Weight calibration.
- Thresholds.
- Interaction between categories.
- Stock Quality vs Entry Quality.

### Signals

- Exact BUY/WATCH/HOLD/AVOID rules.
- Confidence model.
- Entry calculation.
- Stop-loss calculation.
- Target calculation.

### Data Providers

- Primary market-data source.
- Backup source.
- Provider abstraction.
- Provider reliability strategy.

### Persistence

- Database technology.
- Repository implementation.
- Historical data storage strategy.

These decisions should be made deliberately rather than implicitly through implementation.

---

# 19. Roadmap

## M0 — Vision & Project Blueprint

Establish:

- Vision.
- Scope.
- Architecture direction.
- Engineering rules.
- Documentation structure.
- Major open decisions.

**Current phase.**

---

## M1 — Domain Foundation

Define and test:

- Stock.
- Market Data concepts.
- Data Quality concepts.
- Core domain boundaries.
- Domain value objects where justified.

---

## M2 — Market Data Foundation

Establish:

- Market observation model.
- Historical observations.
- Data-source abstraction.
- Data-quality assessment.

---

## M3 — Data Acquisition

Implement:

- External provider integration.
- Data ingestion.
- Provider failure handling.
- Raw data preservation.

---

## M4 — Data Quality

Implement:

- Validation rules.
- Quality classification.
- Missing-data handling.
- Duplicate detection.
- Conflict detection.

---

## M5 — Technical Analysis

Implement:

- Trend.
- Support/resistance.
- Momentum.
- Volatility.
- Technical indicators.

---

## M6 — Fundamental Analysis

Implement:

- Financial metrics.
- Ratios.
- Growth.
- Profitability.
- Valuation.

---

## M7 — Scoring Engine

Implement:

- Category scores.
- Weighting.
- Normalization.
- Explainable scoring.

---

## M8 — Signal Generation

Implement:

- BUY.
- WATCH.
- HOLD.
- AVOID.
- Entry.
- Stop loss.
- Targets.
- Risk/reward.

---

## M9 — Backtesting

Implement:

- Historical simulation.
- Strategy performance.
- Drawdown.
- Win/loss statistics.
- Signal quality analysis.

---

## M10 — Automation

Implement:

```text
Scheduled Collection
        ↓
Analysis
        ↓
Scoring
        ↓
Signal Generation
```

---

## M11 — Reporting & Alerts

Implement:

- Daily reports.
- Ranked opportunities.
- Notifications.
- Change detection.

---

## M12 — API & Dashboard

Expose:

- Stocks.
- Analysis.
- Scores.
- Signals.
- Reports.
- Historical performance.

---

## M13 — Production Hardening

Address:

- Security.
- Monitoring.
- Logging.
- Reliability.
- Deployment.
- Performance.
- Recovery.
- Operational procedures.

---

# 20. Documentation Structure

The project documentation should evolve into:

```text
docs/
├── PROJECT_BLUEPRINT.md
├── PROJECT_RULES.md
├── ENGINEERING_RULES.md
├── ROADMAP.md
├── DECISION_LOG.md
├── LESSONS_LEARNED.md
└── ADR/
```

Additional documentation may later be organized as:

```text
docs/
├── features/
├── domain/
├── integrations/
├── data/
├── security/
└── operations/
```

Documentation should describe actual project decisions and should not become a collection of hypothetical architecture.

---

# 21. Definition of Success

The project is successful when it can:

1. Reliably collect EGX stock data.
2. Preserve historical observations.
3. Assess data quality.
4. Analyze stocks consistently.
5. Produce explainable scores.
6. Generate explainable signals.
7. Backtest its strategy.
8. Run automatically.
9. Produce useful reports.
10. Evolve without major architectural rewrites.

The final goal is not simply:

> "Build an application that gives stock signals."

The deeper goal is:

> Build an engineering system that transforms external financial data into reliable, explainable, testable, and continuously improvable analytical decisions.

---

# 22. Guiding Principle

The project should be developed as an engineering system first and a feature collection second.

Every new feature should answer:

```text
Why does this exist?
What problem does it solve?
Who owns it?
What does it depend on?
What does it not know?
How can it be tested?
What are the trade-offs?
```

If these questions cannot be answered clearly, implementation should wait.

---

# 23. Project State & GitHub Synchronization

GitHub is the source of truth for the project's current state.

At the beginning of every development session, the project documentation
must be reviewed to understand:

- What the system is
- Why it is being built
- How it is being built
- Current architectural decisions
- Current milestone
- Completed work
- Open decisions
- Known risks and lessons learned

The primary documents to review are:

- PROJECT_BLUEPRINT.md
- PROJECT_RULES.md
- ENGINEERING_RULES.md
- ROADMAP.md
- DECISION_LOG.md
- LESSONS_LEARNED.md

### Synchronization Rule

Whenever a meaningful piece of work is completed and reaches a stable state,
it should be committed and pushed to GitHub.

The expected development cycle is:

Design
→ Test
→ Implement
→ Review
→ Refactor
→ Document
→ Commit
→ Push
→ Update Project State

GitHub should therefore remain synchronized with the actual project state
throughout development rather than being updated only at major releases.

### Session Start Rule

Every new development session should begin by checking the project state
from GitHub before implementing new work.

The goal is to ensure that development continues from the documented state
rather than relying on memory or conversation history.

---

**Document Status:** Foundational blueprint — maintained

**Current Implementation:** M44 — Execution Reliability & History complete and CI-validated through PR #102.

**Current Project State:** M44 completion is recorded in `docs/M44-EXECUTION-RELIABILITY-AND-HISTORY-MVP-COMPLETION.md`. The M44 design, implementation, CI validation, and roadmap are synchronized.

**Next Step:** No next capability is committed yet. The next major capability must begin with a new design gate.
