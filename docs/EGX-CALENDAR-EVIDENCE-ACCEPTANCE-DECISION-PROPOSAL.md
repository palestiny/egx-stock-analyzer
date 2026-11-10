# EGX Calendar Evidence Acceptance — Owner Decision Proposal

**Status:** OWNER-APPROVED POLICY — implementation in progress; activation remains blocked  
**Approved:** 2026-11-10  
**Scope:** Evidence source acceptance, source-artifact retention, and publication-versus-activation requirements for explicit EGX session-calendar day claims.

Owner approval recorded in the project conversation: D1 accepts A / A-R / B / C; D2 selects Hybrid retention (Option C); D3 selects strict evidence-gated publication; D4 approves the Section 3 evidence matrix. This document records the policy decision and does not authorize calendar activation, lifecycle monitoring, provider-finality assumptions, or M61 work.

This approved policy follows the merged immutable evidence registry (PR #465), individual operator accountability (PR #466), authenticated calendar API (PR #467), and atomic publication Unit of Work (PR #471).

## 1. Current verified boundary

The production publication path now:

- Persists one immutable calendar version, its evidence records, explicit day/evidence links, and validation inside one SQLite `BEGIN IMMEDIATE` transaction.
- Requires evidence coverage for every explicit date in the submitted calendar version.
- Enforces minimum evidence kinds implied by day status.
- Rejects unresolved same-kind/day conflicts and rolls back all publication writes on failure.
- Derives the publishing actor from the authenticated individual operator principal.

These controls establish structural completeness, linkage, immutability, and transaction atomicity. They do **not** establish that a source is authoritative, that a URL resolves to the same artifact later, or that the source artifact may legally be retained.

## 2. Proposed source classes

| Class | Source category | Permitted role | Not permitted |
|---|---|---|---|
| A — Primary operational | An EGX-published notice, circular, official calendar, or official market-status artifact that explicitly supports the relevant claim | Primary evidence for EGX dates, session status, hours, cancellations, emergency closures, reopening, and close confirmation when the artifact actually states that fact | Extending the artifact beyond its stated dates, instruments, market segment, or effective period |
| A-R — Primary regulatory | An FRA official notice or binding regulatory publication | Evidence for a regulatory change within FRA authority; link the corresponding EGX operational notice when the claim concerns an actual trading date, session, or market operation | Treating a regulatory publication or national holiday as proof that EGX did not trade on a particular date |
| B — Official corroboration | Official government or other public-sector material relevant to a closure context but not itself an EGX operating notice | Context and corroboration; may trigger a search for the EGX operational notice | Independently authorizing an EGX non-trading day or session hours |
| C — Secondary corroboration | Broker calendars, financial portals, data vendors, news reports, and third-party calendars | Detect discrepancies and corroborate a primary claim | Independently authorizing a calendar day, session time, cancellation, or completed-session status |

**Approved D1:** accept Class A for primary EGX operational claims; accept A-R only within FRA's regulatory scope and require the corresponding EGX operational evidence where the claim is operational; retain B/C as corroboration only. A source's reputation or a matching third-party consensus does not convert it into primary evidence.

A source record must identify the exact publisher, artifact/document reference, publication date when available, retrieval timestamp, effective date range, and the precise claim it supports. A URL alone is not an authority classification.

## 3. Evidence requirements by claim type

| Calendar assertion | Minimum proposed evidence |
|---|---|
| `NON_TRADING` | Class A artifact explicitly establishing that date as non-trading, or an official EGX calendar that explicitly includes the date. Do not infer from weekday or a national holiday. |
| `SCHEDULED` | Class A schedule/calendar artifact whose scope and effective period explicitly cover the date and relevant market/session. |
| `OPEN` | Class A schedule evidence plus an operational status observation appropriate to the meaning of OPEN. Do not treat a planned session as proof that trading actually opened. |
| `CANCELLED` | Class A cancellation/suspension notice explicitly covering the date or session. |
| `CLOSED` | Applicable Class A schedule evidence plus Class A close/market-status evidence that supports the completed-session claim and its close timestamp. A local clock or elapsed-time rule is not evidence of closure. |
| Exceptional or shortened hours | Class A notice specifying the affected date, market/session, and changed hours. Preserve the ordinary schedule separately where needed. |
| Emergency closure / reopening | Class A notice specifying the affected date and effective time. FRA material may explain the regulatory basis but does not replace EGX operational evidence. |

For every claim, the evidence must match the market segment and date. Evidence for EGX30 index values, for example, is not automatically evidence for the operating status of every EGX market segment.

**Approved D4:** use the table as the publication minimum for any calendar version intended to be operationally usable. If adequate evidence is missing, keep the candidate unpublished; do not fill gaps by inference. If the product later needs to store research-only or incomplete candidates, introduce an explicit non-operational draft state rather than weakening the meaning of publication.

## 4. Artifact retention options

### Option A — Archive source artifacts

Store the retrieved source bytes in restricted, durable object storage and record:
- SHA-256 digest;
- original source URL and publisher;
- retrieval timestamp and source publication timestamp, if available;
- content type, byte length, and artifact version;
- effective date range and claim linkage;
- retention/access policy and storage object identity.

**Benefit:** strongest future auditability when retention is permitted.  
**Cost/risk:** storage, access controls, retention operations, and possible copyright, licensing, or terms-of-use restrictions.

### Option B — External reference plus digest only

Store a stable official URL, SHA-256 digest, publisher metadata, and retrieval details without retaining the source bytes.

**Benefit:** lower storage and licensing exposure.  
**Cost/risk:** the URL may disappear or its content may change; the digest cannot reconstruct the original artifact and does not prove publisher authenticity.

### Option C — Hybrid retention (recommended)

Archive exact source bytes only when retention is permitted and operationally supportable. Otherwise store the stable official reference, digest, retrieval metadata, and an explicit `artifact_not_retained` reason. The evidence record must not imply that the artifact is archived or independently recoverable.

For a source whose bytes are not retained, require the URL to be official, stable, directly retrievable, and tied to a digest captured at observation time. If the reference later becomes unavailable or changes, mark the evidence as unverifiable for new activation decisions; preserve its historical record and never rewrite it silently.

**Important:** hashing provides integrity comparison, not source authenticity, legal permission, or proof that the publisher issued the content.

## 5. Publication versus activation

Two policies are possible:

1. **Strict publication gate:** only versions with the complete primary evidence required by Section 3 can be published.
2. **Research-candidate publication:** incomplete or secondary-only candidates may be stored, but they must have an explicit non-operational state and cannot be read as an approved calendar or activated.

**Approved D3:** retain the current simple semantic boundary: publication means the version has passed its evidence acceptance checks. Do not add a partially trusted published state. If incomplete research candidates are needed later, introduce a distinct draft/candidate concept and API explicitly.

Activation remains a separate gate. Even a fully evidenced published version cannot be activated until the owner approves bootstrap, cursor-derived coverage, durable recovery, deployment bootstrap/recovery, and the atomic activation transaction. Calendar evidence does not prove provider daily-bar finality.

## 6. Required enforcement and tests after approval

After the owner selects the policy:

1. Represent source class and artifact-retention status as typed, validated domain values; do not infer them from free-text source names.
2. Validate source class against claim type and effective date scope.
3. Validate that the source reference and artifact metadata are complete and immutable.
4. Require the minimum evidence set for each calendar-day status and reject secondary-only evidence where primary evidence is required.
5. Preserve corroborating sources separately; conflicts between unsuperseded claims remain visible and block publication until resolved by a new explicit superseding record with reason.
6. Test unsupported source classes, wrong date scope, wrong market scope, missing primary evidence, missing close confirmation, unavailable artifact, changed artifact digest, and in-batch supersession.
7. Keep activation endpoints, lifecycle monitoring, freshness enforcement, and M61 disabled.

## 7. Owner decision record

- [x] D1 — A / A-R / B / C source classes approved.
- [x] D2 — Option C hybrid artifact retention approved.
- [x] D3 — Strict evidence-gated publication approved.
- [x] D4 — Section 3 day-category evidence matrix approved.

The approval is limited to evidence acceptance and publication semantics. It does not approve activation, lifecycle monitoring, freshness enforcement, provider-finality assumptions, or M61.


## 8. Review checklist before implementation

The following checklist is the implementation acceptance checklist for the approved D1–D4 policy:

- [x] Confirm the source-class taxonomy and authority boundaries for each claim type.
- [x] Confirm hybrid retention and metadata requirements when source bytes cannot be retained.
- [x] Confirm strict evidence-gated publication; incomplete candidates remain unpublished.
- [x] Confirm primary-evidence requirements for every day status and special-hours claim.
- [ ] Define how an operator records a source that is unavailable, superseded, corrected, or legally non-retainable without weakening the audit trail.
- [ ] Approve the typed domain representation and migration strategy before changing persistence.
- [ ] Add domain tests first, then repository/UoW tests, then authenticated API tests through the production runtime composition.
- [ ] Prove rejected evidence leaves no calendar version, evidence rows, links, active pointer, or success audit event behind.
- [x] Record owner-approved policy in this decision record before implementation.
