# EGX Stock Analyzer — Roadmap

**Project:** EGX Stock Analyzer
**Status:** Active
**Current Phase:** M0 — Vision & Project Blueprint

---

# 1. Purpose

This roadmap defines the planned evolution of the EGX Stock Analyzer from its initial domain foundation into an automated stock-analysis platform.

The roadmap is intentionally milestone-driven.

A milestone is considered complete when its design, implementation, tests, documentation, and acceptance criteria are satisfied.

The roadmap may change when new evidence or requirements justify a change.

---

# 2. Development Strategy

The project follows this progression:

```text
Vision
  ↓
Domain
  ↓
Market Data
  ↓
Analysis
  ↓
Scoring
  ↓
Signals
  ↓
Backtesting
  ↓
Automation
  ↓
Reporting
  ↓
API / Dashboard
  ↓
Production
```

We intentionally avoid starting with:

- UI
- database-heavy architecture
- AI
- microservices
- complex infrastructure

The core analytical model must become reliable first.

---

# 3. Milestone Overview

| Milestone | Name                   | Primary Goal                        | Status         |
| --------- | ---------------------- | ----------------------------------- | -------------- |
| M0        | Vision & Blueprint     | Define what we are building         | 🟡 In Progress |
| M1        | Domain Foundation      | Establish core domain model         | 🟡 In Progress |
| M2        | Market Data Foundation | Define market observations          | 🔴 Not Started |
| M3        | Data Acquisition       | Connect external data sources       | 🔴 Not Started |
| M4        | Data Quality           | Assess and manage data reliability  | 🔴 Not Started |
| M5        | Technical Analysis     | Build technical indicators          | 🔴 Not Started |
| M6        | Fundamental Analysis   | Build fundamental analysis          | 🔴 Not Started |
| M7        | Scoring Engine         | Combine evidence into scores        | 🔴 Not Started |
| M8        | Signal Generation      | Produce explainable signals         | 🔴 Not Started |
| M9        | Backtesting            | Test strategies historically        | 🔴 Not Started |
| M10       | Automation             | Run analysis automatically          | 🔴 Not Started |
| M11       | Reporting & Alerts     | Deliver results                     | 🔴 Not Started |
| M12       | API & Dashboard        | Expose system to users              | 🔴 Not Started |
| M13       | Production Hardening   | Prepare for reliable production use | 🔴 Not Started |

---

# 4. M0 — Vision & Project Blueprint

## Objective

Define the purpose, boundaries, philosophy, architecture direction, and success criteria of the system.

## Deliverables

- Project blueprint
- Project rules
- Engineering rules
- Roadmap
- Decision log
- Lessons learned structure
- Initial architecture direction

## Acceptance Criteria

M0 is complete when:

- Project vision is documented.
- Scope is defined.
- Non-goals are defined.
- Architecture direction is documented.
- Development methodology is documented.
- Major open decisions are known.
- Initial roadmap exists.

## Current State

**In Progress**

---

# 5. M1 — Domain Foundation

## Objective

Build the smallest stable domain model required by the system.

## Initial Concepts

Potential concepts include:

```text
Stock
MarketData
DataQuality
Analysis
Score
Signal
Strategy
```

Only concepts justified by requirements should be implemented.

## Focus

- Entities
- Value objects
- Domain invariants
- Identity
- Ownership
- Domain behavior
- Equality semantics
- Domain tests

## Explicit Non-Goals

Do not introduce yet:

- database repositories
- HTTP endpoints
- external providers
- UI
- AI
- background workers

## Acceptance Criteria

- Core domain concepts have clear meanings.
- Responsibilities are explicit.
- Tests describe important behavior.
- Domain is independent from infrastructure.
- Important decisions are documented.

## Current State

**In Progress**

---

# 6. M2 — Market Data Foundation

## Objective

Define how the system represents market observations.

## Questions To Resolve

- What exactly is a market observation?
- What timeframe does it represent?
- How is timestamp interpreted?
- What timezone is used?
- Is data raw or normalized?
- Does MarketData own quality information?
- How are missing observations represented?
- How are duplicates handled?
- How are conflicting observations handled?

## Potential Data

```text
Timestamp
Open
High
Low
Close
Volume
Stock
Timeframe
Source
```

The final model will be decided through the Design Gate.

## Acceptance Criteria

- Market observation semantics are documented.
- Time semantics are explicit.
- Ownership is clear.
- Data-quality responsibility is separated appropriately.
- Domain tests cover agreed behavior.

---

# 7. M3 — Data Acquisition

## Objective

Introduce external market-data providers.

## Architecture Direction

```text
External Provider
       ↓
Provider Adapter
       ↓
Application
       ↓
Domain
```

The provider itself must not become part of the core domain model.

## Goals

- Provider abstraction
- Data fetching
- Provider mapping
- Error handling
- Retry strategy
- Rate-limit handling
- Provider observability

## Acceptance Criteria

The system can retrieve market data without coupling the domain to a specific provider.

---

# 8. M4 — Data Quality

## Objective

Determine whether received market observations are usable for analysis.

## Possible Quality States

```text
VALID
SUSPECT
INVALID
UNKNOWN
```

The exact model is not yet committed.

## Responsibilities

Potential checks:

- missing values
- impossible relationships
- duplicate observations
- abnormal values
- stale data
- provider conflicts
- timestamp problems
- volume anomalies

## Important Principle

Data quality should not automatically mean data deletion.

Where possible:

```text
Receive
 ↓
Preserve
 ↓
Assess
 ↓
Classify
 ↓
Decide whether analysis may use it
```

## Acceptance Criteria

The system can explain why a data point was considered reliable or unreliable.

---

# 9. M5 — Technical Analysis

## Objective

Transform market data into technical evidence.

## Potential Indicators

Examples:

- Moving averages
- RSI
- MACD
- Bollinger Bands
- ATR
- Support
- Resistance
- Volume analysis
- Trend detection

The final indicator set will be selected based on strategy requirements.

## Design Principle

Indicators should be:

- deterministic
- independently testable
- composable
- explainable

## Acceptance Criteria

Given the same historical data and configuration, the same technical calculations produce the same results.

---

# 10. M6 — Fundamental Analysis

## Objective

Evaluate the financial quality of companies.

## Potential Evidence

Examples:

- Revenue growth
- Earnings growth
- Profitability
- Debt
- Cash flow
- Valuation
- ROE
- Margins
- Dividend information

The final metrics will depend on reliable EGX data availability.

## Important Constraint

Fundamental analysis must account for:

- reporting periods
- missing data
- restatements
- different accounting periods
- corporate actions
- data freshness

## Acceptance Criteria

Fundamental metrics are traceable to their source data and calculation rules.

---

# 11. M7 — Scoring Engine

## Objective

Combine analytical evidence into a consistent scoring model.

## Initial Working Proposal

```text
Technical       30
Fundamental     25
Momentum        15
Liquidity       15
Catalysts       10
Risk             5
------------------
Total           100
```

These values are **not final**.

They are a working hypothesis.

## Requirements

The scoring system must be:

- deterministic
- explainable
- testable
- configurable
- versioned

## Important Separation

The system should distinguish:

```text
Stock Quality
```

from:

```text
Entry Quality
```

## Acceptance Criteria

The system can explain:

- total score
- component scores
- contribution of each component
- strategy version
- missing evidence
- major risks

---

# 12. M8 — Signal Generation

## Objective

Transform analytical evidence into actionable classifications.

## Initial Signal Set

```text
BUY
WATCH
HOLD
AVOID
```

These labels are provisional.

## Future Output

A signal may eventually contain:

```text
Signal
Score
Entry Zone
Stop Loss
Target 1
Target 2
Risk / Reward
Confidence
Reasons
Risks
Strategy Version
Generated At
```

## Important Principle

A signal must be explainable.

The system should answer:

> Why did we generate this signal?

---

# 13. M9 — Backtesting

## Objective

Determine whether strategies would have worked historically.

## Requirements

Backtesting must avoid:

- look-ahead bias
- data leakage
- survivorship bias where relevant
- future information leakage
- unrealistic execution assumptions

## Potential Metrics

- Total return
- Win rate
- Maximum drawdown
- Sharpe ratio
- Profit factor
- Average trade
- Risk/reward
- Number of trades

## Strategy Versioning

Every backtest must identify the strategy version used.

Example:

```text
Strategy v1.0
Strategy v1.1
Strategy v2.0
```

## Acceptance Criteria

A historical strategy can be reproduced using the same:

```text
Historical Data
+
Strategy Version
+
Configuration
```

---

# 14. M10 — Automation

## Objective

Run the analysis pipeline automatically.

## Target Pipeline

```text
Collect
  ↓
Assess Data Quality
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
```

## Potential Scheduling

Examples:

- daily
- weekly
- event-driven
- market-session based

The exact scheduling model will be decided later.

## Acceptance Criteria

The complete analytical pipeline can execute without manual intervention.

---

# 15. M11 — Reporting & Alerts

## Objective

Deliver useful results to the user.

## Possible Outputs

- Daily market report
- Top opportunities
- Watchlist changes
- New signals
- Risk alerts
- Data-quality alerts
- Strategy-performance reports

## Potential Channels

Future possibilities:

- Email
- Telegram
- Web notifications
- Dashboard notifications

Provider choices are not yet committed.

## Acceptance Criteria

Reports are:

- understandable
- explainable
- traceable
- generated from reproducible analysis

---

# 16. M12 — API & Dashboard

## Objective

Expose the system through a user-facing interface.

## API Responsibilities

Potentially:

- stock search
- stock details
- historical data
- analysis
- scores
- signals
- reports
- strategy results

## Dashboard Responsibilities

Potentially:

```text
Market Overview
Stock Details
Technical Analysis
Fundamental Analysis
Score
Signals
Historical Performance
Backtests
Alerts
```

## Important Rule

The API and UI must consume domain/application capabilities.

They must not become owners of business rules.

---

# 17. M13 — Production Hardening

## Objective

Prepare the system for reliable long-term operation.

## Areas

### Reliability

- retries
- failure recovery
- idempotency
- monitoring

### Security

- secrets management
- authentication
- authorization
- secure configuration

### Performance

- caching
- efficient calculations
- database optimization

### Observability

- structured logging
- metrics
- tracing where justified
- pipeline execution history

### Operations

- deployment
- backups
- migrations
- rollback strategy

---

# 18. Cross-Cutting Requirements

These requirements apply across milestones.

## Correctness

Results must be mathematically and logically correct.

## Explainability

Important outputs must have understandable reasons.

## Reproducibility

Historical results should be reproducible.

## Testability

Important behavior must be independently testable.

## Replaceability

External providers must be replaceable.

## Extensibility

New strategies and indicators should not require rewriting the entire system.

## Observability

Failures and important system decisions must be visible.

---

# 19. Milestone Completion Rule

A milestone is not complete simply because the code exists.

A milestone requires:

```text
Design
 ↓
Tests
 ↓
Implementation
 ↓
Review
 ↓
Refactor
 ↓
Documentation
 ↓
Git Commit
 ↓
Milestone Complete
```

---

# 20. Changing the Roadmap

The roadmap may change when:

- a requirement changes
- an architectural assumption proves incorrect
- new evidence becomes available
- a dependency becomes unavailable
- a milestone reveals a better sequence

Changes should be intentional.

If a roadmap change affects architecture or important domain decisions, record the decision in:

```text
docs/DECISION_LOG.md
```

---

# 21. Current Position

```text
M0  █████████░  Vision & Blueprint
M1  ████░░░░░░  Domain Foundation
M2  ░░░░░░░░░░  Market Data Foundation
M3  ░░░░░░░░░░  Data Acquisition
M4  ░░░░░░░░░░  Data Quality
M5  ░░░░░░░░░░  Technical Analysis
M6  ░░░░░░░░░░  Fundamental Analysis
M7  ░░░░░░░░░░  Scoring
M8  ░░░░░░░░░░  Signals
M9  ░░░░░░░░░░  Backtesting
M10 ░░░░░░░░░░  Automation
M11 ░░░░░░░░░░  Reporting
M12 ░░░░░░░░░░  API / Dashboard
M13 ░░░░░░░░░░  Production
```

Current focus:

> **Finish M0 and establish the domain design before continuing implementation.**

---

# 22. Guiding Principle

> **We are not racing toward a dashboard. We are building a reliable analytical engine that a dashboard can eventually depend on.**
