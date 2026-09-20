# Lessons Learned

## 1. Purpose

This document records important engineering and architectural lessons discovered while building the EGX Stock Analyzer.

The purpose is not to document what the system does, but **how our understanding of the system evolved**.

A lesson should be recorded when an implementation, test, discussion, or design decision changes the way we think about the system.

---

## 2. Lesson: Not Every Validation Is a Domain Invariant

### Context

While implementing `MarketData`, we considered adding validations such as:

```text
High >= Open
High >= Close
Low <= Open
Low <= Close
```

These relationships look like obvious rules because they are normally true for OHLC market data.

However, `MarketData` represents an observation received from an external source.

The system does not necessarily know whether an unusual observation is:

- incorrect data,
- corrupted data,
- delayed data,
- provider-specific behavior,
- a mapping problem,
- or a legitimate exceptional observation.

### What We Learned

A condition being **normally true** does not automatically make it a **domain invariant**.

There is an important difference between:

```text
"This data looks suspicious."
```

and:

```text
"This object is forbidden from existing."
```

The first is a **data-quality concern**.

The second is a **domain invariant**.

### Architectural Consequence

We should avoid automatically rejecting external observations merely because they violate an expected relationship.

Instead, the architecture should eventually allow us to distinguish between:

```text
Raw Observation
        ↓
Data Quality Assessment
        ↓
VALID / SUSPECT / INVALID
        ↓
Analysis Decision
```

The observation may still be preserved even when its quality is questionable.

### General Rule

> **Do not confuse data-quality rules with domain invariants.**

Before adding a validation, ask:

1. Who owns this rule?
2. Is violating it impossible in the business domain?
3. Or does it merely indicate suspicious external data?
4. Should the information be rejected, preserved, flagged, or quarantined?
5. What would happen to historical analysis if we silently discarded it?

---

## 3. Lesson: External Data Is an Observation, Not Automatically the Truth

### Context

Market data enters our system from outside.

The provider may supply:

- prices,
- volume,
- timestamps,
- company information,
- financial values,
- corporate actions,
- or other market observations.

### What We Learned

The system should not blindly assume:

```text
Provider → Truth
```

Instead:

```text
External World
      ↓
Data Provider
      ↓
Observation
      ↓
Quality Assessment
      ↓
Analysis
```

The analyzer's responsibility is not to "correct the external world."

Its responsibility is to determine:

> **Can this observation safely be used for this particular purpose?**

### Architectural Consequence

Data acquisition and data quality should remain separate concerns.

A provider adapter should primarily acquire data.

A data-quality component should assess the data.

Analysis components should decide whether and how data of a particular quality should be used.

### General Rule

> **Preserve information before deciding what it means.**

---

## 4. Lesson: A Test Can Expose a Design Problem, Not Just a Code Bug

### Context

We initially wrote a test around an expected OHLC relationship.

The test passed after implementing the validation.

However, the discussion around the test revealed that the real question was not:

> "Does the code reject invalid data?"

The real question was:

> "Should this object reject this data at all?"

### What We Learned

A passing test does not necessarily mean the design is correct.

A test can successfully prove behavior that we later discover should never have existed.

Therefore:

```text
Test passes
    ≠
Design is correct
```

### Architectural Consequence

Before expanding test coverage, we should verify that the behavior being tested belongs to the correct boundary.

### General Rule

> **Tests validate decisions; they do not replace design decisions.**

---

## 5. Lesson: Ownership Must Be Decided Before Implementation

When a rule appears, the first question should not be:

> "Where do we write the `if` statement?"

The first question should be:

> **"Who owns this rule?"**

For example:

```text
Stock
MarketData
DataQuality
TechnicalAnalysis
Scoring
SignalGeneration
```

may each have very different responsibilities.

Putting a rule in the wrong component can make the code work today while creating architectural problems later.

### General Rule

> **A rule without a clear owner should not be implemented yet.**

---

## 6. Lesson: Preserve Information When Possible

In an analysis system, deleting information can be more damaging than keeping questionable information.

For example, if a market observation looks unusual, silently deleting it can make historical data appear cleaner than reality.

That can affect:

- backtesting,
- anomaly detection,
- provider comparison,
- debugging,
- historical reconstruction,
- and future analysis strategies.

### General Rule

> **Prefer preserving raw information and explicitly describing its quality over silently destroying it.**

---

## 7. Lesson: The Database Should Not Define the Domain

The future system will almost certainly use persistent storage.

However, the domain model should not be designed around:

- database tables,
- ORM limitations,
- SQL schemas,
- API payloads,
- or UI requirements.

The domain should first express the business meaning.

Persistence should adapt to that model.

Conceptually:

```text
Domain
  ↑
Application
  ↑
Infrastructure
  ↑
Database / Providers / External Systems
```

### General Rule

> **The domain model represents meaning; infrastructure represents technology.**

---

## 8. Lesson: AI Should Not Become the Architecture

The project may eventually use AI for:

- interpreting news,
- extracting information,
- classifying events,
- summarizing reports,
- detecting patterns,
- or assisting with research.

However, AI should remain a replaceable capability.

The core system must remain functional without depending on one specific AI provider or model.

### General Rule

> **AI is a tool used by the system, not the foundation of the system.**

---

## 9. Lesson: Architecture Should Evolve From Understanding

We are intentionally not starting with:

```text
API
Database
Dashboard
AI
Microservices
Cloud
```

Instead, we are starting with:

```text
Meaning
   ↓
Domain
   ↓
Responsibilities
   ↓
Boundaries
   ↓
Application Flow
   ↓
Infrastructure
```

This prevents technology decisions from defining business concepts prematurely.

### General Rule

> **Understand the problem before optimizing the implementation.**

---

## 10. Lesson: Small Code Does Not Mean Small Design

The first `MarketData` implementation was very small.

That does not mean the concept itself is simple.

A small class can represent an important architectural boundary.

We should therefore distinguish between:

```text
Implementation complexity
```

and:

```text
Conceptual complexity
```

### General Rule

> **Keep implementations simple without assuming the underlying concept is simple.**

---

## 11. Lesson: Uncertainty Is a Valid Engineering State

Some decisions are intentionally unresolved.

For example:

- Is `MarketData` an Entity?
- Is it a Value Object?
- Is it an Observation?
- Should observations have identity?
- Where should data-quality status live?
- How should conflicting providers be handled?

We should not force premature answers merely to make the code move forward.

### General Rule

> **An explicit open decision is better than an accidental architecture.**

Open questions belong in:

`DECISION_LOG.md`

rather than being silently answered by implementation.

---

## 12. Lesson: The Project Is Teaching Us the Architecture

The architecture is not something we should invent completely before writing any code.

Instead, the process is:

```text
Understand
   ↓
Design
   ↓
Implement
   ↓
Test
   ↓
Discover
   ↓
Question
   ↓
Learn
   ↓
Update Architecture
```

The important part is that discoveries are captured.

Otherwise the same architectural mistakes can return later.

---

## 13. Current Most Important Lesson

The most important lesson discovered so far is:

> **Before implementing a rule, understand whether it describes the business domain, the quality of external data, or the behavior of an analysis strategy.**

These are different responsibilities and should not automatically live in the same object.

---

## 14. How Future Lessons Should Be Recorded

For every significant lesson, prefer this structure:

```text
Context
What happened?

Initial assumption
What did we originally believe?

Discovery
What changed our understanding?

Lesson
What did we learn?

Architectural consequence
What changes because of this?

General rule
What principle should we remember?
```

This document should evolve throughout the project.

It should record changes in **engineering thinking**, not every small coding detail.
