# EGX Session Calendar Provenance & Operator Accountability — Design Gate

**Status:** APPROVED DESIGN — implementation partially complete; activation remains blocked  
**Reviewed:** 2026-11-09  
**Related:** PR #459, #460, #465, #466, #467

## 1. Owner decisions

The owner approved:
- **B — Immutable per-day evidence registry**
- **B — Individual named operator principals**

The approved decisions are implemented in part:
- PR #465 adds append-only, hash-verified evidence records keyed by calendar version, session date, and evidence kind. Corrections are new records with explicit supersession and reason.
- PR #466 adds individual operator grants, append-only grant/revoke/bootstrap events, a local first-operator bootstrap command, and durable-credential-aware permission resolution.
- PR #467 is merged and requires an active individual operator identity (user ID plus durable credential ID) for calendar administration; it rejects the synthetic shared operator identity.

## 2. Per-day evidence registry — implemented boundary

The current evidence record includes:
- Stable evidence ID and calendar version.
- Explicit session date and typed evidence kind.
- Source type/reference and a concise claim.
- Recorded-by user ID.
- Observed-at, recorded-at, and optional source-published-at timestamps.
- Optional superseded evidence ID and mandatory supersession reason.
- Canonical SHA-256 digest checked on read.

Persistence is append-only: database triggers reject UPDATE and DELETE. Conflicting unsuperseded claims of the same kind/day remain visible. A superseding record preserves the prior evidence history.

**Important remaining limitation:** the registry is not yet a publication gate. Calendar publication does not currently require a minimum evidence set for each date, nor does each calendar-day payload carry an explicit evidence-ID list. The registry proves what was recorded; it does not independently prove the source's authenticity or preserve the source artifact.

## 3. Evidence acceptance rules

- Primary EGX notices are preferred for trading sessions, auctions, shortened sessions, emergency closures, and reopening dates.
- FRA notices may support regulatory changes but must be linked to the corresponding EGX operational notice where applicable.
- Broker guides and third-party calendars are corroboration only; they cannot independently authorize a date or session time.
- Egyptian national public holidays are not equivalent to EGX closures.
- Conflicting sources remain unresolved until the underlying exchange notice or a documented operator decision is captured.
- A hash without a retained or independently retrievable artifact proves only that some bytes matched at publication time.
- Dates without sufficient evidence must not be used to infer a completed session or activate lifecycle evaluation.

## 4. Individual operator access — implemented boundary

The operator access model uses named application users with an explicit `OPERATOR` permission derived from an active grant and an active durable bearer credential.

- Grant/revoke operations require an individually authenticated operator and record actor user ID, actor credential ID, target user ID, reason, and timestamp.
- The event history is append-only.
- First-operator bootstrap is a one-time local administrative command for an active user with an active durable credential. The event is marked as a system bootstrap, not falsely attributed to a person.
- The last active operator cannot be revoked or disabled.
- Disabling/deleting an operator automatically revokes the grant; reactivation does not silently restore it.
- The legacy shared operator token remains for compatibility with unrelated legacy operator routes, but calendar administration rejects it.

## 5. Remaining tests and decisions

- Require the approved evidence policy at calendar publication/activation boundaries.
- Link calendar-day records to evidence IDs and validate that every required date has adequate supporting evidence.
- Decide whether source artifacts must be archived inside the application or whether stable external references plus hashes are sufficient.
- Define which day categories require primary evidence before publication versus before activation.
- Verify first-operator bootstrap and recovery against the actual deployment database and operational procedure.
- Add end-to-end tests against the production runtime composition, not only isolated repositories and test authenticators.

## 6. Current boundary

Calendar publication remains separate from activation. No calendar has been activated, and lifecycle monitoring remains disabled. No schedule, weekend, holiday, or session time is inferred. Provider completed-bar attestation and cursor-derived coverage validation remain independent activation blockers.

**Gate result:** the approved provenance and individual-operator foundations are implemented, but the evidence acceptance policy, evidence-to-calendar enforcement, and operational activation gates remain open.
