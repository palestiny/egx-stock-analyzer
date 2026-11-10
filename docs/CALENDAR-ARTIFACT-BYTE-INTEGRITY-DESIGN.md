# Calendar Artifact Byte Integrity — Implementation Slice

**Status:** byte-storage, authenticated upload, and publication-time byte verification are merged in `main` (`d1114c1`). All five exact PR-head CI jobs passed; post-merge main CI run #42874061006 is in progress.

## Scope implemented

- `CalendarArtifactService` computes SHA-256 from the exact input bytes.
- The service writes through a storage port, reads the bytes back, recomputes SHA-256, and returns a receipt only when the digests match.
- `FileSystemCalendarArtifactStore` uses content-addressed paths (`sha256:<digest>`), rejects malformed references and symbolic-link targets, writes through a temporary file, and uses a no-overwrite hard-link operation.
- Existing content is verified rather than silently replaced. Read operations detect post-write tampering.
- Focused tests cover binary bytes, idempotent writes, missing artifacts, malformed references, tampering, and a corrupt storage adapter.
- Authenticated operator upload is exposed as `POST /api/v1/owner/session-calendars/artifacts` with `Content-Type: application/octet-stream`. The server streams the request into a bounded buffer, computes the digest, stores the bytes, reads them back, and returns the storage reference plus computed digest only after verification.
- Every `ARCHIVED` evidence item is re-read and verified by the SQLite publication Unit of Work itself, before it opens the database transaction. This protects direct internal callers as well as the HTTP route; there is no API-only bypass. Missing or tampered artifacts fail closed; `EXTERNAL_ONLY` evidence remains unchanged and still requires an explicit non-retention reason.
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

The current implementation proves that the stored bytes matched the computed digest at upload/read-back and again inside the publication Unit of Work before the database transaction begins. It does not prove source authenticity, legal retention permission, or future availability after external storage loss/tampering.

## Scope exclusions

No calendar activation, lifecycle monitoring, freshness enforcement, provider-finality behavior, or M61 work is introduced.


## Read-only artifact inventory — implementation slice in progress

A report-only inventory command is being added at `app/infrastructure/maintenance/calendar_artifact_inventory.py`.

- Reads `ARCHIVED` evidence references through a SQLite `mode=ro` connection with `query_only`; it does not initialize or migrate the database.
- Scans only the content-addressed two-level filesystem layout and hashes regular files without following symbolic links.
- Classifies referenced-and-valid, orphaned, missing, integrity-failure, invalid-reference, and invalid-storage-entry cases.
- Emits a JSON report and a non-zero exit code when any non-clean condition is found.
- Requires explicit database and storage-root paths; a missing storage root is an error and is never created.
- Does not delete, move, rewrite, repair, or otherwise mutate database records or files. Orphan cleanup remains prohibited until a separate retention/deletion policy is approved.

This report describes the state observed during one scan only. It does not prove publisher authenticity, legal retention permission, or future availability, and it does not reconcile concurrent writes as an atomic snapshot.
