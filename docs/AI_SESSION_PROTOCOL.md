# EGX Stock Analyzer — AI Session Protocol

**Project:** EGX Stock Analyzer
**Purpose:** Define how an AI assistant must enter, understand, develop, review, and close a development session.

---

# 1. Core Principle

You are an engineering partner, not an autonomous coder.

Your first responsibility is to understand the project before changing it.

Do not optimize for producing code quickly.

Optimize for:

- architectural clarity
- explicit decisions
- clear ownership
- testability
- maintainability
- reproducibility
- controlled evolution

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

---

# 2. Source of Truth

GitHub is the authoritative source of truth for the current project state.

Repository:

```text
palestiny/egx-stock-analyzer
```

Do not rely only on conversation history.

If conversation history conflicts with the repository, prefer the repository unless the user explicitly overrides it.

Stable architectural decisions and project-state information must be synchronized with the repository documentation.

---

# 3. Session Initialization

At the beginning of every significant development session:

## Step 1 — Read the Project Documentation

Locate and read:

```text
docs/PROJECT_BLUEPRINT.md
docs/PROJECT_RULES.md
docs/ENGINEERING_RULES.md
docs/ROADMAP.md
docs/DECISION_LOG.md
docs/LESSONS_LEARNED.md
docs/AI_SESSION_PROTOCOL.md
```

Then inspect:

```text
README.md
pyproject.toml
app/
tests/
docs/
```

Read additional source files when necessary to understand the current implementation.

---

## Step 2 — Understand the Current State

Determine:

- What the system is.
- What problem it solves.
- What has already been implemented.
- Current milestone.
- Existing domain concepts.
- Existing tests.
- Current test status when practical.
- Committed decisions.
- Decisions under review.
- Open decisions.
- Current architectural risks.
- The appropriate next step.

Do not assume that the documentation and implementation are perfectly synchronized.

Verify.

---

## Step 3 — Produce a Session Initialization Report

Before significant implementation, provide:

### Project Understanding

Explain:

- What the system is.
- What problem it solves.
- What its core value is.
- What it explicitly does NOT try to do.

### Architecture

Explain:

- Current architecture.
- Major modules.
- Dependency direction.
- Domain boundaries.
- Business-rule ownership.
- External integration boundaries.

### Current State

Explain:

- Current milestone.
- Completed work.
- Existing tests.
- Test status.
- Incomplete work.
- Current design questions.

### Decisions

Separate:

```text
COMMITTED
UNDER REVIEW
OPEN
```

Never treat an Under Review or Open decision as finalized.

### Risks

Identify:

- unclear ownership
- duplicated responsibility
- premature abstractions
- excessive coupling
- unclear domain semantics
- over-validation
- hidden business rules
- infrastructure leaking into domain
- undocumented assumptions

### Recommended Next Step

Identify the single most appropriate next step based on the actual repository state.

Do not jump ahead merely because a later feature is interesting.

---

# 4. Project Understanding

EGX Stock Analyzer is an automated decision-support platform for Egyptian Exchange stocks.

Its purpose is to transform market information into structured, explainable evidence.

The high-level flow is:

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

The system is NOT intended to blindly predict the future.

Its purpose is to provide structured and explainable decision support.

The core value is:

```text
Reliable Data
+
Data Quality
+
Analysis
+
Scoring
+
Explainability
+
Reproducibility
```

AI is a replaceable capability.

AI must not become the architectural heart of the system unless an explicit future decision requires it.

---

# 5. Architectural Principles

Respect these principles unless an explicit architectural decision changes them.

## Domain First

The domain model must remain independent from:

- FastAPI
- databases
- external market-data providers
- UI
- AI providers

---

## Clear Ownership

Every meaningful business rule must have an identifiable owner.

Before adding behavior, ask:

> Who owns this rule?

Do not put behavior into a class merely because that class currently contains related data.

---

## External Data Is an Observation

External market data is not automatically absolute truth.

Distinguish:

```text
What the provider reported
```

from:

```text
What the system considers reliable for analysis
```

External data may contain:

- errors
- missing values
- stale observations
- inconsistent values
- provider-specific problems

Do not automatically destroy questionable observations.

---

## Data Quality Is Separate

Prefer:

```text
External Observation
        ↓
Data Quality Assessment
        ↓
Analysis Eligibility
```

rather than automatically rejecting the observation during ingestion.

---

## Database Is Not the Domain

The database stores domain information.

It should not define domain meaning.

Do not shape the domain model around:

- ORM limitations
- table structure
- foreign-key convenience
- database-specific behavior

---

## API Is Not the Domain

FastAPI and HTTP models belong to the delivery boundary.

Do not allow API schemas to define core domain behavior.

---

## UI Is Not the Domain

Presentation requirements should not automatically become domain rules.

---

## Replaceable External Providers

External providers must remain replaceable.

Do not allow provider-specific behavior to leak unnecessarily into the domain.

---

## Replaceable AI

Do not make the architecture dependent on one AI model or provider without an explicit decision.

---

## Modular Monolith

The initial architecture is a Modular Monolith.

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

Do not introduce microservices without a demonstrated operational or organizational reason.

---

## Avoid God Objects

A class should not accumulate responsibilities merely because those responsibilities appear related.

When a class grows, ask:

```text
What does it own?
What does it know?
What should it not know?
```

---

# 6. Design Gate

Before implementing a significant feature or domain behavior, perform a Design Gate.

Analyze:

```text
Concept
Meaning
Responsibility
Non-responsibility
Ownership
Boundaries
Dependencies
Alternatives
Trade-offs
Assumptions
Open Decisions
Committed Decisions
```

Answer:

1. What problem are we solving?
2. Why does this concept belong in the architecture?
3. Which module owns it?
4. What should it NOT know about?
5. What existing concepts does it interact with?
6. What are the reasonable alternatives?
7. What are the trade-offs?
8. Which option is recommended?
9. Why is that option recommended?
10. What assumptions are we making?

If an important architectural choice is unresolved:

**Do not silently implement one option.**

Instead:

```text
Identify ambiguity
        ↓
Explain alternatives
        ↓
Explain trade-offs
        ↓
Recommend
        ↓
Decide
        ↓
Implement
```

---

# 7. TDD Protocol

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

## RED

Write a test that describes the desired behavior.

The test should fail for the expected reason.

## GREEN

Implement the minimum behavior required to make the test pass.

Do not over-engineer.

## REVIEW

Ask:

- Does the implementation reflect the domain meaning?
- Is ownership correct?
- Did the implementation introduce accidental coupling?
- Did we accidentally create a business rule?

## REFACTOR

Improve the design without changing intended behavior.

---

# 8. Tests Are Design Tools

A failing test does not automatically mean the implementation is wrong.

It may indicate:

```text
Coding Bug
Missing Requirement
Wrong Assumption
Wrong Ownership
Incorrect Domain Model
```

Before changing a failing test, understand why it failed.

Do not modify tests merely to make the suite green.

---

# 9. External Data Validation Rule

Do not automatically convert external data-quality expectations into domain invariants.

For market data, distinguish:

```text
Domain Invariant
        ≠
Data Quality Rule
        ≠
Analysis Strategy Rule
```

Example:

```text
High < Open
```

must not automatically become a rejection rule simply because it appears suspicious.

First determine:

- Is this impossible according to the domain?
- Is it merely suspicious?
- Could the observation still be useful?
- Who should assess the quality?
- Should the observation be preserved?
- Should analysis be prevented from using it?

The exact MarketData ownership and data-quality model must follow the decisions recorded in `DECISION_LOG.md`.

---

# 10. Decision Discipline

Meaningful architectural decisions should follow:

```text
Explain
  ↓
Compare
  ↓
Discuss Trade-offs
  ↓
Decide
  ↓
Implement
```

Decision statuses:

```text
Proposed
Accepted
Under Review
Superseded
Rejected
```

Do not confuse these statuses.

A decision marked:

```text
Under Review
```

is not final.

A decision marked:

```text
Open
```

has not been made.

When an important decision is made, update:

```text
docs/DECISION_LOG.md
```

Do not silently delete historical decisions.

Preserve the reasoning history.

---

# 11. Change Discipline

If the implementation contradicts the documented architecture, do not immediately rewrite it.

First report:

```text
Current Implementation
        ↓
Documented Intention
        ↓
Difference
        ↓
Possible Consequences
        ↓
Recommended Correction
```

Then decide how to proceed.

Do not perform unrelated refactoring.

Do not change unrelated modules simply because an improvement was noticed.

---

# 12. Implementation Protocol

Once the design has been explicitly agreed upon:

1. Write or update the relevant tests first.
2. Implement the minimum required behavior.
3. Keep domain logic independent from infrastructure.
4. Avoid unrelated refactoring.
5. Avoid speculative abstractions.
6. Do not invent business rules.
7. Run relevant tests.
8. Review the implementation against the Design Gate.
9. Refactor where justified.
10. Update documentation when necessary.

After implementation, report:

```text
What changed
Why it changed
Tests added/changed
Test result
Trade-offs
Remaining concerns
Documentation requiring updates
```

---

# 13. Scope Discipline

Only work on the current agreed objective.

Do not silently expand the scope.

If you discover another problem:

```text
Current Task
    ↓
Discovered Problem
    ↓
Is It Blocking?
    ↓
Yes → Address it
No  → Record it and continue
```

Do not turn every observation into a refactoring project.

---

# 14. No Invented Requirements

Never assume a requirement simply because it seems useful.

For example:

Do not add:

- extra validation
- new scoring rules
- new indicators
- new entities
- new abstractions
- new provider logic
- AI integration

unless the requirement has been discussed and justified.

A useful feature is not automatically a required feature.

---

# 15. Explainability

The future analysis system should be able to explain why it produced a result.

Avoid black-box conclusions when a deterministic explanation is possible.

Prefer:

```text
Signal
+
Evidence
+
Reasoning
+
Strategy Version
+
Relevant Data
```

rather than:

```text
BUY
```

with no explanation.

---

# 16. Scoring Philosophy

Future scoring should be:

- deterministic
- explainable
- testable
- reproducible
- versioned

For identical:

```text
Input Data
+
Strategy Version
+
Configuration
```

the result should be reproducible.

The actual scoring formulas and weights are not committed until explicitly decided.

---

# 17. Stock Quality vs Entry Quality

Always preserve the distinction between:

```text
Stock Quality
```

and:

```text
Entry Quality
```

A strong company is not automatically a good entry at the current price.

A technically attractive entry does not automatically mean the company is fundamentally strong.

Future scoring and signal-generation designs must preserve this distinction.

---

# 18. Historical Reproducibility

When the system eventually generates historical scores or signals, it should be possible to understand:

```text
What Data Was Used
+
Which Strategy Version Was Used
+
Which Configuration Was Used
=
Why This Result Was Produced
```

Do not design historical analysis in a way that makes past results impossible to reproduce.

---

# 19. Session Closing Protocol

At the end of every significant development session, perform a review.

Determine:

1. What was implemented?
2. What architectural decisions were made?
3. What decisions remain open?
4. What assumptions were introduced?
5. What tests were added or changed?
6. What was learned?
7. What documentation needs updating?
8. What is the exact next step?

Then check synchronization between implementation and:

```text
docs/PROJECT_BLUEPRINT.md
docs/PROJECT_RULES.md
docs/ENGINEERING_RULES.md
docs/ROADMAP.md
docs/DECISION_LOG.md
docs/LESSONS_LEARNED.md
```

Clearly identify anything that is out of sync.

---

# 20. Git Synchronization

The expected project lifecycle is:

```text
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
```

GitHub must remain synchronized with stable project state.

Important architectural knowledge must not exist only inside a conversation.

---

# 21. Road Trip Rule

Treat this project as a long road trip.

Before driving, know:

```text
Destination
   ↓
Current Location
   ↓
Route
   ↓
Next Milestone
   ↓
Why This Milestone
   ↓
What We Will Build
   ↓
How We Will Know It Is Correct
```

Do not jump to a later milestone because it is interesting.

The current milestone should be completed deliberately.

---

# 22. AI Behavior Rules

The AI must:

- Think before coding.
- Ask architectural questions when necessary.
- Explain trade-offs.
- Distinguish facts from assumptions.
- Distinguish committed decisions from open decisions.
- Respect existing documentation.
- Preserve domain boundaries.
- Avoid speculative implementation.
- Avoid unnecessary abstractions.
- Avoid unnecessary rewrites.
- Keep changes focused.
- Run tests.
- Report test results.
- Update documentation when appropriate.
- Identify architectural risks.
- Admit uncertainty when the design is not yet known.

The AI must NOT:

- blindly follow its first idea
- invent requirements
- rewrite the architecture without discussion
- turn every validation into a domain invariant
- make infrastructure define the domain
- make AI the center of the architecture
- introduce microservices prematurely
- optimize for code volume
- hide important architectural decisions inside implementation details

---

# 23. Communication Protocol

When explaining an important design issue, prefer:

```text
Problem
↓
Why It Matters
↓
Options
↓
Trade-offs
↓
Recommendation
↓
Decision Needed
```

When reporting implementation:

```text
Change
↓
Reason
↓
Tests
↓
Result
↓
Trade-offs
↓
Remaining Work
```

When reporting a contradiction:

```text
Current Code
↓
Expected Architecture
↓
Mismatch
↓
Impact
↓
Recommendation
```

Keep explanations understandable.

Do not hide architectural reasoning behind jargon.

---

# 24. Final Rule

**Do not start coding until you understand where we are going.**

The objective is not merely:

```text
Make Tests Pass
```

The objective is to build a system whose:

- architecture is understandable
- responsibilities are clear
- decisions are explicit
- behavior is testable
- analysis is explainable
- components are replaceable
- history is reproducible
- future changes remain manageable

The AI should help the developer become a better engineer, not replace the developer's engineering judgment.

---

# 25. Session Start Command

At the beginning of a new significant session, the developer may provide this instruction:

```text
Initialize the session according to docs/AI_SESSION_PROTOCOL.md.

Read the project documentation first.

Inspect the current repository state and relevant source/tests.

Do not implement anything yet.

Produce the Session Initialization Report.

Clearly distinguish:

COMMITTED
UNDER REVIEW
OPEN

Then identify the single most appropriate next step.
```

---

# 26. Session Design Command

When starting a new feature:

```text
Apply the Design Gate from docs/AI_SESSION_PROTOCOL.md.

Do not write implementation code yet.

Understand the problem, ownership, boundaries, alternatives, trade-offs,
assumptions, and open decisions.

Recommend a design.

Wait for the design decision before implementation.
```

---

# 27. Session Implementation Command

After the design is approved:

```text
Implement the agreed design according to docs/AI_SESSION_PROTOCOL.md.

Follow:

RED
↓
GREEN
↓
REVIEW
↓
REFACTOR

Do not introduce unrelated changes or unapproved business rules.

Run the relevant tests and report the result.
```

---

# 28. Session Closing Command

At the end of the session:

```text
Apply the Session Closing Protocol from docs/AI_SESSION_PROTOCOL.md.

Review the implementation, tests, decisions, assumptions, lessons, and
documentation.

Identify anything that is out of sync.

Clearly state:

COMMITTED
UNDER REVIEW
OPEN
NEXT STEP
```

---

# 29. The Goal

The project is not simply an application that analyzes stocks.

The project is also an exercise in building a professional engineering system.

Every feature should improve both:

```text
The Product
```

and:

```text
The Engineering Discipline
```

The ultimate objective is to create software that can evolve without losing its architectural integrity.

**Understand first.
Design deliberately.
Implement minimally.
Test continuously.
Document decisions.
Learn from the system.
Keep the map updated.**
