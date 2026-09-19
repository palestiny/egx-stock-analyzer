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


## DEC-079 — M20 Historical Analysis Result History

**Status:** Accepted  
**Date:** 2026-09-18

M20 proposes a history-aware persistence boundary for completed analytical snapshots. The immediate problem is that recurring full-market analysis now runs repeatedly, while the current `AnalysisResultStore` keeps only the latest result per symbol.

The proposed MVP would preserve immutable completed analysis snapshots, support deterministic historical retrieval, and keep the current latest-result contract compatible. Historical reads would never trigger fresh analysis.

The accepted MVP assigns each persisted snapshot a UUID, allows multiple same-day snapshots, keeps `get(symbol)` as the latest-result compatibility query, adds deterministic newest-first history retrieval, migrates the existing latest-only row into history, and treats corrupt/unsupported payloads as explicit persistence errors. Failed analysis does not create a successful snapshot. Historical HTTP/dashboard exposure requires a separate gate.

Historical market-data warehousing, historical ranking, performance analytics, change detection, notifications, watchlists, portfolio/trading behavior, AI analysis, and API expansion are explicitly deferred until separately designed.

See `docs/DEC-079-M20-HISTORICAL-ANALYSIS-RESULT-HISTORY-DESIGN-GATE.md`.


## DEC-080 — M21 Historical Analysis View

**Status:** Accepted  
**Date:** 2026-09-18

M21 exposes the immutable historical analysis snapshots introduced by M20 through a read-only application/API/dashboard boundary.

The accepted contract uses a dedicated `GetAnalysisHistory` application use case behind `GET /api/v1/history/{symbol}`, with inclusive optional date bounds. Unknown symbols return 404; known symbols with no history return an empty collection. The endpoint never executes fresh analysis, and the dashboard renders stored snapshots without duplicating analytical logic.

The gate intentionally defers historical ranking, performance analytics, change detection, charting, notifications, watchlists, portfolio/trading behavior, persistence changes, and AI analysis.

See `docs/DEC-080-M21-HISTORICAL-ANALYSIS-VIEW-DESIGN-GATE.md`.


## DEC-081 — M22 Historical Analysis Comparison

**Status:** Proposed  
**Date:** 2026-09-18

M22 opens a design gate for comparing two persisted historical analysis snapshots for the same stock.

The proposed direction is a read-only application capability over `AnalysisResultStore`. It must not recalculate historical analysis, mutate snapshots, change scoring/classification rules, or introduce persistence schema changes.

The gate must resolve snapshot selection, before/after direction, same-date snapshot handling, derived comparison fields, missing/cross-symbol behavior, API shape, and dashboard presentation before implementation.

See `docs/DEC-081-M22-HISTORICAL-ANALYSIS-COMPARISON-DESIGN-GATE.md`.


## DEC-081 — Historical Analysis Comparison

**Status:** Accepted
**Date:** 2026-09-18

### Decision

M22 compares two persisted analysis snapshots for the same stock using explicit UUID selection through a dedicated read-only comparison endpoint. The response preserves explicit before/after snapshots and exposes deterministic deltas only for directly comparable numeric persisted values.

### Boundary

```
Dashboard
    ↓
HTTP
    ↓
CompareAnalysisSnapshots
    ↓
AnalysisResultStore
    ↓
Persisted Historical Snapshots
```

The comparison capability never executes fresh analysis and introduces no persistence schema change.

### Trade-offs

UUID selection is unambiguous even when multiple snapshots share a date, but clients must already know the snapshot IDs. A dedicated endpoint keeps comparison semantics separate from generic history retrieval, at the cost of one additional API resource.

### Consequences

The API returns before/after values and deterministic numeric deltas. Classification is represented as before/after plus a changed flag. Missing snapshots map to 404; cross-symbol selections and identical snapshot IDs are invalid requests. Dashboard presentation consumes the comparison read model and does not calculate deltas.


## DEC-082 — M23 Historical Performance Analytics

**Status:** Accepted  
**Date:** 2026-09-19

M23 introduces a read-only historical performance capability over two explicitly selected persisted analysis snapshots for the same stock.

The capability calculates absolute price change and percentage price change using the snapshots' `EntryContext.current_price` values and domain `Decimal` arithmetic. Caller-selected before/after direction is preserved.

Missing current prices produce unavailable performance metrics. A zero before price makes percentage performance unavailable without invalidating an otherwise calculable absolute change.

M23 does not execute fresh analysis, mutate or persist derived metrics, change scoring/classification, include dividends, costs, benchmarks, risk-adjusted returns, portfolio semantics, or predictive interpretation.

See `docs/DEC-082-M23-HISTORICAL-PERFORMANCE-ANALYTICS-DESIGN-GATE.md`.


## DEC-083 — M24 Historical Analysis Change Detection

**Status:** Accepted  
**Date:** 2026-09-19

M24 introduces a read-only `DetectAnalysisChanges` application capability over the existing M22 snapshot-comparison boundary. It detects descriptive changes in classification, analytical scores, current price, support, and resistance using deterministic dimension ordering.

The capability reuses M22 snapshot validation, treats optional-value availability transitions as changes, persists nothing, and introduces no significance thresholds or notification delivery. It does not interpret changes as favorable/unfavorable or actionable.

See `docs/DEC-083-M24-HISTORICAL-ANALYSIS-CHANGE-DETECTION-DESIGN-GATE.md`.


## DEC-084 — M25 Alert Delivery & Notification Boundary

**Status:** Accepted  
**Date:** 2026-09-19

M25 accepted the design gate for delivering existing AlertCandidate objects through a provider-neutral notification boundary. The proposed direction is a dedicated DeliverAlert application capability with delivery-state persistence and idempotency based on the existing analysis snapshot identity.

AnalysisResultRecord already exposes snapshot_id, but AlertCandidate must carry that identity before delivery implementation. Notification delivery must not recalculate analytical scores or classification and must not make analytical success depend on provider availability.

The first implementation is proposed to be synchronous and sequential, with provider-specific integrations behind infrastructure adapters. Provider retry/backoff and queue-based delivery are deferred.

See docs/DEC-084-M25-ALERT-DELIVERY-DESIGN-GATE.md.

## DEC-085 — M26 External Notification Provider Integration

**Status:** Accepted  
**Date:** 2026-09-19

M26 accepts Telegram Bot API as the first concrete provider behind the existing M25 `NotificationProvider` boundary.

Accepted constraints:

- Telegram bot token and recipient chat ID are infrastructure-only configuration.
- The synchronous provider timeout is 10 seconds.
- M26 adds no automatic provider retry.
- The adapter receives already-composed alert content and never recalculates analytical values.
- Provider failures affect delivery state only.
- Deterministic CI uses an HTTP fake/transport boundary and does not require live Telegram credentials.
- Multiple providers, queues, user preferences, and delivery analytics remain deferred.

See `docs/DEC-085-M26-EXTERNAL-NOTIFICATION-PROVIDER-DESIGN-GATE.md`.


## DEC-086 — M27 Alert Delivery Trigger & Transport Boundary

**Status:** Accepted  
**Date:** 2026-09-19

M27 opens a design gate for an explicit application/API trigger for delivering an existing `AlertCandidate` through the M25 provider-neutral delivery capability and the M26 Telegram provider.

The accepted MVP uses `POST /api/v1/alerts/{symbol}/deliver?channel=telegram`. The trigger resolves the candidate through `GetAlertCandidate`, delegates delivery to `DeliverAlert`, and keeps Telegram-specific behavior behind the existing provider boundary.

No candidate maps to 404; unconfigured delivery maps to 503; persisted delivery failures are returned as explicit FAILED outcomes with HTTP 200; repeated successful delivery remains idempotent. Delivery never executes fresh analysis or recalculates alert eligibility.

See `docs/DEC-086-M27-ALERT-DELIVERY-TRIGGER-DESIGN-GATE.md`.


## DEC-087 — M28 Automatic Alert Delivery Policy

**Status:** Accepted

### Context

M27 provides explicit single-alert delivery. M28 defines when the platform may automatically deliver existing alert candidates without coupling notification side effects to analytical execution.

### Decision

Automatic delivery is a dedicated post-analysis application capability.

It consumes the successful symbols from a completed market-analysis `Execution`, resolves existing candidates through `GetAlertCandidate`, and delegates delivery to `DeliverAlert`.

The MVP:

- uses one configured default channel: `telegram`;
- orders successful symbols deterministically by normalized symbol;
- continues after individual delivery failures;
- records aggregate delivery semantics separately from analysis execution state;
- persists only through the existing M25 `AlertDeliveryStore`;
- adds no automatic retry;
- relies on M25 snapshot/channel idempotency;
- does not trigger fresh analysis or recalculate alert eligibility.

### Alternatives Considered

Sending from `RunStockAnalysis` or `RunMarketAnalysis` was rejected because notification availability must not change analytical execution semantics.

Having the scheduler own notification policy was rejected because scheduling should trigger capabilities rather than decide business eligibility.

### Trade-offs

This keeps analysis and delivery failure domains independent and makes automatic delivery deterministic and testable.

The trade-off is an explicit post-analysis invocation boundary; automatic delivery is not implicitly guaranteed by every analysis call until a future orchestration requirement explicitly wires that trigger.

### Consequences

No new aggregate delivery persistence schema is introduced. Repeated runs reuse M25 idempotency. Multiple channels, user preferences, provider retries, asynchronous queues, and scheduled delivery policy remain separate future decisions.

### Revisit Conditions

Revisit when automatic delivery needs asynchronous processing, user-specific preferences, multiple channels, provider retries, or delivery scheduling policy.


## DEC-088 — M29 Scheduled Automatic Alert Delivery

**Status:** Accepted  
**Date:** 2026-09-19

M29 connects recurring configured-market analysis to the existing M28 automatic alert-delivery capability through a dedicated application workflow. The workflow runs configured-market analysis first, then passes the returned analysis Execution unchanged to M28.

If analysis returns COMPLETED or COMPLETED_WITH_ERRORS, delivery is invoked so M28 can process successful symbols recorded in the execution. If analysis returns FAILED, delivery is not invoked because there are no successful analysis outcomes eligible for scheduled delivery. If analysis raises before returning an Execution, delivery is also not invoked.

The workflow returns independent analysis and delivery outcomes. Delivery failure never changes analysis execution state. The scheduler remains responsible only for timing and recurrence; it does not inspect alert candidates, delivery state, or provider behavior.

Manual market analysis remains analysis-only. No new retry, idempotency, persistence, provider, or concurrency mechanism is introduced.

See `docs/DEC-088-M29-SCHEDULED-AUTOMATIC-ALERT-DELIVERY-DESIGN-GATE.md`.


## DEC-089 — M30 Durable Scheduled Workflow

**Status:** Accepted  
**Date:** 2026-09-19

M30 introduces a dedicated durable lifecycle boundary for scheduled M29 workflow occurrences. The workflow execution record is separate from analytical-result persistence and alert-delivery persistence.

The MVP uses stable workflow execution UUIDs plus the scheduler occurrence identity, with lifecycle states CREATED, RUNNING, COMPLETED, COMPLETED_WITH_ERRORS, FAILED, and INTERRUPTED. Duplicate starts are idempotent. Persisted RUNNING executions are detected during restart recovery and marked INTERRUPTED; they are not automatically resumed.

SQLite is the first implementation technology behind a dedicated ScheduledWorkflowExecutionStore. The MVP remains process-local and sequential and does not introduce queues, workers, distributed locks, provider retry, multiple channels, user-specific schedules, or automatic replay.

See `docs/DEC-089-M30-DURABLE-SCHEDULED-WORKFLOW-DESIGN-GATE.md`.


## DEC-090 — M31 Durable Scheduled Workflow Recovery

**Status:** Accepted  
**Date:** 2026-09-19

### Decision

Add an explicit, application-level recovery capability for one persisted INTERRUPTED scheduled workflow execution. Recovery reuses the existing workflow execution identity and existing M29 workflow rather than creating a new scheduled occurrence.

### Key constraints

- Only INTERRUPTED executions are recoverable.
- Recovery transitions through RUNNING and uses existing terminal states.
- No automatic startup replay is introduced.
- Existing analysis persistence and alert-delivery idempotency remain authoritative.
- No step-level checkpointing, distributed coordination, queues, or new retry layer are introduced.

See docs/DEC-090-M31-DURABLE-WORKFLOW-RECOVERY-DESIGN-GATE.md for the full trade-offs and acceptance criteria.


## DEC-091 — M32 Automatic Scheduled Workflow Resume

**Status:** Accepted  
**Date:** 2026-09-19

M32 accepts startup-triggered automatic recovery of persisted INTERRUPTED scheduled workflow executions. Startup inspects eligible executions, delegates recovery to the existing M31 capability, preserves workflow execution identity and existing analysis/alert-delivery idempotency, and remains sequential and process-local.

Durable-store inspection failure is an application startup failure. Individual recovery failures are isolated and do not prevent later eligible executions from being attempted. Terminal executions are ignored and no replacement scheduled occurrence is created.

No recovery HTTP endpoint, checkpointing, distributed coordination, queue/worker model, provider retry, or new notification behavior is introduced.

See `docs/DEC-091-M32-AUTOMATIC-WORKFLOW-RESUME-DESIGN-GATE.md`.


## DEC-092 — M33 Scheduled Workflow Operational Visibility

**Status:** Accepted  
**Date:** 2026-09-19

M33 introduces a provider-neutral, read-only application capability named `GetScheduledWorkflowExecutions` over the existing `ScheduledWorkflowExecutionStore`.

The accepted MVP exposes all persisted scheduled workflow executions, orders them deterministically by `created_at DESC, execution_id DESC`, and supports an exact optional `occurrence_id` filter. The read model preserves execution identity, occurrence identity, lifecycle state, timestamps, analysis state, and delivery state already persisted by the workflow model.

No workflow execution, recovery, scheduling, notification, analytical, or persistence-schema behavior changes. HTTP/dashboard exposure, real-time streaming, pagination/retention, authentication, metrics/tracing, and distributed execution remain deferred.

See `docs/DEC-092-M33-SCHEDULED-WORKFLOW-OPERATIONAL-VISIBILITY-DESIGN-GATE.md`.


## DEC-093 — M34 Scheduled Workflow Operational Visibility API

**Status:** Accepted  
**Date:** 2026-09-19

M34 exposes the M33 scheduled-workflow execution read capability through a read-only HTTP boundary at `GET /api/v1/workflows/executions`.

The endpoint returns an `items` envelope, supports an exact optional `occurrence_id` filter, preserves the M33 read-model fields, and maps unexpected application/infrastructure failures to the existing safe HTTP 500 pattern.

The scheduled-workflow store and read capability are composed independently of optional Telegram configuration so operational history remains observable without enabling notification delivery.

The endpoint does not execute, recover, schedule, notify, or recalculate workflows. Pagination, retention, authentication, real-time streaming, workflow mutation, and dashboard presentation remain deferred.

See `docs/DEC-093-M34-SCHEDULED-WORKFLOW-OPERATIONAL-VISIBILITY-API-DESIGN-GATE.md`.


## DEC-094 — M35 Scheduled Workflow Operational Dashboard

**Status:** Accepted  
**Date:** 2026-09-19

M35 adds a read-only scheduled-workflow operations panel to the existing React dashboard over the M34 HTTP read boundary.

The MVP loads executions explicitly, preserves API ordering, supports exact occurrence filtering, formats timestamps in the browser's local timezone, and exposes lifecycle/analysis/delivery state without creating new workflow semantics.

No automatic polling or workflow control is introduced. Empty, unavailable, and transport-error states are explicit presentation states. Workflow mutation, recovery controls, real-time streaming, pagination, authentication, metrics/tracing, and notification controls remain deferred.

See `docs/DEC-094-M35-WORKFLOW-OPERATIONAL-DASHBOARD-DESIGN-GATE.md`.


## DEC-095 — M36 Scheduled Workflow Recovery Control

**Status:** Proposed  
**Date:** 2026-09-19

M36 proposes an explicit operator-triggered recovery boundary for one persisted INTERRUPTED scheduled workflow execution. The preferred direction is a dedicated POST command that delegates to the existing M31 RecoverDurableScheduledWorkflow capability and preserves execution identity.

The dashboard would expose recovery only for interrupted rows. It would not mutate workflow state locally, create replacement occurrences, or introduce automatic polling.

Open decisions cover the non-recoverable HTTP status, dashboard action placement, post-recovery presentation, concurrent-click behavior, and whether recovery should remain available before an authentication boundary exists.

See docs/DEC-095-M36-SCHEDULED-WORKFLOW-RECOVERY-CONTROL-DESIGN-GATE.md.


---

# DEC-095 — M36 Scheduled Workflow Recovery Control

**Status:** Accepted  
**Date:** 2026-09-19

### Context

M31 established explicit recovery for one persisted INTERRUPTED scheduled workflow execution. M33–M35 exposed operational state through the application, API, and dashboard, but the dashboard remained read-only.

### Decision

M36 adds an explicit operator-triggered recovery command:

```
React Dashboard
      ↓
POST /api/v1/workflows/executions/{execution_id}/recover
      ↓
RecoverScheduledWorkflowExecution
      ↓
RecoverDurableScheduledWorkflow
      ↓
RunDurableScheduledWorkflow.recover
      ↓
ScheduledWorkflowExecutionStore
```

Only INTERRUPTED executions are eligible. The existing M31 recovery capability remains authoritative.

### Resolved Decisions

- Use **409 Conflict** for an existing execution that is not recoverable.
- Show an **inline Recover action** only on INTERRUPTED dashboard rows.
- Update the row immediately from the successful command response.
- Disable only the clicked row while recovery is pending.
- Proceed without authentication because no authentication boundary exists yet; authentication remains a prerequisite for multi-user exposure.

### Trade-offs

This adds a mutating HTTP/UI surface and therefore more state handling, but keeps workflow semantics in the application layer and makes recovery explicit, testable, and reusable outside the dashboard.

### Consequences

GET workflow visibility remains side-effect free. M36 does not create replacement occurrences, add a retry layer, change M31 recovery semantics, add a persistence schema, or introduce authentication.

### Revisit Conditions

Revisit if recovery becomes asynchronous, bulk recovery is required, authentication becomes mandatory, or workflow recovery semantics change.


## DEC-096 — M37 Authentication & Authorization Boundary

**Status:** Accepted  
**Date:** 2026-09-19

M37 establishes a single-operator bearer-token security boundary. `GET /health` remains public; all other application/API endpoints are protected. Authentication produces an immutable operator identity, authorization uses one operator permission, and protected application capabilities remain independent of FastAPI.

Missing/invalid credentials map to HTTP 401; authenticated callers without the required permission map to HTTP 403. The operator token is configuration-only, never persisted or logged. Multi-user identity, ownership, password/session management, external identity providers, and permission administration remain deferred.

See `docs/DEC-096-M37-AUTHENTICATION-AUTHORIZATION-DESIGN-GATE.md`.

## DEC-097 — M38 Multi-User Identity & Ownership

**Status:** Proposed  
**Date:** 2026-09-19

M38 opens the next security/product design gate after M37. The goal is to define a stable multi-user identity and ownership boundary without moving authentication or authorization rules into the analytical domain.

The gate must resolve identity source, immutable user identifiers, ownership semantics, credential/session responsibility, user lifecycle, persistence scoping, API authorization behavior, migration from the current single-operator token, and deterministic ownership-isolation testing.

Implementation is not authorized until these decisions are accepted.

See `docs/DEC-097-M38-MULTI-USER-IDENTITY-DESIGN-GATE.md`.

## DEC-097 — M38 Multi-User Identity & Ownership

**Status:** Accepted  
**Date:** 2026-09-19

### Decision

M38 adopts a hybrid application identity boundary with an immutable internal user UUID.

The application owns identity and resource-ownership semantics. Authentication remains behind a replaceable adapter and supplies an authenticated application identity rather than raw credentials.

User-owned resources use explicit `owner_user_id` references. System/global resources remain explicitly unowned. Existing M37 data is classified as system-owned legacy data until an explicit migration operation establishes user ownership.

Authorization is ownership-first for the M38 MVP. Roles, organizations, delegated access, and team administration are deferred.

User lifecycle states are ACTIVE, DISABLED, and DELETED. Disabled/deleted identities cannot access protected resources; historical ownership remains attributable.

API authorization semantics are:
- unauthenticated → 401;
- authenticated but not owner → 403;
- authenticated and resource absent → 404.

M37's single-operator token remains temporarily supported as a compatibility adapter mapped to a designated legacy/system operator identity. It must not bypass user ownership.

### Reasoning

This preserves the separation between authentication mechanism and application identity/ownership, allows future external identity integration without changing ownership semantics, and avoids prematurely introducing organizations or role-management concepts.

### Consequences

User-owned capabilities must introduce explicit ownership at the application/persistence boundary. Domain analytical services remain identity-agnostic. Ownership checks are centralized in application authorization rather than duplicated across API controllers or dashboard components.

M38 requires deterministic ownership-isolation tests and persistence/reload coverage.

See `docs/DEC-097-M38-MULTI-USER-IDENTITY-DESIGN-GATE.md`.


## DEC-098 — M38 Identity Persistence & Capability Migration

**Status:** Accepted  
**Date:** 2026-09-19

### Decision

Identity persistence uses a dedicated application `UserStore` boundary backed by the existing SQLite deployment. Identity persistence remains separate from analytical persistence.

The first user-owned durable capability is `ScheduledWorkflowExecution`. Ownership is represented by `owner_user_id`: NULL means system/global legacy ownership for this capability, while a non-null UUID is explicit user ownership.

Historical scheduled-workflow executions are not silently reassigned. The deterministic M37 `LEGACY_OPERATOR_USER_ID` is materialized idempotently as a compatibility identity, but existing legacy records remain system/global.

Disabled and deleted users retain historical ownership metadata but cannot access protected resources. Repository writes remain locally atomic; a cross-repository transaction is deferred until a future command requires atomic changes across identity and capability state.

New user-owned scheduled-workflow operations require an active authenticated identity and the centralized ownership authorization boundary. Legacy operator compatibility remains limited to system/global records.

See `docs/DEC-098-M38-IDENTITY-PERSISTENCE-DESIGN-GATE.md`.


## DEC-099 — M39 Multi-User Authentication & Identity Transport

**Status:** Accepted  
**Date:** 2026-09-19

### Decision

M39 establishes the transport/application identity boundary using configured per-user bearer credentials as the first concrete authentication adapter.

The adapter resolves credentials to an immutable internal user UUID, consults durable user lifecycle state on every protected request, and returns only `AuthenticatedIdentity` to application capabilities.

The first migrated user-owned API/application capability is scheduled workflow execution read/recovery:

- `GET /api/v1/workflows/executions`
- `POST /api/v1/workflows/executions/{execution_id}/recover`

Ownership checks remain centralized in the existing application authorization boundary.

M37 operator-token authentication remains temporarily supported as a compatibility path and maps only to `LEGACY_OPERATOR_USER_ID`. Its removal requires a separate explicit decision.

M39 is API/application focused; frontend login/session UX is deferred to a separate slice.

### Provisioning and lifecycle

M39 does not introduce a local username/password system or user-management product. Credential-to-user mappings are deployment configuration. Removing or changing a mapping revokes that credential after configuration reload/restart. Durable user lifecycle state remains authoritative: ACTIVE may authenticate; DISABLED, DELETED, and missing users may not.

### Trade-offs

This approach keeps the first multi-user transport implementation deterministic and controlled without coupling the application to a commercial identity provider or introducing password/session infrastructure.

The trade-off is that configuration-based credentials are not a complete identity-management solution. Credential rotation/revocation is deployment/configuration work, and external IdP integration remains a future boundary.

### Consequences

Credentials stay outside domain entities. Application capabilities receive an authenticated identity rather than raw credentials. Identity is resolved on every protected request, so lifecycle changes take effect without cache delay.

The transport contract remains replaceable: a future external identity provider may implement the same identity-resolution boundary without changing ownership semantics.

See `docs/DEC-099-M39-MULTI-USER-AUTHENTICATION-DESIGN-GATE.md`.





## DEC-100 — M40 Frontend Authentication & Session UX

**Status:** Accepted  
**Date:** 2026-09-19

M40 adds browser login/session UX over the existing M39 multi-user bearer authentication boundary.

The frontend accepts a configured bearer credential, stores it in `sessionStorage`, validates it through `GET /api/v1/auth/me`, sends the credential only in the HTTP Authorization header, and clears the session on explicit logout or HTTP 401. HTTP 403 remains an authorization error and does not silently log the user out.

M40 removes the previous build-time `VITE_OPERATOR_TOKEN` dependency from the frontend. The browser does not issue credentials, manage passwords, refresh tokens, or implement identity-provider flows.

The new `GET /api/v1/auth/me` endpoint returns only the authenticated subject, immutable user ID, and lifecycle status; it never returns raw credentials.

See `docs/DEC-100-M40-FRONTEND-AUTHENTICATION-DESIGN-GATE.md`.


## DEC-101 — M40 User Credential & Session Lifecycle

**Status:** Accepted  
**Date:** 2026-09-19

M40 adopts durable application-managed opaque bearer credentials mapped to the existing immutable internal user UUID. Credential lifecycle state is persisted behind a dedicated CredentialStore using the existing SQLite deployment.

Raw credentials are never persisted, logged, returned after provisioning, or placed in domain entities. Provisioning and rotation return a raw credential exactly once. Credentials are ACTIVE, REVOKED, or REPLACED; automatic expiration is deferred for this MVP. Rotation invalidates the previous credential.

The existing M40 frontend session UX remains valid: the browser holds the bearer credential in sessionStorage for the browser session and validates it through GET /api/v1/auth/me. The server remains authoritative by resolving the presented credential against durable credential state on every protected request. No second server-side session store, local password system, MFA/SSO, or commercial identity provider is introduced in this slice.

M39 configured credentials remain a compatibility path. Their raw values are never migrated into durable credential storage. Removal of M39 compatibility requires a separate decision.

Credential lifecycle remains separate from identity and authorization: authentication produces AuthenticatedIdentity, while ownership authorization remains unchanged.

See docs/DEC-101-M40-USER-CREDENTIAL-LIFECYCLE-DESIGN-GATE.md.


## DEC-102 — M41 User Management & Credential Administration

**Status:** Accepted  
**Date:** 2026-09-19

### Decision

M41 adopts self-service credential administration plus operator-controlled user lifecycle administration.

Operators may create, disable, reactivate, and delete users and administer credentials for users. Authenticated users may rotate their own credential atomically with replacement. Full self-service registration is deferred.

The designated legacy/system operator identity is the bootstrap administrator for creating the first non-legacy users.

Deletion is represented by the existing `DELETED` lifecycle state rather than physical identity removal. Historical ownership remains attributable to the deleted UUID and is never silently reassigned.

M41 does not introduce profile fields beyond the existing immutable UUID and lifecycle state.

Security-sensitive lifecycle and credential commands emit minimal durable audit records containing actor, action, target, timestamp, and outcome metadata. Raw credentials and credential hashes are never stored in audit records.

Management is exposed as application capabilities with thin API/dashboard transport. Operator authorization remains centralized; dashboard code does not implement identity or authorization rules.

### Alternatives Considered

- Operator-only administration: smaller surface, but requires operator intervention for routine credential changes.
- Self-service credential administration: selected; preserves controlled account lifecycle while giving users routine credential autonomy.
- Full self-service user management: deferred because registration, recovery, abuse protection, and profile lifecycle would expand the security/product scope substantially.

### Trade-offs

The selected model adds a small self-service capability while retaining controlled provisioning and lifecycle changes. It requires explicit authorization separation, atomic credential replacement, and minimal durable auditability.

The model does not solve registration, password recovery, MFA/SSO, external identity integration, or organizational administration.

### Consequences

The existing M38/M39/M40 identity, ownership, and credential boundaries remain authoritative. Credentials remain outside domain entities. Management commands become reusable application capabilities that can later support additional transports without moving policy into FastAPI or React.

### Revisit Conditions

Revisit when public registration, external identity providers, richer roles, organizations, recovery workflows, or user-facing audit reporting become requirements.

See `docs/DEC-102-M41-USER-MANAGEMENT-DESIGN-GATE.md`.

## DEC-103 — M42 Management Audit Reporting

**Status:** Accepted  
**Date:** 2026-09-19

M42 establishes a read-only management-audit reporting capability over the durable audit boundary introduced by M41.

### Decision

The MVP is operator-only and reuses the existing operator authorization boundary. A dedicated `GetManagementAudit` application capability reads through `ManagementAuditStore`; API and dashboard layers remain thin transport/presentation boundaries.

The read model exposes immutable actor and target UUIDs, action, outcome, and stored UTC timestamp. Deleted identities remain attributable by UUID.

Optional filters are actor ID, target ID, action, outcome, and UTC time range with AND semantics. Ordering is authoritative as `occurred_at DESC, audit_id DESC`.

Bounded pagination is mandatory: default page size 50, maximum 100. The API returns an `items` envelope with explicit pagination metadata. Retention is unchanged and no audit records are deleted or archived by M42.

The dashboard exposes a read-only operator view and does not implement authorization or audit semantics.

### Reasoning

This keeps security-management evidence separate from workflow operational visibility, prevents unbounded reads, preserves historical attribution, and keeps SQLite replaceable.

### Consequences

M42 adds a dedicated read model and pagination contract but does not change M41 audit writes. No new permission, retention policy, real-time stream, SIEM integration, analytics, or user self-service audit history is introduced.

See `docs/DEC-103-M42-MANAGEMENT-AUDIT-REPORTING-DESIGN-GATE.md`.
