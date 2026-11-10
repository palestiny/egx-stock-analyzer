# Calendar Artifact Byte Integrity — Implementation Slice

**Status:** byte-storage, authenticated upload, and publication-time byte verification are implemented on a stacked feature branch; CI and merge are pending.

## Scope implemented

- `CalendarArtifactService` computes SHA-256 from the exact input bytes.
- The service writes through a storage port, reads the bytes back, recomputes SHA-256, and returns a receipt only when the digests match.
- `FileSystemCalendarArtifactStore` uses content-addressed paths (`sha256:<digest>`), rejects malformed references and symbolic-link targets, writes through a temporary file, and uses a no-overwrite hard-link operation.
- Existing content is verified rather than silently replaced. Read operations detect post-write tampering.
- Focused tests cover binary bytes, idempotent writes, missing artifacts, malformed references, tampering, and a corrupt storage adapter.
- Authenticated operator upload is exposed as `POST /api/v1/owner/session-calendars/artifacts` with `Content-Type: application/octet-stream`. The server streams the request into a bounded buffer, computes the digest, stores the bytes, reads them back, and returns the storage reference plus computed digest only after verification.
- Every `ARCHIVED` evidence item is re-read and verified against its expected digest before the SQLite publication Unit of Work starts. Missing or tampered artifacts fail closed; `EXTERNAL_ONLY` evidence remains unchanged and still requires an explicit non-retention reason.
- Compose config uses `/data/calendar-artifacts` on the existing persistent `egx-data` volume. The default maximum upload size is 20 MiB (`EGX_CALENDAR_ARTIFACT_MAX_BYTES`); the path and limit are configurable. Non-Compose runtime configuration keeps storage disabled unless `EGX_CALENDAR_ARTIFACT_STORAGE_PATH` is set.

## Explicit guarantees and non-guarantees

This slice proves **byte integrity across the adapter write/read boundary** when the service returns a receipt. It does not prove that the bytes genuinely originated from EGX/FRA or that the declared publisher is authentic.

The filesystem adapter is a storage implementation, not yet a deployment decision. Production use requires a protected persistent volume, backup/recovery procedures, capacity/retention controls, and an explicit deployment configuration. It is not a multi-node object-storage solution.

## Remaining acceptance gates

1. Define and implement source-verification method and outcome separately from byte integrity. HTTPS, publisher labels, and a matching digest do not independently authenticate the source.
2. Establish source-specific retention/reuse permission before treating any artifact as lawfully retainable.
3. Validate backup/restore and recovery procedures for the persistent volume; the filesystem adapter is not a multi-node object-storage solution.
4. Define reconciliation for uploaded artifacts that are not attached to a successful publication. No automated deletion is enabled because deletion rights and retention policy have not been approved.
5. Decide whether a future authenticated artifact-download endpoint is required for operator workflows.

The current implementation proves that the stored bytes matched the computed digest at upload/read-back and again immediately before publication. It does not prove source authenticity, legal retention permission, or future availability after external storage loss/tampering.

## Scope exclusions

No calendar activation, lifecycle monitoring, freshness enforcement, provider-finality behavior, or M61 work is introduced.
