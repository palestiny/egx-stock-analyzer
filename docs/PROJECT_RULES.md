# EGX Stock Analyzer — Project Rules

## 1. Purpose

This document defines the rules that govern the EGX Stock Analyzer project.

These rules exist to prevent uncontrolled architectural changes, premature implementation, and inconsistent business decisions.

They are project-level rules and apply to all modules unless an explicit architectural decision overrides them.

---

# 2. Core Rule

> **Do not implement a business rule before its meaning and ownership are understood.**

Code should be the result of a design decision, not the place where the design decision is accidentally made.

---

# 3. Domain Comes First

The domain model is the center of the system.

Infrastructure must not dictate the domain model.

The following should not define business concepts:

- Database schema
- ORM limitations
- API models
- External provider formats
- UI requirements
- AI provider APIs

Instead:

```text
Business Meaning
       ↓
Domain Model
       ↓
Application Logic
       ↓
Infrastructure
       ↓
External Systems
```

---

# 4. External Data Is Not Automatically Truth

Market data originates from external systems.

Therefore:

```text
Received Data ≠ Proven Correct Data
```

The system must distinguish between:

- Observation
- Validation
- Quality assessment
- Analytical usability

We must not silently modify external observations merely to make them fit our assumptions.

If an observation appears suspicious, the preferred direction is to preserve it and classify or flag its quality where appropriate.

---

# 5. Preserve Information

The system should avoid destructive transformations of source information unless there is a clear reason.

Prefer:

```text
Raw Observation
      ↓
Normalized Representation
      ↓
Quality Assessment
      ↓
Analysis Representation
```

rather than:

```text
External Data
      ↓
Aggressive Validation
      ↓
Discard
```

This is particularly important for historical financial analysis and future backtesting.

---

# 6. Business Rules Must Have an Owner

Every business rule must belong to a clearly identified component.

For example:

```text
Stock
    → Stock identity rules

Market Data
    → Observation representation

Data Quality
    → Data-quality rules

Technical Analysis
    → Technical interpretation

Scoring
    → Score calculation

Signal Generation
    → Trading-signal rules
```

A class should not accumulate rules simply because it is convenient to place them there.

---

# 7. Avoid God Objects

No entity, service, or module should become responsible for unrelated concerns.

For example, a `Stock` should not become responsible for:

- Downloading market data.
- Calculating RSI.
- Calculating financial ratios.
- Sending notifications.
- Calling AI services.
- Generating reports.

Responsibilities must remain separated according to domain meaning.

---

# 8. Explicit Boundaries

Every module must have:

1. A clear responsibility.
2. A defined input.
3. A defined output.
4. Explicit dependencies.
5. Clear non-responsibilities.

If two modules repeatedly need each other's internal details, the boundary should be reconsidered.

---

# 9. Dependency Direction

Dependencies should generally point toward stable business concepts.

Preferred direction:

```text
Infrastructure
      ↓
Application
      ↓
Domain
```

The domain must not depend directly on:

- Database implementations.
- HTTP clients.
- FastAPI.
- External APIs.
- AI SDKs.
- UI frameworks.

---

# 10. External Providers Must Be Replaceable

Market-data providers are external dependencies.

The domain must not become coupled to a specific provider.

Avoid designs where:

```text
Domain
   ↓
Provider X API
```

Prefer an abstraction boundary:

```text
Domain / Application
        ↓
Market Data Port
        ↓
Provider Adapter
        ↓
External Provider
```

This allows providers to be replaced without rewriting domain logic.

---

# 11. AI Must Remain Replaceable

AI is an optional capability.

The system must not depend on one specific AI provider.

Avoid:

```text
Core Domain
     ↓
OpenAI / Provider X
```

Prefer:

```text
Application
     ↓
AI Capability / Interface
     ↓
AI Adapter
     ↓
Provider
```

If the AI provider changes, the core system should remain functional.

---

# 12. No Premature Microservices

The initial architecture is a Modular Monolith.

We will not introduce microservices merely because the system contains multiple modules.

A module should first demonstrate a real need for independent deployment, scaling, ownership, or operational isolation before becoming a service.

Current direction:

```text
One Application
     │
     ├── Stock
     ├── Market Data
     ├── Data Quality
     ├── Technical Analysis
     ├── Fundamental Analysis
     ├── Scoring
     ├── Signals
     ├── Backtesting
     └── Reporting
```

---

# 13. Do Not Design for Imaginary Requirements

We should not introduce abstractions solely because they might be useful someday.

Before adding an abstraction, ask:

```text
What problem exists today?
Why is the abstraction necessary?
What complexity does it introduce?
What alternative was considered?
```

Future flexibility is valuable, but unnecessary abstraction is technical debt.

---

# 14. Explainability Is a Requirement

Analytical results must eventually be explainable.

The system should prefer:

```text
Signal
   ↓
Score
   ↓
Factors
   ↓
Evidence
```

rather than:

```text
Signal
   ↓
"AI says BUY"
```

AI-generated results may be used as evidence, but unexplained output should not silently become a business decision.

---

# 15. Scoring Must Be Deterministic

The scoring engine should produce the same result for the same inputs and configuration.

For example:

```text
Same Data
+
Same Rules
+
Same Configuration
=
Same Score
```

Any intentional non-deterministic behavior must be explicitly identified and justified.

---

# 16. Separate Stock Quality From Entry Quality

The system should distinguish between:

### Stock Quality

> "Is this a good stock according to our criteria?"

and:

### Entry Quality

> "Is this a good moment to enter this stock?"

A fundamentally strong stock may have a poor entry point.

Likewise, a technically attractive entry does not automatically mean the underlying stock is high quality.

These concepts should not be collapsed into one unexplained score.

---

# 17. Signals Are Conclusions, Not Raw Data

A signal such as:

```text
BUY
WATCH
HOLD
AVOID
```

must be derived from analytical evidence.

The system should maintain a conceptual chain:

```text
Market Observation
       ↓
Analysis
       ↓
Metrics
       ↓
Scores
       ↓
Decision Rules
       ↓
Signal
```

A signal should never become the primary source of truth.

---

# 18. Historical Reproducibility

Historical analysis must eventually be reproducible.

When possible, a historical result should be traceable to:

- Data used.
- Timestamp.
- Data source.
- Data-quality state.
- Strategy version.
- Scoring configuration.
- Signal rules.

This is especially important for backtesting.

---

# 19. Strategy Versions Matter

Analytical rules will evolve.

Therefore, changing a scoring formula should not make historical results impossible to understand.

The system should eventually distinguish between strategy versions, for example:

```text
Strategy v1
Strategy v2
Strategy v3
```

Historical results should identify which strategy produced them.

The exact implementation is not yet decided.

---

# 20. Configuration Is Not Business Logic

Configuration should control parameters such as:

- Weights.
- Thresholds.
- Provider settings.
- Scheduling.
- Feature flags.

Business behavior should remain explicit in the appropriate domain/application component.

Do not hide important business rules inside arbitrary configuration files.

---

# 21. No Silent Failure

Important failures must not disappear silently.

Examples include:

- Data-provider failure.
- Missing market data.
- Invalid response.
- Database failure.
- Analysis failure.
- Report-generation failure.

The system should eventually provide sufficient information to determine:

```text
What failed?
When?
Where?
Why?
What data was affected?
```

---

# 22. Tests Are Part of the Design

Tests are not only verification after implementation.

A test should help define expected behavior.

Preferred workflow:

```text
Requirement
    ↓
Behavior
    ↓
Test
    ↓
Implementation
```

Tests should describe meaningful behavior rather than implementation details.

---

# 23. Do Not Over-Validate External Reality

The system must distinguish between:

```text
Impossible according to domain invariant
```

and:

```text
Unexpected according to our assumptions
```

Unexpected external data should not automatically be rejected.

Before adding validation, ask:

1. Is this a mathematical invariant?
2. Is this a market-domain invariant?
3. Can real market behavior violate it?
4. What information would be lost by rejecting it?
5. Should it instead be classified as suspicious?

---

# 24. Database Is Not the Domain

Database tables are persistence representations.

They should not automatically become domain entities.

For example:

```text
Database Table
      ≠
Domain Entity
```

The persistence model may be optimized for storage while the domain model is optimized for business meaning.

---

# 25. API Is Not the Domain

API DTOs should not automatically become domain objects.

The API exists to communicate with clients.

The domain exists to represent business meaning.

Therefore:

```text
API Request
    ↓
Application
    ↓
Domain
```

rather than:

```text
API Request = Domain Entity
```

---

# 26. UI Must Not Define Business Rules

The frontend may display:

```text
BUY
WATCH
HOLD
AVOID
```

but it must not decide why a stock receives that signal.

Business decisions belong to the backend domain/application layers.

---

# 27. Documentation Is Part of the System

Important architectural and business decisions must be documented.

At minimum, the project should maintain:

```text
PROJECT_BLUEPRINT.md
PROJECT_RULES.md
ENGINEERING_RULES.md
ROADMAP.md
DECISION_LOG.md
LESSONS_LEARNED.md
ADR/
```

Documentation should reflect actual decisions.

Do not document an architecture that the code does not actually follow.

---

# 28. Decisions Must Be Explicit

When a significant architectural decision is made, record:

```text
Decision
Context
Options
Trade-offs
Reason
Consequences
Status
```

If a decision is later changed, the old decision should remain part of the project history.

---

# 29. No Architectural Drift

Before introducing a new technology, pattern, module, or dependency, ask:

```text
Does this fit the Blueprint?
Does it violate a Project Rule?
Does it introduce a new architectural decision?
Does that decision need an ADR?
```

If the answer indicates a significant change, stop implementation and update the design first.

# 30. Design Patterns Are a Learning Objective

Design Patterns are an explicit learning objective of this project.

We will actively learn and apply Design Patterns when a real design problem in the system justifies their use.

The rule is:

> **Use a Design Pattern when a real design problem justifies it — never use a pattern merely to increase the number of patterns in the project.**

Whenever a pattern is considered, the design process should identify:

1. The actual problem being solved.
2. The candidate pattern or patterns.
3. Why the selected pattern fits the problem.
4. Alternative designs that were considered.
5. Trade-offs introduced by the pattern.
6. The consequences for maintainability, flexibility, complexity, and testability.
7. What was learned from the implementation.

Patterns should therefore be treated as engineering tools and learning opportunities, not decorations or architectural goals by themselves.

Examples of patterns that may become relevant include:

- Strategy
- Factory
- Adapter
- Observer
- State
- Repository
- Facade
- Pipeline / Chain of Responsibility

## These are examples only. No pattern is considered required until a real problem justifies it.

# 31. Definition of "Done"

A feature is not considered complete merely because:

```text
Code works
```

A meaningful feature should satisfy:

```text
Design
  ↓
Test
  ↓
Implementation
  ↓
Review
  ↓
Refactor
  ↓
Documentation
  ↓
Tests Passing
  ↓
Commit
```

---

# 32. Git Rule

The repository is part of the engineering workflow.

The expected cycle is:

```text
Design
   ↓
Implement
   ↓
Test
   ↓
Review
   ↓
Commit
   ↓
Push
   ↓
GitHub
```

Commits should represent meaningful project progress.

Avoid commits that mix unrelated changes.

---

# 33. Current Project State

At the time of establishing these rules:

- Repository: `egx-stock-analyzer`
- Primary branch: `main`
- GitHub remote is configured.
- Local project is connected to GitHub.
- Domain tests are passing.
- Current known test baseline: 17 passing tests.
- Current implementation is through **M13 — Operational Runtime Baseline + SQLite Persistence MVP**.
- The project remains under active development; new capabilities require an explicit design gate.
- Market Data validation responsibilities remain under design.

---

# 34. Rule for Uncertainty

When we do not know something:

> **Do not guess silently.**

Instead:

```text
Unknown
  ↓
Identify the question
  ↓
Research / Discuss
  ↓
Evaluate alternatives
  ↓
Decide
  ↓
Document
  ↓
Implement
```

---

# 35. Rule for AI-Assisted Development

AI may propose:

- Designs.
- Code.
- Tests.
- Refactorings.
- Alternatives.

But AI-generated suggestions are not automatically project decisions.

The human/project owner makes the final architectural decision.

Before accepting a significant AI suggestion:

```text
Understand
→ Challenge
→ Compare
→ Decide
```

---

# 36. Final Principle

The project should be built deliberately.

We prefer:

```text
Clear Design
+
Small Steps
+
Strong Tests
+
Explicit Decisions
+
Documented Trade-offs
```

over:

```text
Fast Code
+
Large Refactors
+
Hidden Assumptions
```

The objective is not merely to finish the application.

The objective is to build a system whose architecture, decisions, and behavior can be understood and defended by its engineering team.

# 37. Design Decisions Must Be Recorded Before Implementation

For any significant architectural, domain, ownership, boundary, or responsibility decision:

```text
Decision
  ↓
Record
  ↓
Test
  ↓
Implement
```

The implementation must not be the first permanent record of the decision.

If a decision is significant enough to affect future architecture or domain behavior, it belongs in the project documentation.

A conversation may be used to explore and discuss a decision, but the repository documentation is the durable record.

Therefore:

> **No significant undocumented design decision may silently become code.**
