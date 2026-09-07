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
