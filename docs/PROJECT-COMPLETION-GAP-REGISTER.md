## Latest verified continuation — 2026-11-11 (current-main CI and OHLC triage closeout)

- PR #506 forensic triage merged as `c531969245591e93b817b542452470a7899dc4b6`; post-merge run #42988609864 passed all six jobs.
- PR #504 introduced bounded CI job timeouts and merged; exact-head run #42952211069 passed.
- Current `main` is `cc08f399779164ad0d40a4375f5ca4e310c88009`; post-merge run #42989380564 passed all six jobs on that exact SHA. The latest unit-test job, integration tests, frontend, dependency audit, container build, and read-only daily-history audit all succeeded.
- Operational follow-up remains evidence acquisition/reconciliation, not price correction: 51 OHLC geometry exceptions and 19 source/revision conflicts remain unresolved (70 review rows total). Preserve the canonical CSV unchanged.
- DEC-130 remains open. EGID is the preferred authorized-source contact route; DataCedar is a bounded diagnostic candidate only. No source is accepted, and no provider selection, paid plan, ingestion, adapter, eligibility promotion, or M61 activation is authorized. PR #321 remains Draft/unmerged.

**Baseline:** `main` `cc08f399779164ad0d40a4375f5ca4e310c88009`; post-merge CI run #42989380564 passed 6/6.  
**Last reviewed:** 2026-11-11.

---

## OHLC anomaly triage and post-PR #505 CI — 2026-11-11

- [x] PR #505 merged as `cd75815cc749674321ffd273dde917dd44040cf8`; all six exact-head CI jobs passed on `c7f3a5bec3012db3b923384b169ab12eb9580685`.
- [x] Post-merge `main` run #42953081919 passed all six jobs on the exact merge SHA.
- [x] Python 3.12: 1,661 passed, 8 deselected, 1 warning; 298.49 seconds; 90.58% coverage. Lint and type-check passed.
- [x] Captured a read-only audit artifact (#13825822366) and added `docs/OHLC-ANOMALY-FORENSIC-TRIAGE-2026-11-11.md`.
- [ ] Independently reconcile the 51 OHLC rows under the existing protocol. The 4–5 November cohorts (30 rows) are the first investigation priority; no root cause or replacement value has been established.
- [ ] Independently reconcile the remaining 19 source/revision-conflict rows.
- [ ] Obtain EGID sample, exact field/session semantics, revision policy, coverage, and written intended-use/retention terms.
- [ ] Complete DEC-130 immutable market-data and point-in-time financial evidence before any M61 evaluation.

The triage is diagnostic only. Canonical CSV blob `3c01a843c225d226dc49e7c302220a280cfafb57` and SHA-256 `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3` remain unchanged. Do not repair, replace, delete, forward-fill, or promote any row without independent evidence and explicit review. PR #321 remains Draft/unmerged; M61 remains paused.

---

## PR #503 merge and post-merge CI closeout — 2026-11-11

**Status: documentation closeout merged; post-merge CI passed 6/6; historical-source acceptance remains open and M61 remains paused.**

- PR #503 merged into `main` as `f9a75726f6ca61924f64886b169830a555b019e6` after all six exact-head jobs passed in run #42950852464 on PR head `ff8cdc2d386a0278ddc3eb529ff67d05360bb3dc`.
- Post-merge run #42951664652 completed successfully on that exact merge SHA; all six jobs passed.
- Python 3.12 unit tests: 1,661 passed, 8 deselected, 1 warning; runtime 309.44 seconds; coverage 90.58% against the 85% minimum. Lint and type-check passed. The test duration explains the earlier apparent delay; it is not evidence of a stalled test process.
- No timeout change was made because this run establishes a baseline but does not determine an appropriate timeout threshold. The Starlette/httpx deprecation warning and Node.js 20 action deprecation notices are maintenance observations, not CI failures.
- PR #321 remains Draft/unmerged. Keep it blocked pending DEC-130 evidence acceptance. No historical source is accepted, and M61 remains paused.

### Remaining acceptance work

- [ ] Contact EGID for a dated sample, field semantics, source lineage, revision/correction policy, coverage, and written licensing/retention terms.
- [ ] If the owner deliberately provisions an authorized free DataCedar key, perform only the bounded metadata-first diagnostic after confirming permitted query and retention scope; do not expand into archive replication.
- [ ] Independently reconcile the 70 review rows and 51 OHLC geometry exceptions without editing canonical observations absent evidence and explicit review.
- [ ] Obtain point-in-time financial snapshots and complete the DEC-130 immutable evidence package before any M61 evaluation.

---

## DataCedar candidate review and post-merge CI closeout — 2026-11-11

**Status: PR #502 merged; post-merge CI passed 6/6; no source accepted and M61 remains paused.**

- PR #502 merged as `33abc76c322f90af5a5ff583dd0a956ee1aabea7` after all six exact-head jobs passed in run #42949076002 (PR head `783c34ae092a96ca651985f0837e7d1a40da2481`).
- Post-merge main run #42949638348 completed with conclusion `success` on the exact merge SHA; all six jobs passed, including Python 3.12 unit tests and the daily-history audit report.
- The merged DataCedar review identifies it only as a candidate for a bounded, no-cost recent-history diagnostic. Explorer's one-year daily-history limit is insufficient for the M61 2021–2025 period plus 252-session warm-up. Actual per-symbol coverage, source lineage, raw/adjusted semantics, revisions, and the exact retained-sample rights remain unverified. The pricing matrix's raw-close-only statement conflicts with API adjustment options; obtain written clarification.
- No API key, authenticated request, price-row download, paid plan, production adapter, or ingestion was used or authorized. Do not treat documentation or a successful contract probe as data-source acceptance.
- Current main is `33abc76c322f90af5a5ff583dd0a956ee1aabea7`. PR #321 remains the only pre-existing product/M61 PR and is still Draft/unmerged; PR #503 is this documentation-only closeout. Keep #321 blocked pending DEC-130.

### Remaining acceptance work

- [ ] Contact EGID for a dated sample, field semantics, source lineage, revision/correction policy, coverage, and written licensing/retention terms.
- [ ] If the owner deliberately provisions an authorized free DataCedar key, perform only the bounded metadata-first diagnostic after confirming permitted query and retention scope; do not expand into archive replication.
- [ ] Independently reconcile the 70 review rows and 51 OHLC geometry exceptions without editing canonical observations absent evidence and explicit review.
- [ ] Obtain point-in-time financial snapshots and complete the DEC-130 immutable evidence package before any M61 evaluation.

---

## Daily-history retrieval precision and row-level review inventory — 2026-11-11

- First authorized-source contact identified: EGID states that it is a fully owned EGX subsidiary and sole authorized market-data provider; its Market Data Department contact is `marketdata@egidegypt.com`. Arab Finance's 2023 interview also describes EGID as EGX's sole distributor and says other vendors receive data from EGID. Request an exact dated sample and written terms; no EGID data sample, feed contract, or field semantics have yet been verified. References: https://egidegypt.com/ ; https://egidegypt.com/contact-us.html ; https://arabfinance.com/en/News/newdetails/5055
**Status: retrieval-precision audit improvement merged; 70-row review inventory documented; independent source reconciliation remains open.**

- PR #500 merged as `386b710cb74e34697ceae7d5a883067d7f1c4699` after all six exact-head CI jobs passed in run #42946596578. Python tests: 1,661 passed, 8 deselected, 1 warning; coverage 90.58% against an 85% threshold.
- The audit now distinguishes 233 timezone-aware retrieval timestamps from 22 date-only values. All 22 date-only values belong to the EGAL seed and retain their original date-only form.
- Canonical CSV identity: Git blob `3c01a843c225d226dc49e7c302220a280cfafb57`; SHA-256 `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`. Structural findings: 255 rows, 61 symbols, 31 sessions, 51 OHLC exceptions, 70 review rows, no malformed rows, and no duplicate keys.
- PR #501 merged as `6d0cbd50c937f9de584ae0e0186e130eacc1e399` after all six exact-head CI jobs passed in run #42947547289 on `b9f4ec62ef272ee2f31e41bf09edbe632436e26d`. Python unit tests: 1,661 passed, 8 deselected, 1 warning; coverage 90.58%. The merged inventory preserves all 70 row keys, source links, original OHLC values, 22 date-only retrieval rows, and 19 original source-conflict notes.
- All source conflicts and OHLC exceptions remain unresolved pending independent evidence. No values were changed, no source provider was selected, and no analysis/backtest eligibility was promoted.

### Remaining acceptance work

- [ ] Verify all 70 review items against official EGX evidence or contractually authorized/independent sources.
- [ ] Preserve raw evidence, exact source identity, retrieval timestamps, timezone, units, price semantics, and checksums.
- [ ] Record one explicit reviewer disposition and rationale for each item; second-review proposed alternatives/rejections.
- [ ] Establish exchange-session/universe coverage, revision handling, and written licensing/retention/redistribution terms.
- [ ] Keep all review rows excluded from clean OHLC analysis/backtests until their relevant evidence passes.
- [ ] Keep M61 paused; no provider selection, ingestion, automated correction, or eligibility promotion without separate approval.

---

## Daily-history source-reconciliation gate — 2026-11-10

**Status: design/research gate documented; no independent provider selected and no source values changed.**

- PRs #489 and #490 are merged; current main is `139386c682fa9ae129b35ae3f9237dd49c13894a`.
- Main post-merge run #42889360953 has four of five required jobs passed; `unit-tests (3.12)` is still running. Post-merge CI is not yet green.
- A separate read-only reimplementation of the audit checks against CSV blob `3c01a843c225d226dc49e7c302220a280cfafb57` observed 255 rows, 61 symbols, 31 dates, no malformed rows or duplicate keys, 51 OHLC geometry exceptions, and 70 review-labelled rows. It was not execution of the Python CLI and did not create the official JSON report.
- Candidate source routes for evaluation only: official EGX evidence (preferred but no verified public machine-readable historical endpoint established in this research); ICE Data Services (commercial historical/end-of-day EGX coverage: https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx); DataCedar API (vendor claims daily EGX coverage: https://datacedar.com/markets/egypt); EGX.news data service (vendor claims historical daily and intraday datasets: https://www.egx.news/en/our-data). None has been authenticated, sampled, contract-reviewed, or selected.
- Investing.com remains a secondary comparison source only when it is also the original archive source; it cannot independently authenticate its own conflicting observation.
- Provider acceptance requires a dated sample covering all eight flagged 2026-11-10 bars and control rows; preserved raw bytes/payload and digest; timestamp/timezone/unit/price-type semantics; field-level comparison; session/universe coverage and revision policy; written retention/redistribution terms; and explicit human disposition.
- Preserve original values and provenance. No automatic repairs, substitution, inferred fills, or promotion of structural candidates to authenticated analysis inputs.
- Missing traded value/executions (255 rows) and missing volume (23 rows) remain unknown, not zero.
- M61 remains paused. No backtest, provider ingestion, production data-source switch, or trading behavior is enabled by this gate.

### Acceptance checklist

- [ ] Execute the committed Python audit CLI in a supported checkout and retain its generated JSON report with the exact input blob SHA.
- [ ] Obtain source samples and written terms from at least one candidate provider.
- [ ] Independently verify all eight flagged rows and a control sample.
- [ ] Define immutable source-observation and revision lineage before any correction path.
- [ ] Define exchange coverage/completeness checks, including suspended/delisted instruments and index constituents.
- [ ] Obtain owner approval before selecting a provider or enabling ingestion/analysis eligibility changes.

---

## Daily-history read-only audit, classification, and baseline comparison — 2026-11-10

**Status: PRs #487 and #488 merged; structural audit tooling is implemented. Independent source verification, data reconciliation, and analysis acceptance remain open.**

- PR #487 merged as `5c303ff15b97357d7ab086c921061644265ff309`; it adds `tools/egx_daily_history_audit.py` and tests. The audit checks the canonical CSV header/order, malformed rows, required/optional missing fields, ISO dates, symbols, instrument/price-unit pairing, finite numeric values, OHLC geometry, quality labels, provenance-field shape, duplicate keys, latest-session summary, artifact byte count, and SHA-256.
- PR #487 is read-only with respect to the source CSV. It does not fetch or authenticate source pages, infer exchange sessions or missing instruments, repair values, or treat missing volume/traded-value/execution counts as zero. Its source-authenticity result is `NOT_INDEPENDENTLY_VERIFIED`.
- PR #488 merged as `bdef388e06b854324124f5f61099f0f5717e54e6`; exact head `fe9ba50a823f46e6965aa180d7abb4d488a17df3` passed all five required CI jobs in run #42887122981.
- PR #488 classifies each row into exactly one of: `clean_ohlc_candidates`, `review_required`, or `rejected_or_invalid`. Duplicate-key participants are all rejected from analysis eligibility. “Clean” means structurally eligible only; the report explicitly states `STRUCTURAL_CANDIDATE_ONLY_NOT_SOURCE_AUTHENTICATED`.
- Optional `--baseline PATH` comparison reports added, removed, and changed keys/fields without modifying either snapshot. Duplicate keys in either snapshot make the comparison partial; malformed CSV row shapes prevent comparison. A removed key is a difference, not automatically a defect.
- Do not use review-required, rejected, duplicate-key, or otherwise structurally invalid rows as clean OHLC evidence. Do not use structural candidates as authenticated trading/backtest inputs without independent source verification and the applicable acceptance gate.
- No automatic source correction, deletion, or inferred data fill is implemented. Existing source conflicts and OHLC review flags remain preserved pending reconciliation.
- Post-merge main CI run #42888113689 on merge commit `bdef388e06b854324124f5f61099f0f5717e54e6` was still in progress at this update; verify all five jobs before recording post-merge success.

### Remaining acceptance work

- [ ] Run the audit against the canonical archive and preserve the generated report as an explicitly dated artifact; record findings without editing source data.
- [ ] Verify flagged/review rows against trustworthy, independently accessible source evidence; retain original values and append a documented correction/reconciliation only under an approved process.
- [ ] Establish source authenticity, retrieval reproducibility, licensing/reuse rights, and authoritative market-session coverage independently of CSV shape validation.
- [ ] Keep missing traded value/execution counts and unavailable volume explicitly unknown; do not infer zero or no trading.
- [ ] Keep source-conflict and OHLC-review rows excluded from clean technical analysis/backtests until reconciled.

# Project Completion Gap Register

## Calendar artifact inventory and SQLite WAL regression — 2026-11-10

**Status: read-only inventory implementation and WAL regression merged; production operational acceptance remains open.**

- PR #483 merged as `975409d39b2e80ba00e78a96dfda144b21ba802c`; all five required exact-head CI jobs passed. The inventory opens SQLite in read-only/query-only mode, scans the content-addressed storage layout, hashes regular files, and reports `REFERENCED_AND_VALID`, `ORPHANED`, `MISSING`, `INTEGRITY_FAILURE`, `INVALID_REFERENCE`, and `INVALID_STORAGE_ENTRY` classifications.
- The inventory is report-only. It does not initialize/migrate the database, create a missing storage root, repair records, move files, or delete artifacts. Exit codes: 0 clean, 1 findings, 2 scan failure.
- PR #484 merged as `9e120eec682d155204c64bce150f3aee9b6cbdcf`; exact PR head `b4955c3e745593c68c200a1b2038fe9de95a7a2d` passed all five required CI jobs. Its WAL regression verifies committed evidence visibility with an open writer and unchanged DB/WAL bytes. It does not claim shared-memory sidecar bytes are unchanged.
- Post-merge main CI run #42881049920 for `9e120eec...` was still in progress at this update; wait for all five jobs before marking post-merge verification complete.
- No actual production DB/storage scan has been run. Filesystem TOCTOU protection against a hostile concurrent writer is not claimed as complete. SQLite read-only WAL access may participate in normal shared-memory reader coordination.
- No orphan cleanup, retention policy, backup/restore acceptance, multi-node storage acceptance, source authenticity, or legal retention/reuse approval is implemented or approved. No activation/lifecycle/freshness behavior is enabled.

## Daily history collection — PR #476 status

- PR #476 was closed unmerged as superseded by PR #486. The replacement reapplies the same two reviewed data files on current `main`; both files' blob SHAs at the original base were confirmed identical to current `main` before replay. PR #486 preserves 23 2026-11-10 daily historical rows (17 equities, six indices), provenance/limitations, and all eight `ohlc_inconsistency_review` flags. Fresh exact-head CI is required before merge.
- Archive coverage is partial; per-security traded value/execution counts are not established where blank; application DB ingestion is not claimed; M61/backtesting was not performed. PR #321 remains Draft and M61 paused.


**Status:** Active non-M61 engineering/acceptance register  
**Updated:** 2026-11-10  
**Baseline:** `main` at `9e120eec682d155204c64bce150f3aee9b6cbdcf` (PR #484 merged after all five exact-head CI jobs passed; post-merge main CI run #42881049920 pending at this update).  
**M61:** Explicitly paused by owner request; do not advance M61/backtesting work until the owner resumes it.  
**EGXBot direction:** Owner-approved dual strategy engines (intraday + swing), delayed/daily data, new-opportunity and material-change alerts, manual execution only. See `docs/EGXBOT-DUAL-ENGINE-DESIGN-GATE.md`.

This register separates verified implementation from incomplete acceptance and decisions. A module, endpoint, or passing unit test alone does not prove an end-to-end user capability is complete. Owner policy baseline DEC-135 was accepted on 2026-10-31; policy approval does not mark the related engineering acceptance items complete.

## Calendar artifact byte integrity and publication enforcement — 2026-11-10

**Status: byte-integrity and publication-verification implementation merged; operational acceptance remains incomplete. Do not claim full archival or source authenticity.**

- PR #478 is merged: byte-storage port, content-addressed filesystem adapter, and read-back SHA-256 integrity service. All five exact-head CI jobs passed.
- PR #479 is merged as `d1114c1a020825fb1e8477605c5c18c14bf475e6`. Its exact PR head `9cd81700201c38ceeb34b50ffad18e9565b7f959` passed all five required CI jobs in run #42873143036 before merge. Post-merge main CI run #42874061006 is still running.
- The SQLite publication Unit of Work itself verifies every new `ARCHIVED` evidence item against stored bytes and its expected SHA-256 before opening the transaction. Direct callers cannot bypass this rule. Missing artifacts and digest mismatches fail closed. `EXTERNAL_ONLY` still requires an explicit non-retention reason.
- Compose uses the existing persistent `egx-data` volume for `/data/calendar-artifacts`; the default upload ceiling is 20 MiB. Other runtime configurations must explicitly set `EGX_CALENDAR_ARTIFACT_STORAGE_PATH`.
- The upload endpoint computes the digest from the received bytes; the client-provided digest in a later publication request is only an expected value and must match the bytes re-read from storage.
- Remaining acceptance gaps: source authenticity, publisher identity verification, legal retention/reuse rights, backup/restore testing, multi-node storage behavior, and reconciliation of uploaded artifacts not linked by a successful publication. No automated deletion is enabled.
- PR #479 is merged. The five exact-head CI jobs passed; post-merge main CI is not yet green/verified. No activation, lifecycle monitoring, freshness enforcement, or M61 work is included.

## Verified merged foundations


- PR #465 merged immutable, append-only, SHA-256-verified per-day calendar evidence storage with explicit correction/supersession history. PR #471 adds atomic publication coverage, status-kind validation, explicit day/evidence links, and conflict rejection; its exact-head CI passed. PR #475 is merged: owner-approved source acceptance, hybrid artifact-retention metadata, strict evidence-gated publication, explicit OPEN confirmation, exceptional-hours enforcement, and FRA-only regulatory scope. This still does not prove source authenticity or artifact-byte retention.
- PR #466 merged individually attributable operator grants and append-only grant/revoke/bootstrap audit. Durable active credentials and active users are required; the last active operator is protected; first-operator bootstrap is a trusted local command.
- PR #467 merged authenticated session-calendar publication/read API and persistent runtime composition as `03d3969e19e7b73beb3b8427afb5328183d1553e`. All five exact-head checks passed before merge; the same five checks also passed on the merge commit. PR #462 is closed unmerged as superseded.

- Technical-analysis stack includes deterministic indicators and price-action evidence, with API/dashboard integration (PR #364 and follow-on integration).
- News/event ingestion foundations include normalized metadata, SQLite persistence, provider-neutral orchestration, authenticated API, and operator-configured RSS/Atom feeds.
- Crash Radar exposes explainable components and per-symbol snapshot-date evidence (merged PR #387), while the existing 50/40/10 heuristic remains unvalidated as a crash probability.
- Operator subscription administration includes immutable versioned plans, guarded provisioning, audited transitions, and subscription event history (PR #407).
- Owner dashboard subscription controls are merged (PR #408).
- Telegram dispatch has explicit terminal suppression when no linked recipients exist (PR #409).
- Session opportunity ledger/report domain, report builder, SQLite snapshot store, and authenticated snapshot API exist. PR #414 prevents signals generated after a report's `generated_at` cutoff from leaking into a historical snapshot and validates signal data timestamp timezone-awareness. Automatic end-of-session scheduling and subscriber delivery remain unproven end-to-end.
- PR #416 adds a passing contract test for publication through durable outbox to an entitled linked Telegram recipient with idempotent replay. This proves that tested path only, not all lifecycle states or production scheduling.
- `docs/RELEASE-READINESS-CHECKLIST.md` exists as a checklist template, not a declaration of production readiness.
- EGXBot approved design constraints and implementation gates are recorded in `docs/EGXBOT-DUAL-ENGINE-DESIGN-GATE.md`.
- PR #438 adds finite-number and timezone/chronology invariants to signal-outcome records; exact-head CI run #41203293617 passed all five jobs. Merge commit: `29f7b6655109e91940159e9bf14be1d9eacbf189`.
- PR #439 adds finite-number and timezone-aware timestamp invariants to signal domain models; exact-head CI run #41203128989 passed all five jobs. Merge commit: `7f825a08430b354814b5c875b4aa106d0b2131d2`.
- PR #441 exposes each opportunity's source-data timestamp and the outcome's source-data timestamp in API responses and immutable SQLite snapshots. Exact-head CI run #41204283794 passed all five jobs. Merge commit: `a65612d2f6447dff041699f99e4f879c5a9c4a89`. These are provenance timestamps, not a freshness classification.
- PR #442 updates this register and the session-report scheduler design gate after PR #441. Exact-head CI run #41204657069 and post-merge main run #41205090278 passed all five jobs. Merge commit: `7a672a890e7334335f90b359dbf2c86d845eda6a`.
- PR #443 corrects terminal outcome provenance: `SignalMarketState` now carries the actual market-data source timestamp, and terminal `SignalOutcomeRecord.data_timestamp` is populated from that observation rather than signal-generation data. Exact-head CI run #41205688356 passed all five jobs. Merge commit: `f7de38c6a1c8a2e4cdb0bd29fd7eac5eed80342d`.
- PR #445 limits session opportunity reports to signal identities with a `PUBLISHED` or `PUBLISHED_VERSION` event, preserves the first published version as the original snapshot, and assigns the report session by publication time in the exchange timezone. Exact-head CI run #41206339863 passed all five jobs; 1,469 tests passed, 8 deselected, 90.73% coverage. Merge commit: `d86f418ea927c11755c821a6c1c44c736023ddca`.
- PR #459 merged the explicit, fail-closed EGX session-calendar domain model with contiguous per-day coverage, Africa/Cairo wall-clock times, explicit day states, and completed-session confirmation. No weekend, holiday, or session-time inference is allowed.
- PR #460 merged immutable SQLite calendar-version persistence, SHA-256 integrity checks, the active-version pointer, and append-only activation/deactivation/rollback audit events. No calendar has been published or activated.
- PR #467 merged the individually authenticated operator publication/read API and persistent runtime composition after all five exact-head CI jobs passed. PR #462 is closed unmerged as superseded.

## Calendar evidence publication — atomicity implementation (2026-11-09)

**Status: IMPLEMENTED — merged in PR #471 after all five exact-head CI jobs passed.**

### Problem verified in current implementation
The calendar-version repository and calendar-evidence repository each manage their own SQLite connections and transaction scopes. Evidence rows reference an already-persisted calendar version, so the current composition cannot guarantee that a version and all required per-day evidence are committed or rolled back as one operation. An API-level pre-check alone would leave a time-of-check/time-of-use gap and could persist a calendar version without its complete evidence set.

### Approved transaction contract
1. Begin one write transaction on the calendar database (SQLite `BEGIN IMMEDIATE`).
2. Validate the individually authenticated operator identity and normalize the requested calendar/evidence payload before writes.
3. Insert the immutable calendar version using the transaction connection.
4. Insert immutable evidence records and explicit per-day links using that same connection.
5. Validate exact date coverage, evidence-kind acceptance rules, source-policy requirements, supersession consistency, and unresolved conflicts against the transaction's pending state.
6. Commit only when every validation passes. Any exception or failed gate rolls back the version, evidence rows, links, and related audit entries together.
7. Publication remains distinct from activation. No active-version pointer, activation event, lifecycle cursor, or monitoring state is changed by this transaction.

### Implemented code boundary (merged PR #471)
The calendar-specific SQLite Unit of Work owns one connection and `BEGIN IMMEDIATE` transaction. Calendar and evidence repositories participate through the transaction connection; rollback, isolation, conflict, and production-runtime composition tests are merged in PR #471. No generic cross-domain transaction framework was introduced.

### Required invariants and tests
- The calendar version and all per-day evidence/link rows are visible together after commit.
- Failure after version insert, after any evidence insert, after link creation, and during final policy validation leaves no partial publication state.
- A second connection cannot observe uncommitted rows.
- Concurrent publication attempts serialize safely; duplicate/version conflicts fail deterministically without overwriting immutable history.
- Missing dates, unsupported evidence kinds, conflicting unsuperseded claims, mismatched version/date links, invalid supersession, and unauthorized operators fail closed.
- Existing published/read API contracts and append-only update/delete protections remain intact.
- Tests use the production runtime composition and a temporary on-disk SQLite database, not only isolated in-memory repository fakes.

### Decisions intentionally outside this implementation
D1–D4 evidence acceptance, source classes, hybrid retention metadata, and strict publication are owner-approved and implemented in PR #475, pending final exact-head CI. Independent publisher authenticity, artifact-byte verification and lawful retention, and deployment bootstrap/recovery remain separate operational gates. An operator-supplied digest does not prove source authenticity. These decisions do not authorize calendar activation or lifecycle monitoring.

### Rollout and compatibility
First add the UoW and repository transaction seams with focused tests; then route the publication use case through it. Preserve existing schema and immutable record IDs where possible. If an explicit per-day link table or schema migration is required, document the migration and prove upgrade-from-existing-database behavior before release. Do not silently retrofit existing evidence or infer missing evidence.

## Non-M61 work remaining

### P0 — Verify latest merged main CI

- [x] PR #460 merge commit `d171324800027e9b298bfde9529eb5b75c5d8ec1` passed all five main-branch jobs in run #42619902277.
- [x] PR #422 merge commit `fa5d16a9b8a47e3cdcb9467d1e31ffd4ee6bed64` passed all five main-branch jobs in run #41185546490.
- [x] PR #432 merge commit `93984f481cfbfeb19411f8230f03442a494702bc` passed all five post-merge main jobs in run #41197870758.
- [x] PR #433 exact-head CI run #41198262173 passed all five jobs before merge. Its merge commit is `4733e9237495789ebceba9113567e42b7b6abf6d`; later main commit `d171324800027e9b298bfde9529eb5b75c5d8ec1` includes this change and passed all five CI jobs in run #42619902277.

### P1 — EGX session calendar, lifecycle freshness, and operational readiness

- [x] Implement explicit, contiguous, fail-closed EGX session-calendar domain records (PR #459).
- [x] Persist immutable calendar versions with SHA-256 verification and append-only activation audit history (PR #460).
- [x] Merge authenticated calendar publication/read API with exact-head CI and post-merge main CI verification (PR #467).
- [x] Implement immutable per-day evidence storage and named, attributable operator identities (PRs #465 and #466).
- [x] Merge PR #475 after all five exact-head CI jobs passed; source-class acceptance, FRA regulatory scope, hybrid retention metadata, explicit OPEN confirmation, exceptional-hours evidence, and strict publication are implemented. Post-merge main CI run #42867152618 was pending its unit-test/coverage job at this snapshot.
- [ ] Independently verify source publisher authenticity and artifact bytes against the recorded digest; confirm lawful retention and retrievability in deployment.
- [ ] Verify first-operator bootstrap and recovery against the actual deployment database and operational procedure.
- [ ] Approve calendar bootstrap and cursor-derived coverage horizon; keep activation endpoints unavailable until the durable evaluation cursor and recovery rules exist.
- [ ] Connect the calendar to durable lifecycle scheduling and chronological recovery only after provider-completed-bar attestation and freshness semantics are verified.
- [ ] Keep lifecycle monitoring and Crash Radar freshness enforcement disabled until all required calendar, provider, and recovery gates pass.

### P1 — EGXBot market-data readiness and dual engines (stale/invalid-data safety policy accepted in DEC-135)

- [x] Review current provider contract against DEC-139 and record the gap in `docs/MARKET-DATA-PROVIDER-RELIABILITY-DESIGN-GATE.md`: provider identity, retrieved-at, session mapping, finality attestation and revision identity are not carried by the current `MarketDataProvider`/`RawPriceBarObservation` contract; `DataQualityAssessor` does not implement expected-session STALE eligibility.
- [ ] Approve the provider observation envelope and finality/correction contract after a candidate provider's technical documentation is verified.

- [x] Inspect current adapter path: `YahooFinanceHistoryClient.history()` requests daily bars only (`interval="1d"`); `YahooFinanceAdapter` maps `{stock.symbol}.CA`, carries OHLCV and normalizes naive timestamps as UTC. This is code behavior, not verified provider timezone semantics, delay, coverage, rate limits or reuse rights.
- [x] Verify source-bar timestamp is carried into `StockAnalysisResult.data_timestamp` and serialized with analysis snapshots; `GenerateSignal` suppresses output if timestamp is absent or timezone-naive (PR #418 and current main code).
- [ ] Verify EGX symbol coverage, actual timestamp/timezone semantics, data delay, corrections and rate limits.
- [x] Record Yahoo Finance/yfinance commercial-use and redistribution restriction as an explicit blocker in PR #436. Do not redistribute Yahoo-derived data or expose it to paid/subscriber users until exact applicable terms and written permissions are verified.
- [ ] Select and verify a market-data provider whose contract explicitly permits the intended commercial API use and redistribution, if the product will serve third-party/subscriber users.
- [ ] **Commercial-use blocker:** current implementation uses the unofficial `yfinance` client against Yahoo Finance. The yfinance project describes the Yahoo Finance API as intended for personal use; Yahoo Finance Help says its information must not be redistributed; Yahoo's terms restrict commercial reuse absent explicit permission. Do not expose, redistribute, cache for third-party access, or build paid/subscriber-facing features on Yahoo-derived data until the exact applicable Yahoo product terms and written permissions are verified. Prefer a market-data provider offering an explicit commercial redistribution/API licence for a sellable product. References: https://ranaroussi.github.io/yfinance/ ; https://help.yahoo.com/kb/SLN2310.html ; https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html .
- [ ] Implement and test an explicit completed-session freshness/provenance gate; current validation rejects future/invalid observations but does not classify stale daily bars. Do not invent a calendar or freshness cutoff before its source/semantics are established.
- [ ] Introduce separate, versioned intraday and swing strategy boundaries without silently changing existing scoring or trade rules.
- [ ] Keep intraday strategy output suppressed or explicitly observational until suitable intraday data freshness/granularity is verified; daily bars must not be presented as live intraday evidence.
- [ ] Define relative volume/traded-value evidence from available bars; do not claim order-book imbalance or smart-money activity without suitable underlying data.
- [ ] Record rationale, data timestamp, strategy version, entry conditions, invalidation, targets and expiry on every published opportunity.

- [x] PR #435 aligns recurring configured market-analysis scheduling with the EGX regular Sunday–Thursday trading weekdays and skips Friday/Saturday. Exact-head CI run #41201163061 passed all five jobs; merge commit `c94b0c71db296341aae5f156edf6d3a913bd210c`. This weekly rule does not model official exchange holidays.
- [ ] Add a verified EGX exchange holiday/session calendar before claiming holiday-aware scheduling or completed-session freshness. The current weekday schedule is not a substitute for the official calendar.

### P1 — Opportunity lifecycle and Telegram delivery acceptance (owner policy accepted in DEC-135)

- [x] Verify publication -> durable outbox -> entitled linked recipient -> Telegram transport with idempotent replay via PR #416 contract test.
- [ ] Add/verify contract tests for revised version, invalidation, expiry, target/stop observations, duplicate dispatch, transient failure/retry/recovery, retry exhaustion, no linked recipients and entitlement changes.
- [x] Trace lifecycle composition: `SignalLifecycleOrchestrator` is constructed in `app/infrastructure/runtime.py`, but the inspected opportunity publication API route calls only `GenerateSignal` and `PublishSignalOpportunity`; it does not invoke lifecycle processing. Automatic target/invalidation observation is therefore not evidenced.
- [x] Record the missing observation integration and required price/data/expiry/revision decisions in `docs/SIGNAL-LIFECYCLE-OBSERVATION-INTEGRATION-DESIGN-GATE.md`.
- [x] Confirm per-user opportunity history is not yet evidenced: signal history is global by signal identity, and recipient delivery rows do not provide a user-scoped lifecycle history/read model.
- [ ] Implement an authorized per-user opportunity history/read model with immutable publication versions and lifecycle states after the observation/revision contract is approved.
- [ ] Implement and prove end-to-end re-evaluation only after the observation-price, crossing, data-eligibility, expiry and revision semantics in that gate are resolved.
- [ ] Preserve original published rationale and price levels; keep hypothetical opportunity outcomes separate from actual portfolio P&L.
- [ ] No change to scoring thresholds or automatic recommendation policy without a separately accepted decision.

### P1 — Session reports (owner policy accepted in DEC-135)

- [x] Historical snapshot builder excludes signals whose `generated_at` or `data_timestamp` is after the requested report cutoff; timezone-aware timestamp validation is covered by tests (PR #414).
- [x] Trace session report API, store, runtime/lifespan composition, existing scheduler contracts, and Telegram delivery boundaries; confirmed the report builder/store/API are composed but no automatic session-report scheduler is wired.
- [x] Record the missing scheduling design gate and required calendar/time/correction/delivery decisions in `docs/SESSION-REPORT-SCHEDULER-DESIGN-GATE.md`.
- [x] Expose per-opportunity source-data timestamps for the original signal and recorded market-proxy outcome (PR #441); source timestamps are now traceable, but stale/fresh classification remains open until provider semantics and a freshness policy are verified.
- [ ] Implement the durable end-of-session trigger only after the authoritative EGX session/holiday calendar, completed-session cutoff, and deployment/worker ownership are established; the design gate recommends a durable occurrence ledger and worker.
- [ ] Verify report contents include session summary, opportunities published during the session, status changes/invalidation, resolved versus unresolved outcomes, source freshness and methodology limitations.
- [ ] Add end-to-end tests for scheduled generation, duplicate scheduler invocation, missing data, delayed signals, timezone/session boundaries and delivery failure.
- [ ] Until scheduling and delivery are proven by integration tests or workflow evidence, describe reports as API/manual, not automatic.

### P1 — Subscription and commercial boundary (manual entitlement policy accepted in DEC-135; billing deferred)

- [ ] Keep operator-managed activation manual and auditable; do not treat manual provisioning or payment metadata as proof of payment.
- [ ] Before gateway implementation, record owner decisions for pricing/tiers, payment provider, checkout, trusted webhook verification, idempotency, refunds/chargebacks, cancellation and reconciliation.
- [ ] Verify server-side entitlement enforcement across API and Telegram, including expired/pending/cancelled subscriptions and replayed or out-of-order provider events.
- [ ] Do not treat `payment_provider` or `payment_reference` metadata as verified payment.

### P1 — Crash Radar policy gate (DEC-133 / DEC-135)

[x] Owner policy baseline accepted in DEC-135. Engineering implementation and verification remain open:

- [ ] Implement configurable monitored universe and completed-session freshness evaluation.
- [ ] Mark stale/missing/insufficient coverage explicitly; preserve explainability and avoid automatic alerts.

DEC-135 resolves the owner-policy baseline. Preserve the existing 50/40/10 heuristic; do not change score semantics, enable alerts, or call the score a crash probability or trading signal. The detailed implementation and evidence tasks remain open.

### P1 — News/source policy gate (official-source-only policy accepted in DEC-135; source-specific terms verification remains open)

- [ ] Review a specific official EGX/company-disclosure source, its terms/licensing, attribution, retention, rate limits, timestamp quality and historical coverage.
- [ ] Configure only sources whose terms and operational access have been accepted; retain provenance and point-in-time timestamps.
- [ ] Test duplicate/corrected/late/undated events and symbol-matching uncertainty.
- [ ] Keep news interpretation separate from signal ranking and Telegram alerts until a versioned scoring/alert decision and tests are approved.

### P2 — Repository hygiene and release readiness

- [ ] Review stale branches by comparing each branch to `main` and any associated PR before deletion. Do not mass-delete branches based on names alone.
- [ ] Keep PR #321 and other M61 work paused; do not merge or close them as “complete” while the owner has explicitly deferred M61.
- [x] Add a release checklist template for environment configuration, persistence/migrations, authentication/authorization, secrets, backups, observability and rollback; production readiness still requires evidence for every applicable item.
- [ ] Run a final complete CI and API/UI smoke-test matrix before claiming product completion.

## Acceptance standard

A work item is complete only when:
1. its user-visible behavior and failure states are specified;
2. the implementation respects domain/application/infrastructure boundaries and existing contracts;
3. tests cover normal, edge, invalid, duplicate/retry and authorization cases where relevant;
4. CI is green on the final commit;
5. docs match shipped behavior and explicitly identify external dependencies or owner decisions.

This register is not a claim that all listed work is implemented. It is the auditable checklist for closing remaining non-M61 gaps without silently inventing product policy.


## Owner policy decision update — 2026-10-31 (DEC-135)

The owner accepted the conservative non-M61 product/operational baseline:
- configurable Crash Radar universe, completed-session freshness and visible coverage limitations, with no automatic alerts;
- immutable opportunity versions, completed-session re-evaluation, explicit invalidation/expiry, durable auditable Telegram lifecycle, and manual trading only;
- Cairo-time session reports with idempotent generation and traceable corrections without duplicate distribution;
- manual audited subscription entitlements; live billing/pricing/refunds remain deferred;
- official news disclosures only after source access/reuse terms are verified;
- suppression of actionable output when data is stale, missing, future-dated, or invalid, with explicit reason and coverage.

This acceptance closes the owner-policy decision gate, not the implementation checklist. All engineering, integration, source-rights, and operational verification items above remain open until evidenced. M61 remains paused and PR #321 remains open Draft and untouched.


### Telegram concurrency, ambiguous outcomes, and bounded definite retries — DEC-136/DEC-137 (implementation merged and verified)

- [x] Owner decision: ambiguous outcome after send initiation becomes `DELIVERY_UNKNOWN`; do not automatically resend; require operator reconciliation.
- [x] PR #428: atomic per-recipient SQLite claim/lease, opaque claim-token fencing, safe expired-CLAIMED recovery, and expired-SENDING transition to `DELIVERY_UNKNOWN`.
- [x] PR #428: distinguish definite Telegram rejection from ambiguous timeout/connection/server outcomes; preserve unknown outcomes without automatic resend.
- [x] PR #429: operator-only unresolved-delivery listing, audited manual reconciliation, and terminal `NOT_DELIVERED` handling.
- [x] PR #430: operator runbook with authenticated API examples, evidence requirements, and escalation guidance.
- [x] Owner decision: derive lease duration at runtime as 2 × the effective configured Telegram transport timeout.
- [x] Owner approved DEC-137: 3 total attempts; 1-minute then 5-minute retry delays; 15-minute cap; deterministic bounded ±10% jitter; terminal `RETRY_EXHAUSTED`.
- [x] PR #432 merged DEC-137 implementation: durable UTC scheduling, due-only atomic retry claims, account/entitlement re-evaluation, exhaustion visibility, audited reconciliation, and regression tests. Merge commit `93984f481cfbfeb19411f8230f03442a494702bc`; exact-head CI run #41197542121 passed all five jobs.
- [x] Post-merge main CI run #41197870758 passed all five jobs.
- [x] PR #428 tests cover concurrent claims, stale-token fencing, lease recovery, ambiguous transport outcomes, migration, partial recipient safety, and active-claim protection. PR #429 tests cover audited reconciliation and no-resend terminal resolution.

DEC-136 and DEC-137 implementations are merged and verified by PR #432 exact-head CI run #41197542121 and post-merge main CI run #41197870758, each passing all five jobs. This is not exactly-once delivery. `DELIVERY_UNKNOWN` remains manual-only. PR #428 main CI passed in run #41189366403; PR #429 main CI passed all five jobs in run #41191307763.


## Verified continuation — 2026-11-07

- PR #446 merged: authenticated per-user Telegram opportunity notification feed at `GET /api/v1/me/opportunity-notifications`. This is a recipient delivery feed, not a complete lifecycle history.
- PR #447 merged at `8995e8f4d5ef1420ef4d625195d187cb32397679`: canonical `data/market_history/egx_daily_history.csv` contains 186 source-attributed records through the 2026-11-05 session. Thirty-six rows have reported open below reported low and remain flagged; preserve raw values and do not treat them as clean OHLC bars without reconciliation.
- PR #450 merged the approved lifecycle-specific SQLite Unit of Work at `71acf708aab4b1e6c3bc87b2a6d1a1b9bc1db4a`. Exact-head CI #42377116040 and post-merge main CI #42377785229 passed all five jobs.
- PR #452 merged explicit rollback failpoint tests after history, outcome, and outbox writes at `1f6594b74ba6d6814413b325d21c04395180baa2`. Exact-head CI #42377931439 passed all five jobs. Its post-merge verification is superseded by the later PR #454 post-merge main workflow #42399538146, which passed all five jobs on the main line containing PR #452 and PR #454.
- [x] PR #454 closed the previously open restart-recovery and no-network-I/O transaction-boundary test gaps; see the lifecycle persistence and recovery closeout above.
- [ ] Automatic observation wiring and all unresolved source-observation, price, crossing, expiry, revision, and entry-basis policies remain separate gaps.


## Lifecycle persistence and recovery closeout — 2026-11-07

- [x] Atomic lifecycle persistence: PR #450 merged `SQLiteSignalLifecycleUnitOfWork`, enforcing a shared SQLite database and one `BEGIN IMMEDIATE` transaction for signal history, optional market-proxy outcome, and durable alert intent. Telegram network I/O is not performed by the transaction.
- [x] Rollback proof: PR #452 added failure injection after history, outcome, and outbox writes; all participating stores are verified empty after rollback.
- [x] Restart recovery: PR #454 reconstructs the dispatcher and persistent SQLite stores after restart, delivers a pending outbox event, and proves a subsequent dispatcher does not redeliver it.
- [x] Transport boundary: PR #454 verifies lifecycle rows are visible from a separate SQLite connection before the fake Telegram transport is invoked.
- [x] PR #454 exact-head CI passed all five jobs. Post-merge main CI run #42399538146 completed successfully with all five jobs.
- [ ] Automatic observation integration remains open: no accepted application use case currently connects persisted analysis observations to `SignalLifecycleOrchestrator.process` / `invalidate_for_evidence_change`.
- [ ] Observation identity/deduplication, provider timestamp semantics, eligible completed-bar rules, price selection, OHLC crossing precedence, expiry, revision/version behavior, entry-price basis, and missed-observation reconciliation remain gated by explicit decisions and source verification.
- [ ] A user-facing per-user lifecycle history/read model remains distinct from the existing Telegram notification feed and is not yet complete.

The persistence/recovery foundation is verified; automatic monitoring and lifecycle product acceptance are not. M61 remains paused and PR #321 remains Draft.

### P1 — Calendar evidence provenance and individual operator accountability (updated 2026-11-10)

- [x] Owner approved an immutable per-day evidence registry and individual named operator identities.
- [x] PR #465 merged immutable typed evidence records, SHA-256 integrity checks, append-only corrections, explicit calendar-version/date coverage, and conflict visibility.
- [x] PR #466 merged individual operator grants, append-only grant/revoke/bootstrap audit, durable-credential-aware permissions, trusted first-operator bootstrap, and last-operator protection.
- [x] PR #467 merged the authenticated calendar publication/read API and persistent runtime composition.
- [x] PR #471 merged atomic publication: one SQLite `BEGIN IMMEDIATE` transaction persists the immutable calendar version, per-day evidence, explicit links, and validation; failures roll back the entire publication.
- [x] PR #471 enforces evidence coverage for every explicit date, status-appropriate evidence kinds, actor consistency, and unresolved-conflict rejection. Rollback, isolation, in-batch supersession, and production runtime composition tests passed all five exact-head CI jobs.
- [x] Owner approved source-class acceptance by claim type (D1) and hybrid source-artifact retention (D2) on 2026-11-10; enforcement is under PR #475.
- [x] Owner approved strict evidence-gated publication (D3) and the claim-specific day evidence matrix (D4) on 2026-11-10; enforcement is under PR #475.
- [x] PR #475 merged as `04f4dce6c2d2e5b0f0a285aa4eb3534c8af55f22`; exact-head CI passed all five required jobs in run #42866088424.
- [ ] Independently verify archived artifact bytes and publisher authenticity; operator-declared metadata and SHA-256 strings are not authenticity proof.
- [ ] Verify first-operator bootstrap and recovery against the actual deployment database and operational procedure.
- [ ] Close cursor-derived activation coverage/bootstrap and provider completed-bar attestation gates independently.
- [ ] Keep calendar activation and lifecycle monitoring disabled until every relevant gate passes.

PR #471 and PR #475 are merged; both exact-head CI requirements passed before merge. PR #479 added byte-storage and publication-time byte verification. PR #480 reconciled the merged state and is itself merged as `c475b076c82c7c91a5671a91baf18a47afad105f`; its exact-head CI run #42874761255 passed all five required jobs. Evidence completeness and atomicity do not prove source authenticity, licensing, artifact retrieval/retention legality, full EGX calendar correctness, or provider bar finality.


## Daily market-history audit — verified implementation and remaining gaps (2026-11-10)

- [x] PR #486 rebased the 2026-11-10 daily-history batch onto current main after verifying the original README and CSV blobs matched the new base; no rows were discarded.
- [x] PR #487 added a read-only CSV audit covering canonical schema/order, malformed rows, dates, symbols, instrument/unit pairing, finite numeric values, source metadata shape, quality statuses, duplicate session/symbol keys, OHLC geometry, missing metrics, and artifact byte count/SHA-256.
- [x] PR #487 tests include the repository archive and verify the source CSV bytes remain unchanged.
- [x] PR #487 post-merge main CI run #42886017424 passed all five required jobs on main commit 5c303ff15b97357d7ab086c921061644265ff309.
- [x] PR #488 classification/baseline comparison merged as bdef388e06b854324124f5f61099f0f5717e54e6 after all five required CI jobs passed on exact head fe9ba50a823f46e6965aa180d7abb4d488a17df3 in run #42887122981. Structural candidate classification is not source authentication or permission to use unverified rows for trading analysis.
- [ ] Verify post-merge main CI on bdef388e06b854324124f5f61099f0f5717e54e6 before declaring the main-line closeout complete.
- [ ] Independently authenticate source pages/values and reconcile review rows against authoritative EGX evidence; the CSV audit validates structure and arithmetic only.
- [ ] Establish a trusted and repeatable source acquisition process, explicit coverage/completeness evidence, correction/revision handling, and operator review before using these rows as clean analytical history.
- [ ] Keep rows with review statuses or OHLC geometry failures out of clean OHLC analysis/backtests until independently reconciled. Do not silently repair source values.
- [ ] Keep blank volume, traded value, and executions as unavailable; never convert blanks to zero or infer that no trading occurred.
- [ ] Do not claim production ingestion, source authenticity, M61 data acceptance, or strategy-performance validation from the read-only audit.

The latest archive snapshot after PR #486 has 255 rows, 61 symbols, and 31 session dates. Its 2026-11-10 batch has 23 rows (17 equities and six indices), eight OHLC-review flags, no duplicate symbols within that batch, and blank traded value/execution counts for all 23 rows; EGREAL also has blank volume. These are observed archive properties, not claims of complete EGX market coverage.


## Daily-history audit automation and verified main artifact — 2026-11-10

- [x] PR #493 merged CLI subprocess smoke tests for clean input and the canonical repository archive. They verify exit codes, stdout/persisted report agreement, SHA-256/byte-count metadata, and source CSV immutability.
- [x] PR #494 merged the GitHub Actions report job and manual `workflow_dispatch` trigger. The job accepts the audit's findings exit code 1, validates the JSON result, and uploads a SHA-tagged artifact for 14 days.
- [x] PR #494 exact-head CI passed all six jobs on `187e8970e7e0c93331353db86517c5c60f3c8a0a`; post-merge main CI run #42894527758 passed all six jobs on `be8b8fea246870a517f3f80bad9a8123f23efabb`.
- [x] Downloaded and inspected the actual main artifact #13799198851. The report contains 255 parsed rows, zero malformed/invalid/duplicate rows, 51 OHLC geometry inconsistencies, 70 review-required rows, and 185 structural candidates.
- [ ] Add a true scheduled audit trigger if the owner wants a GitHub Actions cron schedule. PR #494 currently runs on push, pull request, and manual dispatch only; it does not run daily on a timer.
- [ ] Independently authenticate the provider values and reconcile all review rows against authoritative EGX evidence.
- [ ] Establish source coverage/completeness evidence, correction/revision handling, legal reuse/retention terms, and a repeatable trusted acquisition process.
- [ ] Keep missing volume/traded-value/execution metrics as unavailable; never convert blanks to zero or infer no trading.
- [ ] Keep all review-required rows out of clean OHLC analysis/backtests until independently reconciled. Structural candidates remain unauthenticated.
- [ ] Keep M61 paused; no analysis-eligibility promotion, automated price repair, provider substitution, or trading behavior is authorized by the audit workflow.

The main report's `analysis_eligibility` is `STRUCTURAL_CANDIDATE_ONLY_NOT_SOURCE_AUTHENTICATED` and `source_authenticity` is `NOT_INDEPENDENTLY_VERIFIED`. The report is a CI artifact with 14-day retention, not a permanent evidence archive or proof of source authenticity.

### CLI findings-path regression

PR #495 merged as `2b18d2d1ac9ea54aa89b17351875802e5970a7ab`; exact-head CI run #42895151535 passed all six jobs on `db52eb8eefa4c54efdd804dfb16d01cd9af111c0`. Its focused subprocess test supplies a structurally parseable CSV with an unlabelled OHLC geometry inconsistency and asserts exit code 1, matching stdout/file JSON, the unlabelled finding count, and unchanged input bytes. PR #496 also merged as `05c3d00e719b3d50c8f9e57dfc73644d54f72a0c` after all six exact-head CI jobs passed in run #42895373313. The latest post-merge main run on the final SHA is queued; verify it before declaring main-line closeout complete.


## Daily-history reconciliation protocol — merged, post-merge CI pending (2026-11-10)

- [x] PR #497 reconciled the historical merge/CI record for PRs #495/#496 and merged as `0e9bbeccf71d75cece2585e8a95a98c3ea700617`; exact-head CI run #42896485869 passed 6/6.
- [x] PR #498 added the evidence-based daily-history reconciliation protocol and merged as `ca556e1c3dd109f6ccb0f981b1c57398ff54e1e5`; exact-head CI run #42897109443 passed 6/6.
- [x] PR #497 post-merge main CI run #42897359694 passed all six required jobs.
- [ ] Verify final post-#498 main CI run #42899130922 on `ca556e1c3dd109f6ccb0f981b1c57398ff54e1e5`; at this update five jobs passed and unit tests remained in progress.
- [ ] Apply the protocol to each of the 70 review-required archive rows using independently captured evidence and explicit reviewer dispositions. The protocol merge itself does not reconcile any row.
- [ ] Preserve all raw observations; do not repair values, select a provider, ingest data, promote analysis eligibility, or enable M61 without separate evidence and authorization.

The source archive remains structurally auditable but not source-authenticated. Blank volume/traded-value/execution fields remain unavailable, not zero. Review-required rows remain excluded from clean OHLC analysis/backtests until individually reconciled.
