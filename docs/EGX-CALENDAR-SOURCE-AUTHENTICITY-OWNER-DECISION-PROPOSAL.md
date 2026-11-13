# EGX Calendar Source Authenticity — Owner Decision Proposal

**Status:** OWNER-APPROVED — Option B, separate reviewer, and external re-fetch approved  
**Date:** 2026-11-13  
**Scope:** Independent verification of the publisher and exact artifact supporting calendar evidence. This proposal does not approve a publisher, domain, calendar, provider, activation, or production operation.

## 1. Why this gate exists

The current calendar evidence pipeline verifies several different properties:

- The evidence record is append-only and its canonical record digest is checked on read.
- For `ARCHIVED` evidence, the artifact store verifies that the bytes read back match the SHA-256 computed at upload and again before publication.
- The activation validator checks operator-declared metadata such as source class, publisher label, market scope, effective dates, and evidence kind.

These controls do **not** independently prove that the artifact was issued by the declared publisher. A user-entered `source_publisher="EGX"`, an HTTPS URL, and a matching SHA-256 digest are not by themselves publisher authentication. The current validator can therefore accept structurally consistent but falsely attributed metadata if the ingestion boundary is compromised or the operator makes an incorrect attribution.

The source review identifies the EGX public portal (`https://beta.egx.com.eg/en`) as a preferred place to locate individual notices, but does not establish a complete machine-readable calendar, a verified official-origin allowlist, or a cryptographic signing mechanism. No publisher/domain is approved by this proposal.

## 2. Separate the verification claims

Do not collapse these into one boolean:

1. **Artifact integrity:** bytes have not changed relative to the captured digest.
2. **Publisher-origin authentication:** the retrieval endpoint was authenticated against an owner-approved trust anchor at capture time.
3. **Artifact-to-publisher binding:** the artifact itself is verifiably issued by that publisher (for example, a valid publisher signature), if such a mechanism exists.
4. **Claim review:** the artifact actually supports the exact date, market scope, evidence kind, and calendar assertion.
5. **Retention permission:** the bytes may lawfully and operationally be retained.

A successful result in one category must never imply success in another. A SHA-256 digest addresses item 1 only.

## 3. Verification approaches

### Option A — Publisher-signed artifacts

Accept an artifact as independently authenticated only when its signature verifies against a publisher public key obtained through an independently trusted channel, with key identity, validity period, revocation/rotation, signature algorithm, and signed-byte format defined.

**Advantages:** strongest artifact-to-publisher binding; independently reproducible verification.  
**Limitations:** no evidence currently establishes that EGX publishes calendar notices with verifiable digital signatures or provides a public key/key lifecycle. Do not invent a key or infer signatures from HTTPS.

### Option B — Owner-approved origin trust registry plus independent human review

Maintain an append-only, owner-controlled registry of exact publisher origins and their trust basis. At capture time, a verifier must:
- retrieve from an exact approved HTTPS origin;
- reject unapproved hosts, downgrade, invalid TLS, and cross-origin redirects;
- capture the final URL, retrieval time, response metadata, and exact bytes where retention is permitted;
- verify the publisher identity using the approved origin policy;
- inspect the artifact itself and attest that it supports the precise claim/date/market scope;
- be a named individual different from the evidence uploader for operationally usable evidence;
- preserve verifier identity, credential identity, verification method/version, decision, reason, and artifact digest in immutable audit data.

For `EXTERNAL_ONLY`, require the approved reference to remain directly retrievable and re-check the bytes/digest when a new activation decision is made. If retrieval fails or the bytes differ, treat it as unverifiable and fail closed. Do not represent an old digest as proof of current availability.

**Advantages:** can be implemented without assuming a publisher signature or contacting a provider; preserves an explicit human accountability boundary.  
**Limitations:** relies on the owner-approved origin trust basis and reviewer diligence; it is not equivalent to a publisher digital signature. A trusted origin proves the authenticated endpoint at retrieval time, not that every document hosted there is an official operational notice.

### Option C — Independent second-source corroboration only

Require a second source or reviewer to corroborate each claim, without authenticating the primary artifact origin.

**Advantages:** can expose discrepancies and transcription errors.  
**Limitations:** corroboration does not authenticate the primary source. Two secondary sources may repeat the same incorrect information. Under the already approved A/A-R/B/C policy, Class B/C cannot replace Class A primary evidence. This option is insufficient as the sole authenticity control.

## 4. Recommended direction

Adopt **Option B as the minimum implementable control**, while supporting Option A as a stronger future verification method if EGX actually supplies a verifiable signature mechanism.

Important constraints:
- The origin registry must be explicitly owner-approved. Engineering must not silently add `egx.com.eg`, subdomains, broker domains, or any other host to a trusted list.
- Exact-origin matching should be the default; no wildcard subdomains.
- Cross-origin redirects should fail closed unless the destination origin is separately approved and explicitly recorded.
- The verifier must not accept publisher identity solely from operator-entered metadata.
- The uploader and verifier must be distinct named individuals for evidence used in an activation decision.
- Verification must be claim-specific and versioned. A successful verification of a schedule notice cannot automatically verify a closure or close-confirmation claim.
- Archived bytes must still pass the existing byte-integrity check. External-only artifacts remain weaker and must be re-retrievable at decision time.
- Retention permission remains a separate gate; source authenticity does not grant copyright or reuse rights.
- No automatic scraping, calendar ingestion, activation endpoint, worker, monitoring, or production state change is part of this proposal.

## 5. Owner-approved decisions (2026-11-13)

1. **Approach:** approve Option A, Option B, or Option C (not recommended as a standalone control).
2. **Origin trust:** approve a process in which exact origins are added only after an explicit owner decision, with the trust basis recorded per origin. No origins are pre-approved here.
3. **Reviewer separation:** require a second named individual, distinct from the uploader, to verify evidence used for activation.
4. **External-only evidence:** require live re-retrieval and digest equality at each activation decision; otherwise block activation.
5. **Failure policy:** any missing trust anchor, unapproved redirect, TLS/authentication failure, unavailable artifact, digest mismatch, reviewer mismatch, or unsupported verification method blocks the evidence and therefore activation.

## 6. Acceptance tests required before implementation is considered complete

- An unapproved origin is rejected even when metadata says publisher EGX.
- A lookalike hostname and wildcard subdomain are rejected.
- HTTP downgrade, invalid TLS, and unapproved cross-origin redirect are rejected.
- A changed artifact fails digest verification.
- A valid artifact from an approved origin still fails if the content does not support the exact claim/date/market scope.
- A Class B/C artifact cannot satisfy a Class A requirement.
- An uploader cannot self-verify activation-grade evidence when reviewer separation is approved.
- A revoked/expired trust-registry entry cannot verify new evidence; historical verification records remain immutable.
- `EXTERNAL_ONLY` evidence blocks when the reference is unavailable or its bytes differ at activation decision time.
- Verification outcomes are append-only and attributable; corrections create new records and never rewrite old outcomes.
- Existing byte-integrity tests remain intact and are not relabeled as authenticity tests.

## 7. Current operational boundary

Until the approved design is fully implemented and its remaining acceptance tests pass:
- Existing evidence metadata remains operator-asserted, not independently authenticated.
- Calendar activation remains blocked.
- No calendar is activated; no lifecycle worker or monitoring is enabled.
- No EGID or other provider outreach is authorized or performed.
- No provider is selected or approved.
