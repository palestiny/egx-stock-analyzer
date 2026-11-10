# Calendar Artifact Byte Integrity — Implementation Slice

**Status:** byte-storage port and filesystem adapter implemented on a feature branch; API/publication integration is not yet merged.

## Scope implemented

- `CalendarArtifactService` computes SHA-256 from the exact input bytes.
- The service writes through a storage port, reads the bytes back, recomputes SHA-256, and returns a receipt only when the digests match.
- `FileSystemCalendarArtifactStore` uses content-addressed paths (`sha256:<digest>`), rejects malformed references and symbolic-link targets, writes through a temporary file, and uses a no-overwrite hard-link operation.
- Existing content is verified rather than silently replaced. Read operations detect post-write tampering.
- Focused tests cover binary bytes, idempotent writes, missing artifacts, malformed references, tampering, and a corrupt storage adapter.

## Explicit guarantees and non-guarantees

This slice proves **byte integrity across the adapter write/read boundary** when the service returns a receipt. It does not prove that the bytes genuinely originated from EGX/FRA or that the declared publisher is authentic.

The filesystem adapter is a storage implementation, not yet a deployment decision. Production use requires a protected persistent volume, backup/recovery procedures, capacity/retention controls, and an explicit deployment configuration. It is not a multi-node object-storage solution.

## Remaining integration gates

1. Wire artifact intake to the authenticated calendar-operator API without accepting a caller-supplied digest as proof.
2. Require a verified storage receipt before new evidence can be recorded as `ARCHIVED`; preserve `EXTERNAL_ONLY` with an explicit non-retention reason.
3. Ensure evidence publication checks the referenced artifact bytes and digest before committing the evidence record. Define cleanup/reconciliation for uploaded artifacts that are not attached to a published evidence record.
4. Record source-verification method and outcome separately from byte integrity. HTTPS, publisher labels, and a matching digest do not independently authenticate the source.
5. Establish source-specific retention/reuse permission and deployment retrieval/backup evidence before claiming legal or operational retention compliance.

Until these gates are complete, the existing calendar API's operator-supplied artifact digest/reference fields must not be described as independently verified archival. The new storage service is not yet wired into that API.

## Scope exclusions

No calendar activation, lifecycle monitoring, freshness enforcement, provider-finality behavior, or M61 work is introduced.
