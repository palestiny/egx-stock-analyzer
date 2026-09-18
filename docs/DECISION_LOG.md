# EGX Stock Analyzer — Decision Log

**Project:** EGX Stock Analyzer
**Status:** Active
**Purpose:** Record important architectural, domain, and engineering decisions and the reasoning behind them.

---

# 1. How to Read This Document

This document records decisions that affect the structure, behavior, or future evolution of the system.

A decision should answer:

- What did we decide?
- Why?
- What alternatives did we consider?
- What are the consequences?
- Is the decision still active?

Not every implementation detail belongs here.

---

# 2. Decision Status

We use the following statuses:

| Status       | Meaning                                  |
| ------------ | ---------------------------------------- |
| Proposed     | Suggested but not decided                |
| Accepted     | Decision has been made                   |
| Under Review | Previously chosen but being reconsidered |
| Superseded   | Replaced by a newer decision             |
| Rejected     | Explicitly rejected                      |

---

# 3. Decision Template

Future decisions should generally follow:

```text
## DEC-XXX — Title

Status:
Date:

### Context

Why does this decision exist?

### Decision

What did we decide?

### Alternatives Considered

What other approaches were considered?

### Trade-offs

What do we gain?
What do we sacrifice?

### Consequences

What does this decision mean for the rest of the system?

### Revisit Conditions

When should this decision be reconsidered?
```

---

# 4. Accepted Decisions

## DEC-001 — Stock Is an Entity

**Status:** Accepted

### Context

The system needs to represent publicly traded companies/stocks and maintain their identity across time.

### Decision

`Stock` is modeled as a domain Entity.

Its identity is independent from its descriptive attributes.

### Reasoning

A stock may change descriptive information while remaining the same domain object.

Therefore identity should not depend on:

- name
- current price
- current market data
- other mutable attributes

### Consequences

The Stock model owns stock identity.

Other domain objects can reference the Stock identity without taking ownership of the Stock itself.

---

# 5. DEC-002 — Stock Uses UUID as Internal Identity

**Status:** Accepted

### Context

The system needs a stable internal identity for Stock.

### Decision

Each Stock entity has an internal UUID.

Example:

```text id = UUID

```

### Reasoning

The internal identity should be:

- stable
- independent of external naming
- suitable for persistence
- independent of the stock symbol

### Consequences

A symbol is not the internal identity of the entity.

---

# 6. DEC-003 — Stock Symbol Is a Business Identifier

**Status:** Accepted

### Context

EGX stocks are externally identified by symbols such as:

```text
COMI
EGAL
```

### Decision

The stock symbol is treated as the primary external/business identifier.

It is not the internal entity identity.

### Consequences

The system distinguishes:

```text
Internal Identity
UUID

Business Identifier
Symbol
```

This allows the internal identity model to remain independent from external identifiers.

---

# 7. DEC-004 — Normalize Stock Symbol

**Status:** Accepted

### Decision

Stock symbols are normalized by:

1. trimming surrounding whitespace
2. converting to uppercase

Example:

```text
" comi "
```

becomes:

```text
"COMI"
```

### Reasoning

Symbols represent standardized business identifiers.

Normalization prevents accidental differences caused by formatting.

---

# 8. DEC-005 — Normalize Stock Name

**Status:** Accepted

### Decision

Stock names are trimmed when the entity is created or reconstituted.

Example:

```text
"  Commercial International Bank  "
```

becomes:

```text
"Commercial International Bank"
```

### Reasoning

Whitespace around a descriptive name does not represent meaningful domain information.

---

# 9. DEC-006 — Stock Requires an Existing ID in the Constructor

**Status:** Accepted

### Context

There are two different operations:

```text
Create a new entity
```

and:

```text
Reconstitute an existing entity
```

### Decision

The direct constructor requires an explicit ID.

Creation uses:

```python
Stock.create(...)
```

Reconstitution uses:

```python
Stock.reconstitute(...)
```

### Reasoning

This makes the distinction between new and existing entities explicit.

It prevents accidental generation of a new identity when reconstructing an existing Stock.

---

# 10. DEC-007 — Stock Equality Is Based on Identity

**Status:** Accepted

### Decision

Two Stock entities are considered equal when they have the same internal ID.

Conceptually:

```text
Stock A.id == Stock B.id
```

### Reasoning

Entity equality is based on identity rather than descriptive attributes.

Two Stock objects representing the same entity may have different object instances or updated descriptive information while retaining the same identity.

---

# 11. DEC-008 — Domain-First Architecture

**Status:** Accepted

### Context

The project will eventually integrate:

- APIs
- databases
- external market-data providers
- reporting
- automation
- potentially AI

### Decision

The domain is developed independently from infrastructure and delivery mechanisms.

### Reasoning

The core business model should not depend on:

- FastAPI
- database technology
- external provider
- UI
- AI provider

### Consequences

Infrastructure may change without forcing a rewrite of the core domain.

---

# 12. DEC-009 — Modular Monolith as Initial Architecture

**Status:** Accepted

### Context

The system will contain multiple analytical and operational capabilities.

### Decision

The initial architecture will be a Modular Monolith.

Potential modules include:

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

### Reasoning

A Modular Monolith provides:

- clear boundaries
- simple deployment
- low operational complexity
- easier debugging
- room for future extraction if needed

### Trade-off

We sacrifice independent service deployment in exchange for significantly lower initial complexity.

### Revisit Conditions

Consider service extraction only when there is a real operational or organizational reason.

---

# 13. DEC-010 — External Data Is an Observation

**Status:** Accepted

### Context

The system will consume data from external market-data providers.

External data may contain:

- errors
- missing values
- inconsistencies
- stale observations
- provider-specific problems

### Decision

External market data is treated as an observation received by the system, not automatically as absolute truth.

### Reasoning

The system should distinguish:

```text
What the provider reported
```

from:

```text
What the system believes is reliable for analysis
```

### Consequences

Data acquisition and data quality become separate concerns.

---

# 14. DEC-011 — Data Quality Is a Separate Concern

**Status:** Accepted

### Context

During the design of MarketData, the question arose whether suspicious external observations should be rejected immediately.

### Decision

Data quality assessment should be conceptually separated from the raw market observation.

The system should be able to:

```text
Receive
 ↓
Preserve
 ↓
Assess Quality
 ↓
Classify
 ↓
Decide Whether Analysis Can Use It
```

### Reasoning

Rejecting an observation immediately may destroy useful information.

A suspicious observation can itself be valuable for:

- diagnostics
- provider comparison
- auditing
- debugging
- historical investigation

### Consequences

The exact data-quality model remains an open design decision.

---

# 15. DEC-012 — Do Not Automatically Reject External Data Based on One Expected Relationship

**Status:** Under Review

### Context

A validation rule was introduced for:

```text
High < Open
```

The intention was to protect OHLC consistency.

However, this raised a larger architectural question:

> Should the MarketData entity reject external observations, or should the system preserve the observation and assess its quality separately?

### Current Position

The immediate validation rule is under review.

The project currently favors separating:

```text
Domain invariants
```

from:

```text
External data-quality expectations
```

### Reasoning

Market data is received from external systems.

The analyzer's responsibility is not necessarily to declare that an external provider's observation never existed.

The system may instead need to record:

```text
Observation received
+
Quality assessment
```

### Consequences

No additional MarketData validation rules should be added until the ownership and semantics of data quality are finalized.

### Revisit Conditions

This decision should be resolved during:

**M2 — Market Data Foundation**

and:

**M4 — Data Quality**

---

# 16. DEC-013 — Domain Behavior Is Developed Using TDD

**Status:** Accepted

### Decision

Important domain behavior follows:

```text
RED
 ↓
GREEN
 ↓
REVIEW
 ↓
REFACTOR
```

### Reasoning

This provides:

- executable specifications
- safer refactoring
- clearer domain behavior
- early detection of incorrect assumptions

### Consequences

Tests are treated as part of domain design, not merely as final verification.

---

# 17. DEC-014 — AI Is a Development Tool, Not the Architectural Core

**Status:** Accepted

### Context

AI may assist in developing and eventually operating parts of the system.

### Decision

AI is treated as a replaceable capability.

The core architecture must not depend on one specific AI provider or model unless an explicit requirement later justifies it.

### Reasoning

The project's primary value is:

```text
Reliable Data
+
Analysis
+
Scoring
+
Explainable Decisions
```

AI may enhance these capabilities but should not define the entire architecture.

---

# 18. DEC-015 — No Premature Microservices

**Status:** Accepted

### Decision

The project will not begin as a microservices architecture.

### Reasoning

At the current stage, microservices would introduce complexity without a demonstrated need.

Examples:

- service discovery
- network communication
- distributed failures
- deployment complexity
- observability overhead

### Consequences

Modular boundaries must still be designed clearly so that future extraction remains possible if justified.

---

# 19. DEC-016 — Scoring Is Explainable and Deterministic

**Status:** Accepted as a Design Principle

### Decision

The future scoring engine should be:

- deterministic
- explainable
- testable
- versioned

For identical:

```text
Input Data
+
Strategy Version
+
Configuration
```

the resulting score should be reproducible.

### Important Note

The actual scoring formulas and weights are not yet committed.

---

# 20. DEC-017 — Separate Stock Quality From Entry Quality

**Status:** Accepted as a Design Principle

### Decision

The system must distinguish:

```text
Stock Quality
```

from:

```text
Entry Quality
```

### Reasoning

A high-quality company does not automatically represent a good entry at the current price.

Likewise, a technically attractive entry does not necessarily indicate a fundamentally strong company.

### Consequences

Future scoring and signal-generation designs must preserve this distinction.

---

## DEC-019 — PriceBar Is an Immutable Market Observation Value Object

**Status:** Accepted

### Context

The system needs a domain representation for one OHLCV market observation associated with a Stock, timeframe, and timestamp.

The concept must remain independent from:

- external market-data providers
- data-quality assessment
- technical-analysis rules
- database persistence
- API models
- trading strategy

### Decision

`PriceBar` is modeled as an immutable Value Object representing one OHLCV market observation.

Its conceptual structure is:

```text
PriceBar
├── stock_id
├── timeframe
├── timestamp
├── open: Price
├── high: Price
├── low: Price
├── close: Price
└── volume: Volume
```

`PriceBar` composes the existing:

```text
Price
Volume
```

Value Objects.

### Identity / Logical Key

A PriceBar is logically identified by:

```text
Stock
+
Timeframe
+
Timestamp
```

The exact persistence identity is not yet decided.

The exact semantics of the timestamp, including EGX trading-session and timezone rules, remain an open decision.

### Responsibility

`PriceBar` is responsible for representing the structure of one OHLCV observation.

It owns:

- the associated Stock identity
- timeframe
- timestamp
- OHLC prices
- volume

### Non-Responsibility

`PriceBar` does NOT own:

- external data-provider behavior
- provider reliability
- data-quality assessment
- analysis eligibility
- technical indicators
- support/resistance detection
- trading signals
- scoring
- trading strategy
- persistence
- API behavior

### OHLC Relationship Validation

The following relationships are intentionally NOT treated as `PriceBar` domain invariants at this stage:

```text
High >= Open
High >= Close
Low <= Open
Low <= Close
```

These relationships may be relevant to external data quality, but their ownership belongs to the future Data Quality design unless later evidence establishes that they are true domain invariants.

In particular:

```text
High < Open
```

must not automatically cause the observation to be rejected by `PriceBar`.

This is consistent with:

```text
External Observation
        ↓
Data Quality Assessment
        ↓
Analysis Eligibility
```

### Timeframe

The initial project use case is Daily market data.

However, `PriceBar` is designed to represent a bar for a timeframe without making Daily the only possible timeframe.

The exact Timeframe model is a separate design decision.

### Immutability

`PriceBar` is immutable because it represents a completed observation.

Changes to market observations should produce new observations rather than mutate an existing `PriceBar`.

### Alternatives Considered

#### Mutable Entity

Rejected for the current design because a completed market observation is better represented as a stable value.

#### Entity With Its Own Identity

Not selected for the current domain model because the current conceptual identity is the logical combination:

```text
Stock + Timeframe + Timestamp
```

Whether persistence requires a separate technical identity remains open.

#### Primitive OHLCV Fields

Rejected because the project already establishes domain Value Objects for:

```text
Price
Volume
```

Using them preserves explicit domain semantics and prevents primitive values from carrying hidden meaning.

#### Put OHLC Validation Inside PriceBar

Rejected for now because the question is primarily about external data quality rather than the meaning of a valid market observation.

### Trade-offs

Advantages:

- clear domain meaning
- immutable representation
- composition of existing Value Objects
- independent from infrastructure
- easier testing
- preserves the distinction between observation and quality

Trade-offs:

- data-quality validation must exist elsewhere
- additional domain types are required
- timestamp and timeframe semantics still need future decisions

### Consequences

Future market-data acquisition should map external provider responses into `PriceBar` without allowing provider-specific behavior to leak into the domain.

Future Data Quality logic should evaluate whether a PriceBar is reliable or usable for analysis.

Future technical-analysis logic should consume PriceBars rather than own their structural representation.

### Revisit Conditions

Revisit this decision if:

- timestamp semantics require a different model
- timeframe semantics require a different representation
- persistence requirements introduce meaningful domain identity
- market-data requirements reveal missing domain concepts
- new evidence shows that structural OHLC relationships are actual domain invariants

---

# 20.5 DEC-018 — GitHub Is the Project Source of Truth

**Status:** Accepted

### Context

The project is developed across multiple sessions and may involve
AI-assisted development.

Relying only on conversation history creates a risk of losing the actual
project state, architectural decisions, or the latest implementation status.

### Decision

GitHub is the source of truth for the project's current development state.

Project documentation and stable implementation changes must be synchronized
with the GitHub repository.

At the beginning of a development session, the repository documentation
should be reviewed before implementing significant new work.

### Synchronization Cycle

````text
Design
  ↓
Test
  ↓
Implement
  ↓
Review
  ↓
Refactor
  ↓
Document
  ↓
Commit
  ↓
Push
  ↓
GitHub
---

# 21. Open Decisions

The following decisions are intentionally **not finalized**.

## OPEN-001 — MarketData Ownership

Questions:

- Is MarketData an Entity or Value Object?
- Does it have its own identity?
- Is identity based on Stock + timestamp + timeframe?
- Does source become part of identity?

---

## OPEN-002 — MarketData Validation

Questions:

- Which conditions are true domain invariants?
- Which are data-quality checks?
- Which observations should be preserved?
- Which observations should be unusable for analysis?

---

## OPEN-003 — Data Quality Model

Questions:

- Should quality use states?
- Should quality use scores?
- Should quality contain reasons?
- Can one observation have multiple quality issues?
- Who owns the quality assessment?

---

## OPEN-004 — Conflicting Providers

If two providers report different values:

```text
Provider A → 100
Provider B → 102
````

Questions:

- Which value wins?
- Do we preserve both?
- Do we calculate confidence?
- Do we maintain provider precedence?
- Does the conflict itself become a quality event?

---

## OPEN-005 — Missing Data

Questions:

- When is missing data acceptable?
- When should analysis stop?
- Should missing data reduce confidence?
- Should a signal be blocked?

---

## OPEN-006 — Time Semantics

Questions:

- What timezone is canonical?
- How are EGX trading sessions represented?
- How are holidays represented?
- What does a timestamp mean?
- How are daily candles identified?

---

## OPEN-007 — Technical Strategy

Questions:

- Which indicators are required?
- What parameters should they use?
- How are support/resistance levels detected?
- How are conflicting indicators handled?

---

## OPEN-008 — Fundamental Strategy

Questions:

- Which financial metrics matter?
- How are missing fundamentals handled?
- How are reporting periods normalized?
- How are corporate actions handled?

---

## OPEN-009 — Scoring Formula

The current weights are only a working hypothesis:

```text
Technical       30
Fundamental     25
Momentum        15
Liquidity       15
Catalysts       10
Risk             5
```

They are not committed.

---

## OPEN-010 — Signal Rules

Questions:

- What score produces BUY?
- What creates WATCH?
- How is risk/reward calculated?
- How are stop losses determined?
- How are targets determined?

---

## OPEN-011 — Data Providers

No specific market-data provider is currently an architectural commitment.

Provider selection will be evaluated based on:

- EGX coverage
- historical depth
- reliability
- cost
- legal/licensing considerations
- API quality
- rate limits

---

## OPEN-012 — Persistence

The database technology and persistence architecture are not yet finalized.

Persistence decisions should follow domain semantics rather than define them.

---

# 22. Important Rule for Future Decisions

A decision should be recorded when changing it could affect:

- domain meaning
- ownership
- architecture
- dependency direction
- data semantics
- analysis strategy
- reproducibility
- external integration boundaries

Small implementation details do not require an entry.

---

# 23. Decision History Principle

A decision is not permanent merely because it was written down.

A decision may be changed when new evidence proves that the previous reasoning was incomplete or incorrect.

When that happens:

```text
Old Decision
    ↓
Reason for Reconsideration
    ↓
New Decision
    ↓
Consequences
```

The old decision should remain in history rather than being silently deleted.

---

# 24. Current Architectural Position

The current system can be summarized as:

```text
                    ┌────────────────────┐
                    │   External World   │
                    │ Providers / APIs   │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │  Data Acquisition  │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │    Market Data     │
                    │    Observations    │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │    Data Quality    │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │     Analysis       │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │      Scoring       │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │      Signals       │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Reports / Alerts   │
                    └────────────────────┘
```

This is an architectural direction, not a final implementation diagram.

---

# 25. Current Status

The project is currently in:

**M0 — Vision & Project Blueprint**

with initial work beginning on:

**M1 — Domain Foundation**

The most important unresolved domain topic is:

> **What exactly is MarketData, and where does responsibility for data quality belong?**

That question must be resolved before adding unnecessary MarketData behavior.

---

# 26. Guiding Principle

> **A decision is valuable not only because it tells us what to do, but because it records why we chose it.**

# 27. Project State & GitHub Synchronization

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



## DEC-021 — Use Yahoo Finance as the Current Real-Data Source for the Vertical Slice

**Status:** Accepted for current development/testing phase

### Context

The EGX real-data vertical slice reached Yahoo Finance successfully for market data, but the Finnhub financial-data endpoint returned HTTP 403:

`You don't have access to this resource.`

A direct request outside the application reproduced the same 403, confirming that the blocker is external to the application implementation.

The immediate project goal is to exercise the analysis pipeline against real EGX data, not to finalize the long-term external-data architecture.

### Decision

For the current vertical-slice validation, Yahoo Finance is used as the live source for both:

- daily market data;
- annual fundamental data.

The fundamental-data implementation reads Yahoo Finance annual income-statement and balance-sheet data and maps it into the existing `FinancialPeriod` domain model.

This is explicitly a development/testing source decision and is **not** a long-term commitment to Yahoo Finance as the project's permanent data provider.

### Alternatives Considered

#### Continue with Finnhub

Deferred because the currently available account/key cannot access the required financials resource.

#### Introduce another financial-data provider

Deferred because doing so would solve the immediate integration problem while prematurely making a provider choice that the project has explicitly kept open.

#### Use Yahoo Finance for the current vertical slice

Accepted because the project already uses Yahoo Finance for EGX market history and it allows us to continue testing the complete analysis path with one currently accessible source.

### Trade-offs

Advantages:

- removes the immediate Finnhub access blocker;
- keeps the current vertical slice focused;
- avoids adding another external dependency for the test phase;
- allows market and annual fundamental data to come from the same current source.

Trade-offs:

- Yahoo Finance fundamental coverage for EGX must be verified empirically;
- source-specific field names require normalization;
- this does not resolve the project's long-term data acquisition strategy.

### Consequences

The infrastructure runtime no longer requires `FINNHUB_API_KEY` for the current development application.

The existing application and domain layers remain unchanged.

The long-term data-source/provider architecture remains an open decision.

### Revisit Conditions

Revisit when:

- Yahoo Finance cannot provide sufficient EGX fundamental coverage;
- data quality or historical depth becomes inadequate;
- production automation requires stronger guarantees;
- licensing or reliability requirements demand another source;
- multiple-source reconciliation becomes necessary.


## DEC-020 — Exclude Invalid External Observations When Sufficient Valid Data Remains

**Status:** Accepted

### Context

A real EGX vertical-slice run exposed an OHLC inconsistency in Yahoo Finance data for EGAL.CA. The provider returned an observation where the low price was above the open price.

The existing data-quality model correctly classified the observation as invalid, but the assembler rejected the entire market-data window.

### Decision

Invalid or suspect external observations are excluded from the analysis input rather than causing the entire dataset to be rejected.

Analysis may continue only when the remaining valid observations satisfy the minimum data requirement of the analysis policy.

The minimum number of PriceBars is:

    max(momentum_lookback, volume_lookback) + 1

The system does not repair or rewrite provider values.

### Alternatives Considered

#### Reject the Entire Dataset

Rejected because one provider anomaly can unnecessarily block analysis of otherwise usable historical data.

#### Repair the Invalid Observation

Rejected because the system would be inventing market data and could silently alter the provider's observation.

#### Exclude Invalid Observations and Continue

Accepted because it preserves the raw-observation/quality distinction while preventing one isolated external anomaly from contaminating analysis.

### Trade-offs

Advantages:

- resilient to isolated provider anomalies
- preserves strict quality rules
- avoids silently modifying source data
- keeps downstream analysis working when sufficient evidence remains

Trade-offs:

- the analysis input may contain fewer observations than the provider returned
- excessive invalid observations will still block analysis
- the current implementation reports rejection counts through the failure message but does not yet persist a quality report

### Consequences

`AnalysisInputAssembler` is responsible for applying the analysis-eligibility decision after `DataQualityAssessor` evaluates observations.

`PriceBarFactory` continues to accept only `VALID` observations.

No OHLC quality rule is weakened to accommodate a provider response.

### Revisit Conditions

Revisit this decision if:

- downstream indicators require more sophisticated data sufficiency rules
- quality reporting becomes a first-class domain capability
- multiple providers are reconciled
- invalid-data rates become high enough to require provider-level handling


## DEC-021 Validation Note — Real EGAL Vertical Slice

**Status:** Validated for the current development/testing phase

On 2026-09-18, the real-data EGAL integration test completed successfully:

```
1 passed, 5 warnings in 4.82s
```

This validates the current end-to-end vertical slice using Yahoo Finance for the live market and annual fundamental data path.

The five warnings did not cause test failure and remain a separate cleanup/compatibility concern. They do not change the current provider decision.

The validation also confirms that non-finite Yahoo fundamental values such as `NaN` are excluded at the infrastructure boundary rather than entering the `FinancialPeriod` domain model.


## DEC-062 — Preserve Execution Failure Details

**Status:** Accepted  
**Date:** 2026-09-18

### Context

The execution boundary preserved failed stock IDs but discarded the final exception reason. This made failures harder to diagnose after retry handling.

### Decision

Store a lightweight human-readable failure reason per failed stock in Execution. ExecutionRunner records the final exception message when retries are exhausted. A later successful retry clears the stored reason.

### Trade-offs

This improves diagnostics without changing partial-failure semantics or retry behavior. The stored reason is diagnostic context only; it is not a stable API contract, secure audit log, or replacement for structured observability.

### Revisit

Revisit in M13 Production Hardening when production-safe logging, observability, and structured failure categories are designed.


## DEC-063 — M12 API Surface and Boundary Design

**Status:** Accepted for the first M12 API slice  
**Date:** 2026-09-18

The first M12 API surface is intentionally split into a query and a command: `GET /api/v1/analysis/{symbol}` reads the latest stored result, while `POST /api/v1/analysis/{symbol}` requests analysis through the application use case and returns the resulting stored result.

FastAPI remains a transport adapter. Business rules remain in application/domain layers. `AnalysisResultResponse` is the transport DTO and domain objects are not exposed directly.

Current HTTP mappings are: unknown symbol/result not found → 404; execution not configured → 503; analysis execution failure → 500; successful analysis → 200.

Freshness metadata, historical results, reports, alerts, authentication/authorization, structured production error taxonomy, and dashboard implementation remain deferred. Additional API surface requires a separate design decision rather than being added opportunistically.

See `docs/DEC-063-M12-API-SURFACE-AND-BOUNDARY-DESIGN.md` for the full design gate.


## DEC-063 Validation Note — API Contract Coverage

**Status:** Contract tests implemented

The first M12 API slice now has seven contract tests covering:

- missing GET result → 404
- unconfigured execution → 503
- unknown symbol → 404
- execution failure → 500
- successful GET transport DTO
- successful POST execution followed by stored-result response
- successful execution without a stored result → 500

The tests are committed on the `m12-runtime-integration` branch.

Execution of these tests through GitHub Actions is not currently observable through the available workflow-run integration, so the contract is implemented but not marked externally validated by CI.


## DEC-064 — M12 Reporting & Alerts API Boundary

**Status:** Accepted

The M12 API will expose M11 reporting and alert capabilities only as read-side projections of completed analysis. FastAPI remains responsible for routing, transport DTOs, and HTTP semantics; it must not own scoring, classification, alert delivery, persistence, scheduling, or deduplication.

The current `AnalysisResultStore` does not preserve the analysis period alongside `StockAnalysisResult`. Because M11 `AnalysisReport` requires the real analysis date, M12 will not invent report freshness/history semantics with `date.today()`. The next implementation gate is to preserve the actual analysis period in the stored application result before adding report/alert endpoints.

See `docs/DEC-064-M12-REPORTING-ALERTS-API-BOUNDARY.md`.


## DEC-065 — M12 Reporting/Alert API Contract Validation Status

**Status:** Superseded

### Context

The M12 reporting and alert read-side API slice has been implemented and its focused application/API contract tests were executed locally.

### Decision

The current M12 reporting/alert API contract is considered locally validated for the implemented scope.

The focused suite passed:

```text
17 passed, 2 warnings
```

The original contract represented `Decimal` transport values as JSON strings. This was superseded by DEC-066, which defines prices as JSON numbers.

### Consequences

- Analysis dates remain explicit and are not invented by the API.
- Report and alert endpoints remain read-only projections of stored analysis.
- Decimal precision is preserved at the transport boundary.
- The two remaining warnings are dependency deprecation warnings and are tracked separately from business behavior.

### Next Gate

M12 remains in progress. The next design gate is the dashboard/presentation boundary. No dashboard-specific business logic should be introduced before that gate is defined.


## DEC-066 — Price Values Are JSON Numbers at the API Boundary

**Status:** Accepted  
**Date:** 2026-09-18

### Context

M12 reporting API responses exposed domain `Decimal` price values at the transport boundary. The initial contract represented those values as JSON strings to preserve exact decimal text.

The project owner approved changing the external API representation to JSON numbers.

### Decision

The API transport contract represents price values as JSON numbers.

Example:

```json
{
  "current_price": 350.5,
  "nearest_support": 340.0,
  "nearest_resistance": 365.0
}
```

The domain continues to use `Decimal` for price semantics and precision. Conversion happens explicitly in the API response DTO.

### Alternatives Considered

#### JSON strings

Advantages:
- preserves exact decimal representation;
- avoids binary floating-point conversion at the transport boundary.

Trade-offs:
- API consumers must parse the value before numerical operations;
- clients may treat a price as textual data.

#### JSON numbers

Advantages:
- natural representation for numerical market prices;
- consumers can compare and calculate directly;
- better fit for dashboards and analytical clients.

Trade-offs:
- JSON has no native Decimal type;
- floating-point representation has limitations for some decimal values.

### Consequences

- M12 report price fields are JSON numbers.
- Domain precision remains based on `Decimal`.
- Contract tests explicitly verify numeric JSON values.
- Exact decimal text transport must be introduced only through a future explicit design decision.

### Revisit Conditions

Revisit if an API consumer requires exact decimal text, financial/regulatory requirements require fixed-scale decimal transport, or the API adopts a serialization format with native decimal support.


## DEC-069 — Freeze the First M12 Dashboard Slice

**Status:** Accepted  
**Date:** 2026-09-18

### Context

The first M12 user-facing slice now has:

- API/runtime integration;
- reporting and alert read-side endpoints;
- React + Vite dashboard;
- dashboard loading, success, empty, and transport-error states;
- frontend component/API contract tests;
- production frontend build validation;
- CI coverage for Python tests, frontend tests, and frontend build.

### Decision

Treat the implemented dashboard surface as the accepted first M12 slice and freeze its scope.

Further dashboard capabilities require a new design gate and must not be added opportunistically.

The frozen surface is:

- stock symbol input;
- latest stored analysis report;
- analysis date;
- current price;
- support/resistance;
- technical/fundamental/stock-quality/entry-quality scores;
- opportunity classification;
- technical and fundamental status fields;
- latest alert-candidate projection;
- loading, unavailable, and no-alert states.

### Alternatives Considered

#### Continue expanding the dashboard immediately

Rejected for the current milestone because additional capabilities have different product and API implications.

#### Mark the entire dashboard roadmap complete

Not selected because deferred capabilities such as ranking, watchlists, historical comparison, charting, authentication, and real-time behavior remain outside the accepted slice.

### Trade-offs

The freeze gives the current slice a stable contract and prevents presentation work from driving unplanned backend/domain changes.

The trade-off is that useful dashboard capabilities remain deferred until their own design gates are completed.

### Consequences

M12's first user-facing slice is implementation-complete and validated.

The next work must either:

1. complete M12 documentation/acceptance bookkeeping; or
2. open a new design gate for a specific deferred capability.

No new analytical logic belongs in the frontend.

### Revisit Conditions

Revisit when a concrete next dashboard capability is selected and its API/domain impact can be designed explicitly.


## DEC-070 — M13 Production Hardening Boundary and First Slice

**Status:** Accepted — Operational Runtime Baseline Complete  
**Date:** 2026-09-18

M13 begins with an Operational Runtime Baseline rather than a broad production rewrite.

The first slice validated runtime health through application composition/lifespan, safe API error exposure, operational logging, graceful lifecycle ownership, and idempotent runtime shutdown. The current configuration contract has no required external credentials or mandatory environment values, so no artificial configuration validation rule was introduced. If required configuration is added later, deterministic composition-time validation becomes mandatory.

Persistence, authentication/authorization, deployment topology, metrics/tracing, provider failover, durable scheduling, and other production capabilities require separate design gates.

See `docs/DEC-070-M13-PRODUCTION-HARDENING-BOUNDARY.md`.


## DEC-071 — M13 Durable Analysis State Boundary

**Status:** Accepted  
**Date:** 2026-09-18

The analysis result store was initially in-memory, which was suitable for controlled development but lost completed analysis state across process restarts. M13 therefore established a persistence boundary before selecting a concrete database technology; DEC-072 now implements that boundary with SQLite.

Durable state must preserve the existing analysis result and analysis date required by the report and alert read-side projections. Persistence remains behind the application-facing `AnalysisResultStore` contract, and domain/application code must not depend directly on a database library.

DEC-072 has completed that next gate: SQLite is the selected concrete technology, with an explicit serializer, infrastructure adapter, transactional writes, versioned payloads, failure behavior, tests, and local development inspection tooling. Further persistence evolution remains subject to separate design gates.

See `docs/DEC-071-M13-DURABLE-ANALYSIS-STATE-BOUNDARY.md`.


## DEC-072 — SQLite Analysis Result Persistence MVP

**Status:** Accepted  
**Date:** 2026-09-18

Following DEC-071, the first durable persistence implementation will use SQLite behind the existing `AnalysisResultStore` contract. The MVP uses Python's standard-library `sqlite3` driver and an explicit versioned serializer for the complete `StockAnalysisResult` rather than ORM mappings or Python pickle.

The store keeps the latest completed analysis per symbol and preserves the analysis date. Persistence must be transactional, reconstruct complete analytical results, and fail explicitly on unsupported/corrupt payload versions. Report and alert application services remain unchanged.

The implementation is intentionally limited to durable analysis results; historical browsing, market-data warehousing, authentication, scheduler durability, and other production capabilities remain separate concerns.

See `docs/DEC-072-M13-SQLITE-ANALYSIS-RESULT-PERSISTENCE-MVP.md`.


## DEC-073 — M14 Market-Wide Analysis Capability

**Status:** Accepted  
**Date:** 2026-09-18

M14 introduces a dedicated application use case, `RunMarketAnalysis`, for executing an explicit ordered list of stock symbols through the existing single-stock analysis capability.

The MVP resolves symbols through `StockCatalog`, executes sequentially in caller-provided order, reuses the existing `Execution` aggregate and its `COMPLETED` / `COMPLETED_WITH_ERRORS` / `FAILED` semantics, and treats an empty universe as a completed no-op. Unknown symbols are individual failures; duplicate normalized symbols are invalid input.

Successful per-stock persistence remains owned by `RunStockAnalysis`; M14 does not add aggregate persistence, new database schema, API/dashboard behavior, concurrency, ranking, watchlists, notifications, trading logic, or AI-based selection.

The aggregate run uses the existing `Execution.id` rather than introducing a second execution model. Per-stock retry remains inside the existing single-stock execution boundary.

See `docs/DEC-073-M14-MARKET-WIDE-ANALYSIS-DESIGN-GATE.md`.


## DEC-074 — M15 Market Opportunity Ranking

**Status:** Accepted  
**Date:** 2026-09-18

M15 introduces `RankMarketOpportunities` as a pure application composition over completed `StockAnalysisResult` values. It ranks only BUY and WATCH results using deterministic score keys and normalized symbol order, while excluding HOLD and AVOID without synthetic values.

The capability does not execute analysis, persist results, mutate source results, or own transport concerns.

See `docs/DEC-074-M15-MARKET-OPPORTUNITY-RANKING-DESIGN-GATE.md`.

## DEC-075 — M16 Market Opportunity View

**Status:** Accepted  
**Date:** 2026-09-18

M16 introduces `GetMarketOpportunityRanking` as a read-side application capability over `AnalysisResultStore`. It collects the latest stored result for each requested symbol, reports missing symbols explicitly, and delegates ordering to the existing M15 `RankMarketOpportunities` capability.

The HTTP endpoint `GET /api/v1/opportunities?symbols=...` is read-only and never triggers fresh analysis. The dashboard consumes the resulting ordered read model and does not calculate scores, classifications, filtering, or ranking.

No new persistence schema is introduced. Watchlists, historical ranking, personalization, portfolio logic, real-time streaming, trading execution, and AI ranking remain outside M16.

See `docs/DEC-075-M16-MARKET-OPPORTUNITY-VIEW-DESIGN-GATE.md`.


## DEC-076 — M17 Market Universe & All-Market Execution

**Status:** Accepted  
**Date:** 2026-09-18

M17 extends the existing `StockCatalog` with deterministic symbol enumeration and introduces `RunConfiguredMarketAnalysis` to capture the configured universe once and delegate it to the existing `RunMarketAnalysis` capability.

The configured-market command is exposed as `POST /api/v1/market-analysis`. The endpoint triggers execution only; it does not rank, notify, schedule, or perform analytical calculations. The scheduler remains a trigger mechanism and will use the configured-market capability when full-market scheduling is introduced.

No new persistence schema or concurrency model is introduced. A separate `StockUniverse` abstraction is deferred until universe membership becomes independently persisted, filtered, synchronized, or user-configurable.

See `docs/DEC-076-M17-MARKET-UNIVERSE-EXECUTION-DESIGN-GATE.md`.


## DEC-077 — M18 Scheduled Full-Market Analysis

**Status:** Accepted  
**Date:** 2026-09-18

M18 adds a one-shot scheduling boundary around the existing `RunConfiguredMarketAnalysis` capability. The scheduler remains responsible only for timing; the configured-market use case remains responsible for universe discovery and execution. The universe is resolved when the scheduled operation runs, and the execution date is determined at run time. No recurring schedules, schedule persistence, trading-calendar semantics, concurrency, scheduling API, ranking, dashboard, or notification behavior is introduced.

See `docs/DEC-077-M18-SCHEDULED-FULL-MARKET-ANALYSIS-DESIGN-GATE.md`.


## DEC-078 — M19 Recurring Market Scheduling

**Status:** Proposed  
**Date:** 2026-09-18

M19 opens a design gate for recurring full-market analysis after the one-shot M18 scheduling capability. The gate will define recurrence representation, timezone and trading-calendar semantics, missed-run behavior, overlap policy, occurrence identity/idempotency, persistence scope, deterministic clock behavior, and failure continuation before implementation begins.

The current direction is to keep `RunConfiguredMarketAnalysis` as the business-execution boundary and keep the generic scheduler focused on timing mechanics. No implementation decision is committed until the M19 gate is accepted.

See `docs/DEC-078-M19-RECURRING-MARKET-SCHEDULING-DESIGN-GATE.md`.


---

## DEC-078 — M19 Recurring Market Scheduling

**Status:** Accepted

### Decision

M19 introduces recurring full-market scheduling as an application capability around the existing one-shot scheduler. Recurrence is daily at a configured local time, with Africa/Cairo as the default timezone and Monday-Friday as the temporary calendar policy.

Missed occurrences are skipped. Concurrent market-analysis execution is not introduced. Each occurrence has a deterministic identity based on schedule identity plus scheduled local date/time, with process-local idempotency. Schedules remain process-local and do not survive restart. Time is injected through a clock abstraction. Failed occurrences do not disable future recurrence.

The recurring capability owns recurrence policy and next-run calculation. Scheduler owns timestamp timing mechanics. RunConfiguredMarketAnalysis remains responsible for business execution.

### Trade-offs

This keeps the scheduler generic and the market-analysis policy explicit, at the cost of deferring cron/fixed-interval recurrence, authoritative EGX holiday handling, durable schedules, restart recovery, and distributed coordination.

### Revisit Conditions

Revisit when durable user-managed schedules, an authoritative EGX trading calendar, multiple recurrence rule types, distributed scheduling, or multi-process coordination become required.
