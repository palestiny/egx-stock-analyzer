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

This section records the stable architectural foundation only. Milestone-specific decisions are authoritative in `docs/DECISION_LOG.md` and their design/completion documents.

### Architecture

- The project is a **Modular Monolith**.
- Domain logic remains independent from FastAPI, React, SQLite, Yahoo Finance, Telegram, and authentication/transport implementations.
- Application capabilities own use-case orchestration and business-facing boundaries.
- Infrastructure owns external providers, persistence, authentication adapters, and operational integrations.
- API and dashboard layers are transport/presentation boundaries and must not reproduce domain or application business rules.
- AI is a replaceable tool, not the system's core domain or architecture.
- GitHub is the source of truth for project state.

### Stock Identity

- `Stock` is a domain Entity.
- Stock identity is an internal UUID.
- Symbol is the external/business identifier and is normalized with trim + uppercase.
- Name is descriptive information and is normalized with trim.
- `create()` generates identity; `reconstitute()` restores identity.
- Entity equality is identity-based.

### Current Operational Architecture

The implemented system includes deterministic stock analysis, configured-market execution, opportunity ranking/views, historical analysis capabilities, alert delivery, scheduled workflows, durable workflow reliability/history, multi-user identity/authentication, credential management, and management/user audit read models.

M48 cross-execution scheduled-workflow history is complete. The accepted design is implemented and merged through PR #118; see `docs/ROADMAP.md`, `docs/DEC-110-M48-SCHEDULED-WORKFLOW-CROSS-EXECUTION-HISTORY-DESIGN-GATE.md`, and `docs/M48-SCHEDULED-WORKFLOW-CROSS-EXECUTION-HISTORY-MVP-COMPLETION.md`.

---

# 18. Current Open Decisions

Open decisions are **not maintained as a static list in this blueprint**, because many earlier questions have already been resolved through milestone design gates.

The authoritative current decision state is maintained by:

- `docs/ROADMAP.md` for milestone position and execution order;
- `docs/DECISION_LOG.md` for accepted project decisions;
- the latest proposed/accepted design-gate documents under `docs/`.

A new significant capability requires an explicit design gate before implementation unless it is a narrow correction that does not change an established boundary.

When a previously open decision becomes accepted, obsolete uncertainty must not remain elsewhere in foundational documentation as if it were still active.

---

# 19. Current Roadmap Authority

The detailed milestone roadmap is maintained exclusively in `docs/ROADMAP.md`.

This blueprint intentionally does not duplicate milestone-by-milestone status because duplicated roadmap state becomes stale and can mislead future sessions.

Current position:

- M0–M48 are complete according to the current roadmap.
- M48 time filtering and cross-execution history are merged.
- PR #118 implementation head `babd5935c76a01752e8fb2d32536eb7d42c55769` passed GitHub Actions Tests run #1959 before merge.
- M48 completion is recorded in `docs/M48-SCHEDULED-WORKFLOW-CROSS-EXECUTION-HISTORY-MVP-COMPLETION.md`.

The next action must be derived from the actual GitHub state and accepted design, not from historical roadmap text embedded in this blueprint.

---

# 20. Documentation Structure

The repository documentation is organized around durable project state:

```
docs/
├── PROJECT_BLUEPRINT.md
├── PROJECT_RULES.md
├── ENGINEERING_RULES.md
├── ROADMAP.md
├── DECISION_LOG.md
├── LESSONS_LEARNED.md
└── DEC-*.md
```

Milestone completion documents record stable accepted outcomes. Design gates define meaning, ownership, boundaries, alternatives, trade-offs, and acceptance criteria before significant implementation.

---

# 21. Current State Synchronization Rule

GitHub is the source of truth.

At session start, review the current GitHub state rather than relying on an old conversation snapshot.

After meaningful work reaches a stable state:

```
Design
→ Test
→ Implement
→ Review
→ Refactor
→ Document
→ Commit
→ Push
→ Verify GitHub state
```

Do not leave contradictory milestone status, obsolete architecture decisions, or superseded assumptions in foundational documents.

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

# 22. Guiding Principle

The project should be developed as an engineering system first and a feature collection second.

Every new feature should answer:

```
Why does this exist?
What problem does it solve?
Who owns it?
What does it depend on?
What does it not know?
How can it be tested?
What are the trade-offs?
```

The repository must make the current answer discoverable without requiring historical conversation context.

---

# 23. Project State & GitHub Synchronization

GitHub is the source of truth for the project's current state.

At the beginning of every development session, review:

- PROJECT_BLUEPRINT.md
- PROJECT_RULES.md
- ENGINEERING_RULES.md
- ROADMAP.md
- DECISION_LOG.md
- LESSONS_LEARNED.md

Then verify the current branch/PR state before implementing new work.

The expected cycle is:

Design
→ Test
→ Implement
→ Review
→ Refactor
→ Document
→ Commit
→ Push
→ Verify

Meaningful stable work should be synchronized to GitHub promptly.

---

**Document Status:** Foundational blueprint — maintained

**Current Implementation:** M48 is complete. M48 time filtering and cross-execution history are merged and validated within the accepted design scope.

**Current Project State:** See `docs/ROADMAP.md` and `docs/DECISION_LOG.md` for authoritative milestone and decision state.

**Next Step:** Open a new design gate for the next significant capability. Do not extend M48 opportunistically.
