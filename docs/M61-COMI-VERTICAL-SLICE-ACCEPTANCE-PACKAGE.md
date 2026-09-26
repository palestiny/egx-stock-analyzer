# M61 COMI Vertical-Slice Acceptance Package

Status: Ready for a real acquired artifact; no COMI artifact is accepted yet.

## Objective
Use COMI as the first end-to-end market-data acceptance slice before acquiring the remaining nine M61 cohort symbols.

## Required artifact
A provider-delivered daily historical CSV (or legally retainable equivalent) covering at least 252 prior trading observations plus the 2021-01-01 through 2025-12-31 evaluation window.

The artifact must remain unchanged after acquisition. Any normalized copy is a derived artifact with its own checksum.

## Acceptance evidence
### A. Identity
- provider name
- source symbol
- EGX identity / ISIN when available
- internal Stock UUID mapping
- mapping evidence

### B. Coverage
- first source date
- last source date
- total rows
- rows inside evaluation window
- warm-up rows
- duplicate dates
- out-of-order dates
- missing/suspended periods
- explicit exclusions and reasons

Weekends and public holidays are not classified as missing sessions by the generic validator. Exchange-calendar evidence is required for any session-gap conclusion.

### C. Price semantics
Record exactly one: raw_as_published, adjusted_provider, or adjusted_project_transform.
For any adjusted series, record the provider/project methodology and transformation version. Never mix conventions inside one dataset version.

### D. Provenance
- source/provider
- acquisition timestamp
- source URL or delivery reference
- artifact SHA-256
- transformation SHA-256
- schema version
- acquisition tool/version
- licensing/storage/use note

### E. Validation
- required-field validation
- ISO date validation
- deterministic ascending order
- duplicate-date rejection
- numeric/finite OHLCV validation
- OHLC relationship validation
- non-negative volume validation
- coverage checks
- stable symbol mapping

### F. Point-in-time boundary
COMI market data is only one half of the Strategy v0 evidence boundary. Financial snapshots remain independently gated by period_end <= available_at <= decision_date.

## Acceptance states
CANDIDATE -> ACQUIRED -> VALIDATED -> PROVENANCE_VERIFIED -> LICENSE_VERIFIED -> ACCEPTED

Any failed gate returns the artifact to REJECTED or QUARANTINED; it must not be silently repaired into acceptance.

## Current COMI status
CANDIDATE

Public EGX.news evidence confirms that COMI is covered by the site's listed-stock market-data service and that full daily historical CSV packages are advertised. This is product availability evidence, not evidence that a specific COMI artifact has been acquired or accepted.

## Next action
Acquire exactly one real COMI artifact from the chosen source, preserve it unchanged, calculate its checksum, run the validation package, and record the provider's adjustment and retention terms before expanding the acquisition to the other nine symbols.