# EGX Session Calendar Provenance & Operator Accountability — Design Gate

**Status:** PROPOSED — no schema or authorization change approved  
**Reviewed:** 2026-11-09  
**Related:** DEC-139, PR #459, PR #460, PR #462

## 1. Why this gate exists

The calendar model requires explicit dates and session states, and the persistence layer stores immutable versions. The current operator API stores one calendar-level `source_reference` and derives `published_by` from the authenticated principal.

Two gaps remain before the calendar can be treated as operationally auditable:

1. A single version-level source reference does not prove why each exceptional date or session-time override was entered.
2. The current legacy operator token resolves to the shared subject `operator`. It authenticates use of the shared credential but does not identify the human who published a version.

The API deliberately does not expose activation. These gaps should be closed before activation policy is implemented.

## 2. Per-day provenance options

| Option | Shape | Advantages | Limitations |
|---|---|---|---|
| A. Per-day text reference | Add `evidence_reference` to each calendar day. | Small change; easy to publish. | Duplicates repeated notices; no typed source, document hash, retrieval time, or reusable evidence record. |
| B. Immutable evidence registry | Store evidence records once; calendar days reference one or more evidence IDs. | Reusable, structured, auditable, supports multiple notices and independent corroboration. | More tables, validation, and API work. |
| C. External evidence manifest | Publish a signed/versioned manifest alongside the calendar JSON. | Keeps calendar payload simple and supports offline review. | Requires artifact storage, signature verification, and atomic linkage to the calendar version. |

### Recommendation — B, with optional archived artifact support

Introduce an immutable `CalendarSourceEvidence` record with at least:

- `evidence_id` (stable identifier)
- `source_kind` (`EGX_OFFICIAL_NOTICE`, `REGULATOR_NOTICE`, `OFFICIAL_EXCHANGE_CALENDAR`, `BROKER_REFERENCE`, `THIRD_PARTY_DATASET`, `OPERATOR_ATTESTATION`)
- `title` / concise description
- `source_reference` (URL or document/reference identifier)
- `content_sha256` when a retrievable document or response snapshot is available
- `published_at` (nullable when not stated)
- `retrieved_at` (required, timezone-aware)
- `recorded_by` (authenticated operator principal; never caller-supplied)
- `verification_status` (`PRIMARY_VERIFIED`, `SECONDARY_ONLY`, `UNVERIFIED`)

Each calendar day should reference the evidence that supports its status and session times. A normal-session baseline may reference one annual/seasonal EGX notice across many dates; an exceptional closure or shortened session should reference its specific notice. A calendar version must not upgrade secondary evidence to primary merely by being published.

A hash without a retained or independently retrievable artifact proves only that some bytes matched at publication time. If evidence files are archived, the storage location and retention/access policy must be defined separately; do not pretend a hash alone preserves the source document.

## 3. Evidence acceptance rules

- Primary EGX notices are preferred for trading sessions, auctions, shortened sessions, emergency closures, and reopening dates.
- FRA notices may support regulatory changes but must be linked to the corresponding EGX operational notice where applicable.
- Broker guides and third-party calendars are corroboration only; they cannot independently authorize a date or session time.
- Egyptian national public holidays are not equivalent to EGX closures.
- Conflicting sources remain unresolved until the underlying exchange notice or a documented operator decision is captured.
- A date without sufficient evidence may be stored as `UNVERIFIED` for research, but must not be used to infer a completed session or activate lifecycle evaluation.

## 4. Operator identity options

| Option | Meaning | Trade-off |
|---|---|---|
| A. Keep shared legacy token | Continue recording `operator`. | Minimal change, but no individual human accountability. |
| B. Named operator principals | Add an explicit operator permission/role to named user identities and issue individual credentials. | Best auditability; requires role administration, credential lifecycle, and authorization tests. |
| C. External signed attestation | Keep the service credential but require a separately signed operator identity assertion. | Can integrate an external identity provider, but adds signing-key and verification lifecycle. |

### Recommendation — B

Use named operator accounts with an explicit `OPERATOR` permission. The authenticated principal must supply the actor identity for publication and activation events. The API must continue to reject body-supplied actor fields. The shared legacy token may remain available for compatibility, but should not be accepted for calendar publication/activation once named operator credentials are available, unless the owner explicitly accepts its reduced audit quality.

## 5. Required tests before implementation is accepted

- A calendar day cannot reference a missing evidence ID.
- A version cannot be published if a required date has no supporting evidence under the approved policy.
- Evidence records and links are immutable after publication; corrections create new evidence/version references.
- A third-party or secondary-only source cannot satisfy a primary-source requirement.
- Evidence timestamps must be timezone-aware and distinguish publication from retrieval.
- Evidence hash mismatch or missing archived artifact fails closed when artifact retention is enabled.
- Two named operators produce distinct audit actors; revocation or disabled status blocks publication.
- Non-operators and the legacy shared token receive the explicitly approved response.
- Re-publication/correction preserves the prior calendar and evidence history.

## 6. Decisions required from the owner

1. Approve the immutable evidence registry (B), or select another provenance option.
2. Approve named operator principals (B), or explicitly accept that shared-token audit entries cannot identify an individual.
3. Decide whether source artifacts must be archived inside the application or whether stable external references plus hashes are sufficient.
4. Define which day categories require primary evidence before publication versus before activation.

## 7. Current boundary

PR #462 adds authenticated publication and read APIs, but its current calendar-level reference is not a substitute for per-day provenance. The shared legacy operator subject is not an individual identity. No calendar has been published or activated, and lifecycle monitoring remains disabled.

**Gate result: no per-day provenance schema, named-operator authorization change, or activation endpoint should be implemented until the owner approves the options above.**
