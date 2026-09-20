# Engineering Rules

**Project:** EGX Stock Analyzer
**Status:** Maintained — M56
**Purpose:** Define the engineering process, coding discipline, testing workflow, and development rules used to build the system.

---

## 1. Purpose

This document defines how the EGX Stock Analyzer is engineered.

It exists to prevent:

- random implementation
- premature coding
- architectural drift
- untested business rules
- unclear ownership
- unnecessary complexity
- AI-generated code that nobody understands

The objective is not simply to make the code work.

The objective is to build a system that is:

- understandable
- testable
- maintainable
- explainable
- extensible
- replaceable
- reliable

---

# 2. Development Philosophy

The project follows:

> **Understand → Map → Design → Discuss Trade-offs → Decide → Test → Implement → Review → Refactor → Document → Learn → Update the Map**

Coding is only one step in the process.

A feature is not considered ready merely because its code works.

---

# 3. Design Before Implementation

Before implementing a new domain concept, we must understand:

1. What is it?
2. What does it mean?
3. Why does it exist?
4. Who owns it?
5. What is responsible for it?
6. What is explicitly not responsible for it?
7. What does it depend on?
8. What depends on it?
9. What alternatives exist?
10. What trade-offs are involved?

If these questions cannot be answered, implementation should normally stop.

---

# 4. Design Gate

Every meaningful domain feature passes through a Design Gate.

## Required questions

### Concept

What is the concept?

### Meaning

What does it represent in the business/domain?

### Responsibility

What behavior belongs to it?

### Non-responsibility

What behavior does NOT belong to it?

### Ownership

Which object/module owns the rule?

### Boundaries

Where does the responsibility begin and end?

### Alternatives

What other designs were considered?

### Trade-offs

What do we gain and what do we sacrifice?

### Assumptions

What are we currently assuming?

### Open Decisions

What remains undecided?

### Committed Decisions

What have we explicitly decided?

---

# 5. TDD Workflow

For domain behavior, the preferred workflow is:

```text
RED
 ↓
GREEN
 ↓
REVIEW
 ↓
REFACTOR
```

## RED

Write a test describing the behavior we want.

The test should fail for the expected reason.

## GREEN

Implement the smallest amount of code necessary to make the test pass.

Do not prematurely implement future behavior.

## REVIEW

Ask:

- Does the implementation represent the domain correctly?
- Is the responsibility in the right place?
- Is the abstraction necessary?
- Are we hiding an important business rule?
- Did we accidentally introduce coupling?

## REFACTOR

Improve the implementation without changing behavior.

Tests must remain green.

---

# 6. Tests Are Part of the Design

Tests are not only verification.

They are executable documentation of domain behavior.

A good domain test should help answer:

> "What does this concept mean?"

Tests should therefore favor meaningful business behavior over implementation details.

Prefer:

```python
assert stock.symbol == "COMI"
```

over testing private implementation details.

Avoid tests that become tightly coupled to internal implementation unless that implementation itself is part of the contract.

---

# 7. One Behavior at a Time

When developing a domain concept, introduce behavior incrementally.

Example:

```text
Create Stock
    ↓
Normalize symbol
    ↓
Validate required fields
    ↓
Define identity
    ↓
Define equality
```

Do not implement all imaginable Stock behavior at once.

Each behavior should have a reason to exist.

---

# 8. Smallest Useful Implementation

During GREEN:

> Implement the smallest solution that satisfies the current requirement.

Do not add:

- speculative abstractions
- unused interfaces
- future database support
- unnecessary factories
- unnecessary dependency injection
- unused configuration
- premature optimization

The next requirement may invalidate today's assumptions.

---

# 9. No Speculative Architecture

Do not create abstractions simply because they might be useful later.

For example, do not create:

```text
IStockRepository
IStockFactory
IStockValidator
IStockNormalizer
IStockManager
IStockCoordinator
```

unless the domain actually requires those boundaries.

Architecture should emerge from real requirements and stable responsibilities.

---

# 10. Responsibility Must Have an Owner

Every business rule should have an identifiable owner.

For example:

```text
Stock
    → identity and stock-specific invariants

MarketData
    → market observation representation

DataQuality
    → data quality assessment

TechnicalAnalysis
    → technical calculations

Scoring
    → score calculation

SignalGeneration
    → interpretation of analysis into signals
```

If a rule cannot be assigned to a clear owner, stop and redesign.

---

# 11. Avoid God Objects

No object should become responsible for everything.

For example, a future `Stock` object must not become responsible for:

- downloading market data
- calculating RSI
- calculating financial ratios
- scoring itself
- sending alerts
- storing itself in the database

Those responsibilities belong to different boundaries.

---

# 12. Domain Independence

The domain should not depend directly on:

- FastAPI
- HTTP
- SQLAlchemy
- PostgreSQL
- external market-data APIs
- UI frameworks
- notification providers
- AI providers

The direction should remain conceptually:

```text
External Systems
       ↓
Application / Infrastructure
       ↓
Domain
```

The domain should contain business meaning, not infrastructure details.

---

# 13. Dependency Direction

Dependencies should point toward stable business concepts.

Prefer:

```text
API
 ↓
Application
 ↓
Domain
```

and:

```text
Infrastructure
 ↓
Application / Domain contracts
```

Avoid allowing infrastructure details to leak into domain objects.

---

# 14. External Providers Must Be Replaceable

Market-data providers may change.

Therefore provider-specific behavior must not become part of the core domain model.

The system should be able to change:

```text
Provider A
```

to:

```text
Provider B
```

without rewriting the domain.

The same principle applies to:

- AI providers
- notification providers
- storage providers
- external APIs

---

# 15. AI-Assisted Development Rule

AI may help with:

- implementation
- brainstorming
- refactoring
- test generation
- documentation
- debugging
- alternative designs

But AI does not own architectural decisions.

The developer must understand:

- what was implemented
- why it was implemented
- what assumptions were made
- what trade-offs exist
- what could break

Never merge code merely because:

> "The AI generated it and the tests passed."

Tests are necessary, but understanding is mandatory.

---

# 16. AI Must Not Become the Architecture

AI should remain a replaceable capability.

The system must not depend on one specific AI provider or model unless that dependency is an explicit business requirement.

The core system should remain functional without requiring AI for basic domain correctness.

---

# 17. External Data Philosophy

External market data is an observation.

It is not automatically absolute truth.

Therefore:

```text
Provider
   ↓
Raw Observation
   ↓
Data Quality Assessment
   ↓
Analysis
```

The system should distinguish between:

- received data
- validated data
- suspicious data
- unusable data

We should avoid silently destroying information unless there is a strong reason.

---

# 18. Do Not Over-Validate External Reality

The system should distinguish between:

### Domain invariant

Something that must always be true because of the meaning of the domain object.

and:

### External-data expectation

Something that we normally expect to be true but which may indicate a bad observation.

These should not automatically be treated the same way.

Example:

```text
High < Open
```

may indicate a data-quality problem.

That does not automatically mean the system should destroy or reject the observation.

The final behavior must be decided at the appropriate data-quality boundary.

---

# 19. Business Rules vs Technical Rules

Business rules belong to the domain.

Technical rules belong to engineering/infrastructure.

Example:

```text
"BUY requires score >= X"
```

is a business rule.

While:

```text
"Use PostgreSQL connection pooling"
```

is a technical rule.

Do not mix them.

---

# 20. Deterministic Scoring

The scoring engine should be deterministic for the same:

```text
Input Data
+
Strategy Version
+
Configuration
```

Therefore:

```text
Same inputs
      ↓
Same strategy
      ↓
Same score
```

unless randomness is explicitly part of the design.

---

# 21. Strategy Versioning

Analysis strategies will evolve.

Therefore historical results must eventually be associated with the strategy version that produced them.

Example:

```text
Strategy v1
Strategy v2
Strategy v3
```

A backtest or historical signal should not become impossible to reproduce because the scoring formula changed.

---

# 22. Separate Quality From Opportunity

The system should distinguish between:

### Stock Quality

How fundamentally/structurally strong the stock is.

and:

### Entry Quality

Whether the current market conditions provide an attractive entry.

A strong company does not automatically mean:

> BUY NOW

Likewise, a technically attractive setup does not automatically mean:

> High-quality company

These concepts must remain separate.

---

# 23. Signals Are Conclusions

A signal is not raw market data.

Conceptually:

```text
Market Data
    ↓
Analysis
    ↓
Evidence
    ↓
Score
    ↓
Signal
```

A signal should therefore be explainable.

For example:

```text
BUY

Score: 82/100

Reasons:
- Strong momentum
- Price near support
- Positive earnings trend
- Healthy liquidity

Risks:
- High volatility
```

The exact rules will be defined later.

---

# 24. No Silent Failure

Important failures must be visible.

Avoid patterns where the system silently:

- ignores invalid data
- skips stocks
- drops provider failures
- replaces values without recording it
- generates incomplete analysis

The system should eventually provide observability into:

```text
What happened?
Why did it happen?
What data was used?
What failed?
What was skipped?
```

---

# 25. Error Handling

Errors should be handled at the appropriate boundary.

Do not catch every exception everywhere.

Avoid:

```python
try:
    ...
except Exception:
    pass
```

unless there is an explicit and justified reason.

Errors should either:

- be handled meaningfully
- be transformed into an appropriate domain/application error
- or propagate to a boundary that can handle them correctly

---

# 26. Refactoring Rule

Refactoring is allowed only when behavior remains unchanged.

Before refactoring:

```text
Tests Green
```

After refactoring:

```text
Tests Green
```

If behavior needs to change, that is not merely refactoring.

It is a new design/change.

---

# 27. Code Review Questions

Before considering a feature complete, ask:

### Correctness

Does it implement the intended behavior?

### Domain

Does the code represent the business meaning correctly?

### Ownership

Is the rule owned by the correct component?

### Coupling

Did we introduce unnecessary dependencies?

### Simplicity

Is there a simpler design?

### Testability

Can the behavior be tested easily?

### Explainability

Can we understand why the system produced a result?

### Extensibility

Can we change the implementation without breaking unrelated areas?

### Documentation

Did an important decision need to be documented?

---

# 28. Git Discipline

Each meaningful change should be represented by a focused commit.

Prefer:

```text
Add Stock identity behavior
```

over:

```text
Update project
```

Good commits should communicate intent.

Avoid mixing unrelated changes into one commit.

---

# 29. Commit After Stable Milestones

A useful milestone is:

```text
Design
→ Tests
→ Implementation
→ Review
→ Refactor
→ Green
→ Commit
```

Do not commit broken intermediate states unless there is a deliberate reason.

---

# 30. Definition of Done

A feature is considered done when:

- The behavior is understood.
- Ownership is clear.
- Design decisions are explicit.
- Tests exist for important behavior.
- Tests pass.
- Implementation is reviewed.
- Unnecessary complexity is removed.
- Documentation is updated when necessary.
- Git state is clean or intentionally contains the next change.
- The developer understands the implementation.

---

# 31. When to Stop Coding

Stop coding and return to design when:

- responsibilities become unclear
- multiple objects appear to own the same rule
- a rule keeps moving between classes
- tests become difficult to write
- implementation requires many exceptions
- external-provider details leak into the domain
- the model no longer represents the business meaning
- a requirement contradicts an existing architectural decision

This is not failure.

It is a design signal.

---

# 32. Learning From Implementation

After meaningful implementation, record important lessons.

Examples:

```text
What did we assume?
What did we discover?
What changed our thinking?
What trade-off did we make?
What should we avoid next time?
```

These lessons belong in:

```text
docs/LESSONS_LEARNED.md
```

when they are reusable beyond a single line of code.

---

# 33. Documentation Rule

Documentation should explain:

- why
- meaning
- boundaries
- decisions
- trade-offs

Documentation should not merely repeat the code.

Bad documentation:

```text
Stock.create creates a stock.
```

Useful documentation:

```text
Stock.create represents creation of a new Stock entity
and therefore generates a new internal identity.
```

---

# 34. Architecture Change Rule

If a change significantly affects:

- domain boundaries
- ownership
- dependency direction
- data semantics
- strategy behavior
- persistence architecture
- provider abstraction

then the change should be recorded in:

```text
docs/DECISION_LOG.md
```

or an ADR.

---

# 35. Current Engineering Baseline

Current project baseline:

```text
Python 3.13
pytest
Git
Modular Monolith direction
Domain-first development
TDD for domain behavior
```

Current known test baseline is maintained by the repository CI pipeline rather than a fixed test-count checkpoint.

The exact passing count may evolve as coverage grows; CI success is the authoritative validation signal for the current branch.

---

# 36. Engineering Principle

The primary engineering principle is:

> **Do not optimize for writing more code. Optimize for building correct understanding into the system.**

The code is the result of the design.

The tests protect the behavior.

The documentation preserves the decisions.

The architecture protects the boundaries.

And the developer remains responsible for understanding all of them.

---

# 37. Current Status

This document is currently:

**Maintained — M48**

The rules remain active and may evolve only through intentional project-level decisions.

Changes to this document should be intentional and should not be used to justify arbitrary architectural changes after implementation.

---
