## Latest verified continuation — 2026-11-11 (PR #508 post-merge main CI closeout)

- PR #508, `docs(data): add Nov 4–5 OHLC evidence register`, is merged as `cbbfa4d9622b54be6a42aa5979d12f6fe00856f1`. The merged evidence register is `docs/EGX-2026-11-04-05-OHLC-EVIDENCE-REGISTER.md`; it is documentation-only and does not alter market observations.
- Post-merge main workflow run [#42998190190](https://github.com/palestiny/egx-stock-analyzer/actions/runs/42998190190) completed with conclusion `success` on the exact merge SHA `cbbfa4d9622b54be6a42aa5979d12f6fe00856f1`.
- All six required jobs passed: `unit-tests (3.12)`, `integration-tests (3.12)`, `frontend-tests`, `dependency-audit`, `container-build`, and `daily-history-audit-report`. The Python unit-test job's full step sequence completed successfully, including lint, type checking, and unit tests with coverage. Do not infer a specific test count or coverage percentage from this run's job summary; only the successful job conclusion is confirmed here.
- The read-only daily-history audit artifact is #13845680026 (`egx-daily-history-audit-cbbfa4d9622b54be6a42aa5979d12f6fe00856f1`), 3,523 bytes, not expired at the time of verification.
- Canonical CSV remains unchanged: blob `3c01a843c225d226dc49e7c302220a280cfafb57`, SHA-256 `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`. The 70 review rows, including 51 OHLC geometry exceptions and 19 source/revision conflicts, remain unresolved. The evidence register and forensic triage are not proof of root cause or corrected values.
- DEC-130 remains the historical-data acceptance gate. EGID remains the preferred authorized-source contact route; DataCedar remains an unaccepted candidate for bounded diagnostics only. No provider selection, paid plan, credential use, ingestion, production adapter, canonical CSV edit, analysis-eligibility promotion, or M61 activation is authorized. PR #321 remains Draft/unmerged.

**Authority:** GitHub `main`, merged PR #508, post-merge run #42998190190, unit-test job #130447433869, and audit artifact #13845680026.  
**Last reviewed:** 2026-11-11; main `cbbfa4d9622b54be6a42aa5979d12f6fe00856f1`; post-merge CI 6/6 successful.

---

## Latest verified continuation — 2026-11-11 (PR #506/#504 and current-main CI closeout)

- PR #506, read-only OHLC anomaly forensic triage, is merged as `c531969245591e93b817b542452470a7899dc4b6`. Its post-merge main run [#42988609864](https://github.com/palestiny/egx-stock-analyzer/actions/runs/42988609864) completed successfully with all six jobs.
- PR #504, CI job timeout bounds, is merged. Its exact-head workflow run #42952211069 passed; the change sets explicit per-job timeouts in the test workflow and does not change application behavior or market data.
- Current `main` is `cc08f399779164ad0d40a4375f5ca4e310c88009`. Post-merge main run [#42989380564](https://github.com/palestiny/egx-stock-analyzer/actions/runs/42989380564) completed with conclusion `success` on that exact SHA; all six jobs passed: unit tests (Python 3.12), integration tests (Python 3.12), frontend tests, dependency audit, container build, and daily-history audit report.
- The read-only daily-history audit artifact for this run is #13841695149 (`egx-daily-history-audit-cc08f399779164ad0d40a4375f5ca4e310c88009`).
- The 51 OHLC exceptions and 19 source/revision conflicts remain unresolved; all 70 review rows remain under review. The forensic triage is diagnostic only and does not prove a root cause or corrected value.
- Canonical market-history CSV remains unchanged. No provider selection, paid plan, ingestion, production adapter, source-authenticity promotion, or M61 activation is authorized. EGID remains the preferred authorized-source contact route; DataCedar remains a candidate for bounded diagnostics only. PR #321 remains Draft/unmerged; M61 remains paused pending DEC-130.
  
**Authority:** GitHub `main`, PR #504/#506, post-merge runs #42988609864/#42989380564, and current-main audit artifact.  
**Last reviewed:** 2026-11-11; main `cc08f399779164ad0d40a4375f5ca4e310c88009`; post-merge CI 6/6 successful.

---

## Latest verified continuation — 2026-11-11 (PR #505 merged; post-merge CI passed; OHLC triage recorded)

- PR #505, documentation-only CI closeout, merged as `cd75815cc749674321ffd273dde917dd44040cf8`. Its exact head `c7f3a5bec3012db3b923384b169ab12eb9580685` passed all six required CI jobs in run #42952568050 before merge.
- Post-merge `main` run [#42953081919](https://github.com/palestiny/egx-stock-analyzer/actions/runs/42953081919) completed successfully on the exact merge SHA; all six jobs passed.
- Python 3.12 tests: **1,661 passed, 8 deselected, 1 warning** in 298.49 seconds; coverage **90.58%**, above the 85% minimum. Ruff lint and mypy type-check passed. The warning is Starlette's httpx/TestClient deprecation; Node.js 20 / punycode deprecation notices are maintenance items, not CI failures.
- The post-merge audit artifact is #13825822366. Canonical CSV remains blob `3c01a843c225d226dc49e7c302220a280cfafb57`, SHA-256 `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`, 255 rows, 61 symbols, 31 sessions, 70 review rows, and 51 OHLC exceptions.
- Read-only forensic triage is documented in `docs/OHLC-ANOMALY-FORENSIC-TRIAGE-2026-11-11.md`: 48 open-below-low, 3 open-above-high; 34 equities and 17 indices; 30 exceptions occur on 4–5 November; 22 of 40 comparable opens match the preceding same-symbol close within 1e-8. All flagged rows remain within the Investing.com source family. These correlations are investigation clues, not proof of root cause or corrected values.
- The canonical CSV was not edited. No source was accepted, no ingestion/provider selection or eligibility promotion occurred, and M61 remains paused. PR #321 remains Draft/unmerged pending DEC-130.
  
**Authority:** GitHub PR #505, exact-head run #42952568050, post-merge run #42953081919, artifact #13825822366, and canonical CSV blob above.  
**Last reviewed:** 2026-11-11; main `cd75815cc749674321ffd273dde917dd44040cf8`; post-merge CI 6/6 successful.

---

## Latest verified continuation — 2026-11-11 (PR #503 merge and post-merge CI closeout)

- PR #503, documentation-only historical data source review closeout, merged into `main` as `f9a75726f6ca61924f64886b169830a555b019e6`. Its exact PR head `ff8cdc2d386a0278ddc3eb529ff67d05360bb3dc` passed all six required CI jobs before merge.
- Post-merge workflow run [#42951664652](https://github.com/palestiny/egx-stock-analyzer/actions/runs/42951664652) completed with conclusion `success` on the exact merge SHA `f9a75726f6ca61924f64886b169830a555b019e6`. All six jobs passed.
- Python 3.12 unit tests completed: **1,661 passed, 8 deselected, 1 warning** in 309.44 seconds. Total coverage was **90.58%**, exceeding the configured 85% minimum. Lint and mypy type-check also passed. The observed duration is the test suite's measured runtime, not evidence of a hung runner.
- The sole test warning was Starlette's deprecation notice about using httpx with `starlette.testclient`; it did not fail the job. The logs also reported upstream Node.js 20 deprecation notices for the pinned checkout/setup actions. Track these as maintenance items; do not conflate them with test failures.
- No workflow timeout change was made: this run provides a measured baseline of approximately 5m 9s for pytest, but does not by itself justify an arbitrary timeout value.
- Current `main` is `f9a75726f6ca61924f64886b169830a555b019e6`. PR #321 remains Draft and unmerged; M61 remains blocked pending DEC-130 evidence acceptance. No provider selection, paid plan, ingestion, canonical CSV edit, or analysis-eligibility promotion is authorized.

**Authority:** GitHub PR #503, exact-head CI run #42950852464, post-merge run #42951664652 and its unit-test job logs.  
**Last reviewed:** 2026-11-11; main `f9a75726f6ca61924f64886b169830a555b019e6`; post-merge CI 6/6 successful.

---

## Latest verified continuation — 2026-11-11 (DataCedar candidate review and post-merge CI closeout)

- PR #502, **DataCedar EGX source candidate review**, merged into `main` as `33abc76c322f90af5a5ff583dd0a956ee1aabea7`. Its exact PR head `783c34ae092a96ca651985f0837e7d1a40da2481` passed all six required CI jobs in run #42949076002 before merge.
- Post-merge workflow run #42949638348 completed successfully on that exact merge commit. All six jobs passed: dependency audit, integration tests (Python 3.12), container build, frontend tests, daily-history audit report, and unit tests (Python 3.12). The unit-test job completed; the workflow conclusion is `success`. This closes the previously pending post-merge CI check.
- PR #502 adds `docs/M61-DATACEDAR-EGX-SOURCE-CANDIDATE-REVIEW.md` and `docs/M61-DATACEDAR-LIVE-DOCS-RECHECK-2026-11-11.md`. DataCedar remains a candidate for a bounded recent-history diagnostic only, not an accepted M61 source. Explorer's documented one-year daily-history limit cannot meet the 2021–2025 evaluation period plus 252-session warm-up. The pricing matrix's raw-close-only statement conflicts with the API adjustment parameters and requires written clarification.
- No DataCedar API key was used; no authenticated request, price-row download, or persistent market-data extraction was performed. No plan was purchased. Provider selection, ingestion, production adapter, canonical CSV edits, analysis eligibility promotion, and M61 activation remain unauthorized.
- The latest read-only daily-history audit artifact for this main commit is artifact #13824232626. The canonical market-history CSV was not modified by PR #502. Existing 70-row review inventory and 51 OHLC exceptions remain unresolved; structural validity is not source authentication.
- Current `main` remains `33abc76c322f90af5a5ff583dd0a956ee1aabea7`. PR #321 remains the only pre-existing product/M61 PR; it is Draft and unmerged, and its M61 Strategy v0 COMI test remains blocked pending DEC-130 evidence acceptance. PR #503 is this documentation-only closeout PR.

**Authority:** GitHub `main`, PR #502, exact-head run #42949076002, post-merge run #42949638348, and artifact #13824232626.  
**Last reviewed:** 2026-11-11; main `33abc76c322f90af5a5ff583dd0a956ee1aabea7`; post-merge CI 6/6 successful.

---

## Latest verified continuation — 2026-11-11 (retrieval precision and row-level review inventory)

- **Authorized source route identified for follow-up:** EGID's own site states that it is a fully owned EGX subsidiary and the sole authorized EGX market-data provider, and describes its market-data feed service. Its contact page lists `marketdata@egidegypt.com`. A 2023 Arab Finance interview independently describes EGID as EGX's sole distributor and says other data vendors obtain data from EGID. This makes EGID the preferred first commercial/technical contact for an authorized sample; it does **not** mean a sample, contract, historical OHLC fields, or redistribution rights have been verified. References: https://egidegypt.com/ ; https://egidegypt.com/contact-us.html ; https://arabfinance.com/en/News/newdetails/5055
- PR #500 merged into `main` as `386b710cb74e34697ceae7d5a883067d7f1c4699`. Exact PR head `a747e775e2acf239f4b07b1ebf7cf9f445bf1369` passed all six required CI jobs in run #42946596578 before merge.
- The Python unit-test job completed with **1,661 passed, 8 deselected, 1 warning** in 308.25 seconds. Total measured coverage was **90.58%**, above the configured 85% threshold. Lint, type checking, frontend tests/build, deterministic integration tests, dependency audit, container build, and the read-only daily-history audit all passed on the exact PR head.
- PR #500 improves provenance reporting only: retrieval metadata is counted as timezone-aware timestamps versus date-only values, and date-only rows are listed without inventing a time or timezone. It does not authenticate the provider or promote analysis eligibility.
- The canonical CSV remains Git blob `3c01a843c225d226dc49e7c302220a280cfafb57`, SHA-256 `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`, 101,315 bytes. The exact read-only audit artifact reports 255 rows, 61 symbols, 31 sessions, 51 OHLC geometry exceptions, 70 review-labelled rows, 0 malformed rows, and 0 duplicate keys.
- The report distinguishes 48 open-below-low cases and 3 open-above-high cases. It records 233 timezone-aware retrieval timestamps and 22 date-only values (all from the initial EGAL seed), 255 missing traded-value fields, 255 missing execution-count fields, and 23 missing volume fields.
- PR #501 merged into `main` as `6d0cbd50c937f9de584ae0e0186e130eacc1e399`. Exact PR head `b9f4ec62ef272ee2f31e41bf09edbe632436e26d` passed all six CI jobs in run #42947547289. Python unit tests: 1,661 passed, 8 deselected, 1 warning; coverage 90.58% against an 85% threshold. The merged `docs/EGX-DAILY-HISTORY-REVIEW-INVENTORY-2026-11-11.md` records all 70 review rows with CSV row number, original OHLC, retrieval metadata, source URL, 22 date-only rows, and all 19 original source-conflict notes.
- No canonical CSV values were repaired, replaced, or deleted. The 185 structural candidates remain unauthenticated. No provider was selected, no ingestion was enabled, and M61 remains paused.

**Authority:** GitHub `main`, PRs #500/#501, exact-head runs #42946596578/#42947547289, and audit artifact #13823266584.  
**Last reviewed:** 2026-11-11; main `6d0cbd50c937f9de584ae0e0186e130eacc1e399`.

---

## Latest verified continuation — 2026-11-10 (source-reconciliation gate and docs consolidation)

- PR #490 (daily-history audit/classification/baseline documentation) and PR #489 (archive snapshot statistics and acceptance-gap documentation) are both merged. #490 was merged first; #489 followed, preserving the unique archive statistics/checklist rather than discarding overlapping documentation.
- Current `main` is `139386c682fa9ae129b35ae3f9237dd49c13894a`, with #489 as its latest commit.
- Post-merge main workflow run #42889360953 targets this exact main SHA. At this update, frontend tests, dependency audit, container build, and integration tests passed; `unit-tests (3.12)` remained in progress at `Run unit tests with coverage report`. Do not mark this main run green until that job completes.
- A separate read-only inspection of the canonical CSV at Git blob `3c01a843c225d226dc49e7c302220a280cfafb57` reproduced the committed audit's principal structural findings: 255 rows, 61 symbols, 31 dates (2026-09-28 through 2026-11-10), no malformed rows, no duplicate keys, 51 OHLC geometry exceptions, and 70 review-labelled rows. This was an independent JavaScript reimplementation of the checks, **not execution of the committed Python CLI** and not a persisted official audit report. The official command remains:
  `python -m tools.egx_daily_history_audit --input data/market_history/egx_daily_history.csv --output reports/egx-daily-history-audit.json`
- The eight 2026-11-10 OHLC review rows remain `HDBK`, `ORAS`, `PHDC`, `RAYA`, `TMGH`, `EGX30`, `EGX70EWI`, and `EGX100EWI`. No CSV values were repaired, replaced, or deleted.
- The 255-row archive has blank `traded_value_egp` and `executions_count` in all rows; volume is blank in 23 rows. These fields remain unknown, not zero. Structural candidates remain unauthenticated and are not automatically approved for trading/backtests.

### Source-reconciliation gate (research only; no provider selected)

Potential independent acquisition/verification routes identified for evaluation:

- **EGX / official exchange-origin evidence:** remains the preferred primary operational evidence for exchange-reported values and coverage. The current research did not establish a publicly accessible, machine-readable historical OHLC endpoint or prove that a particular public bulletin resolves the eight flagged bars. This is an open evidence gap, not a claim that no such service exists.
- **ICE Data Services — EGX product:** its public developer catalogue describes EGX coverage and historical/end-of-day data, including daily frequency and history beginning February 2012. It is a commercial candidate; availability, exact OHLC fields, corrections, symbology, redistribution rights, sample quality, and price must be confirmed directly. Reference: https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx
- **DataCedar — EGX API:** its public page claims daily history and an API for EGX listings, with a free one-year daily window and paid longer history. Treat all coverage, accuracy, continuity, adjustment, and licensing claims as vendor claims pending a sample and written terms. Reference: https://datacedar.com/markets/egypt
- **EGX.news data service:** its public page advertises historical daily bars and intraday CSV datasets for EGX instruments. It is a commercial candidate only; verify operator identity, source lineage, coverage, sample rows, correction policy, and reuse rights before relying on it. Reference: https://www.egx.news/en/our-data
- **Investing.com:** keep as a secondary comparison source, not as the sole independent authority for reconciling rows originally collected from Investing.com. A same-provider page showing the same anomalous bar is not independent confirmation.

Acceptance requirements before a provider can be promoted:

1. Obtain a dated sample for at least the eight flagged instruments/session rows plus several unflagged control rows and representative index rows.
2. Preserve raw payload/file, retrieval timestamp, provider identity, exact endpoint/page, request parameters, timezone, units, price type, and cryptographic digest.
3. Compare OHLCV field-by-field without overwriting the canonical archive; distinguish provider revision, locale/page rendering conflict, corporate-action adjustment, symbol mapping, and unresolved discrepancy.
4. Confirm exchange-session coverage, delisted/suspended instruments, missing sessions, symbol changes, index methodology/units, and whether bars are adjusted or unadjusted.
5. Obtain written licensing/retention/redistribution terms and correction/revision semantics. A matching hash proves byte integrity only, not source authenticity.
6. Require explicit reviewer disposition for each discrepancy. Only an approved, auditable reconciliation may create a corrected successor observation; retain the original source record and its history.
7. Keep all review rows excluded from clean OHLC analysis/backtests until the relevant evidence and acceptance checks pass.

**Current decision:** no provider selected; no new data ingestion, source substitution, automatic correction, analysis eligibility promotion, M61 activation, or trading behavior is authorized by this research. M61 remains paused.

**Authority:** GitHub `main` and exact-head workflow evidence.  
**Last reviewed:** 2026-11-10; main `139386c682fa9ae129b35ae3f9237dd49c13894a`; post-merge CI run #42889360953 has four required jobs passed and unit tests pending.

---

## Latest verified continuation — 2026-11-10 (daily-history audit and snapshot comparison)

- PR #487 merged into `main` as `5c303ff15b97357d7ab086c921061644265ff309`. It adds a read-only canonical daily-history CSV audit covering schema/row shape, types, provenance shape, quality labels, duplicate keys, OHLC geometry, latest-session summary, byte count, and SHA-256. It does not fetch or authenticate source pages, infer EGX sessions/coverage, repair values, or mutate the source CSV.
- PR #488 merged into `main` as `bdef388e06b854324124f5f61099f0f5717e54e6`. Exact PR head `fe9ba50a823f46e6965aa180d7abb4d488a17df3` passed all five required CI jobs in run #42887122981 before squash merge.
- PR #488 adds mutually exclusive row classifications: `clean_ohlc_candidates` (structural candidates only), `review_required`, and `rejected_or_invalid`. Every row participating in a duplicate `(session_date, symbol)` key is rejected from analysis eligibility. It also adds optional read-only `--baseline` comparison for added/removed/changed keys and fields; duplicate keys make the comparison partial, and malformed row shapes prevent comparison.
- Structural candidates are explicitly `STRUCTURAL_CANDIDATE_ONLY_NOT_SOURCE_AUTHENTICATED`; they are not source-authenticated bars or automatic approval for trading/backtests. Removed rows are reported as differences, not automatically treated as errors.
- Post-merge main CI run #42888113689 on `bdef388e06b854324124f5f61099f0f5717e54e6` was in progress at the time of this documentation update. Do not mark post-merge CI green until all five jobs complete.
- No source CSV values were edited, repaired, inferred, or deleted by PRs #487/#488. Missing volume/traded-value/execution metrics remain unavailable, not zero. Source authenticity and independent source reconciliation remain separate gaps.

**Authority:** GitHub `main` + current open pull requests  
**Last reviewed:** 2026-11-10 (`main` at `bdef388e06b854324124f5f61099f0f5717e54e6`; PR #488 exact-head CI passed 5/5 before merge; post-merge run #42888113689 pending.)

---

# EGX Stock Analyzer — Current State

## Latest verified continuation — 2026-11-10 (artifact inventory and SQLite WAL verification)

- PR #483 merged into `main` as `975409d39b2e80ba00e78a96dfda144b21ba802c`. Its exact head `ad0d3ff31a78a1da0c42ed9df7faeb3b70814c1d` passed all five required CI jobs before squash merge. It adds a read-only calendar artifact inventory that classifies referenced-valid, orphaned, missing, integrity-failure, invalid-reference, and invalid-storage-entry findings. It does not repair or delete anything.
- PR #484 merged into `main` as `9e120eec682d155204c64bce150f3aee9b6cbdcf`. Exact PR head `b4955c3e745593c68c200a1b2038fe9de95a7a2d` passed all five required CI jobs in run #42880047021. The added regression test verifies that a read-only inventory sees committed ARCHIVED evidence in SQLite WAL mode while the writer connection remains open, without changing the database file or WAL bytes. Normal shared-memory WAL reader coordination is not asserted as immutable.
- Post-merge main run #42879830031 on PR #483 merge commit `975409d...` completed successfully with all five required jobs. Post-merge CI for PR #484 merge commit `9e120eec...` is run #42881049920 and was in progress at the time of this update; do not mark it green until all five jobs finish.
- PR #476 (original daily-history branch) was closed unmerged as superseded by PR #486. PR #486 reapplies the same two reviewed data-file changes on current `main` after confirming both archive files were unchanged from the original PR base. It preserves 23 Investing.com daily rows (17 equities, six indices), 255 total records, and eight explicit OHLC-review flags. Fresh exact-head CI is required; no application-database ingestion or M61/backtest result is claimed.
- PR #321 remains Draft and M61 remains paused by explicit owner request.
- Calendar activation, lifecycle monitoring, freshness enforcement, provider-finality behavior, and M61 remain disabled/paused. No production database/storage inventory, source-authenticity proof, legal retention acceptance, backup/restore test, multi-node acceptance, or orphan cleanup has been performed. The inventory implementation is read-only and must not be described as a production scan.

**Authority:** GitHub `main` + current open pull requests  
**Last reviewed:** 2026-11-10 (`main` at `9e120eec682d155204c64bce150f3aee9b6cbdcf`; PR #484 merged after all five exact-head CI jobs passed.)

---

## Latest working continuation — 2026-11-10 (calendar artifact verification)

- PR #477 is merged into `main` as `cea2b8e8620a2ccb96693a20bd00ccc5ca900e63`; its post-merge Main workflow run #42868953457 completed successfully.
- PR #478 is merged into `main` as `622783b7ade6e23be604d6c07d4c5bc83e638b90`; all five required CI jobs passed on exact PR head `dde6315975732b89559aee2fecdbb507b016b86a` in run #42869283451.
- PR #479 is merged into `main` as `d1114c1a020825fb1e8477605c5c18c14bf475e6`; exact PR head `9cd81700201c38ceeb34b50ffad18e9565b7f959` passed all five required jobs in run #42873143036 before merge.
- Post-merge main CI run #42874061006 completed successfully; all five required jobs passed.
- PR #480 (`docs/reconcile-calendar-artifact-merge-state`) merged into `main` as `c475b076c82c7c91a5671a91baf18a47afad105f`. Its exact head `2b8a40e8917ff06772f501a95b0ec248d8a5e642` passed all five required jobs in run #42874761255 before merge.
- Artifact storage/upload/publication verification is implemented, but source authenticity, legal retention permission, backup/restore, multi-node behavior, and orphan reconciliation remain open acceptance gates. No automatic deletion is enabled.
- Compose config stores artifacts under `/data/calendar-artifacts` on the existing persistent `egx-data` volume; default upload limit is 20 MiB and can be configured. Non-Compose configurations keep artifact storage disabled unless explicitly configured.
- The API returns a computed SHA-256 and opaque storage reference after successful write/read-back verification. Publication rejects missing or tampered archived artifacts; `EXTERNAL_ONLY` remains supported with its explicit non-retention reason.
- New tests cover authenticated upload, successful archived publication, missing/tampered artifact rejection, direct Unit-of-Work rejection when no verifier is configured, content-type enforcement, upload size limits, and artifact storage configuration.
- Remaining gaps: source authenticity is not established; lawful retention/reuse rights, backup/restore acceptance, orphaned uploads after failed publication, and deployment storage operations still need explicit controls. This work does not equate a matching digest with an authentic EGX/FRA source.
- Calendar activation remains paused. No lifecycle monitoring, freshness enforcement, provider-finality behavior, or M61 work is introduced.

## Latest verified continuation — 2026-11-10 (PR #475 merged)

- PR #475 merged into `main` as `04f4dce6c2d2e5b0f0a285aa4eb3534c8af55f22`. Exact PR head `6f53e65bdd8615be92c99fc6fcf42308b36624dd` passed all five required CI jobs in run #42866088424.
- Post-merge main run #42867152618: frontend, dependency audit, container build, and integration tests passed; unit tests with coverage were still running at this snapshot. Post-merge CI is not yet claimed green.
- D1–D4 enforcement is merged: typed A/A-R/B/C evidence, A-R restricted to `FRA_REGULATORY`, hybrid retention metadata, strict evidence-gated publication, claim-specific daily evidence, explicit OPEN confirmation, and exceptional-hours marker/evidence validation.
- Limits: publisher identity and digest remain operator-declared; artifact bytes are not independently authenticated or verified; lawful retention and actual artifact retrieval remain deployment/operational tasks. `ARCHIVED` metadata alone does not prove bytes were archived.
- Publication is distinct from activation. No calendar is activated; lifecycle monitoring, freshness enforcement, provider completed-bar attestation, cursor-derived activation coverage, and M61 remain disabled/blocked/paused. PR #321 remains Draft.

## Latest verified continuation — 2026-11-10

- PR #471 merged as `bad0f1b134586fd6ffe32ebf09352c31a5fb445f`. Its exact head `e57b9ca301be3541bd47cadfdc1a597dd7ad60e2` passed all five required CI jobs in runs #42854454025 and #42855087258. It implements atomic calendar publication: calendar version, per-day immutable evidence, explicit links, and validation share one SQLite `BEGIN IMMEDIATE` transaction.
- PR #472 merged as `b2fa65e4ffa68cb80c27bad6e69da45e03fe126a`. Its exact head `71ebdb22c5f3dd517ef4c896a6dfc8643e083dc6` passed all five CI jobs in run #42667845797. The canonical archive now contains 232 records across 19 columns, including 23 rows for 2026-11-09 (17 equities and 6 indices). Independent structural verification found no duplicate `(session_date, symbol)` keys and complete required provenance fields on all 23 new rows.
- Four 2026-11-09 index rows remain flagged `ohlc_inconsistency_review`; PHDC and EGX30 remain flagged for localized-source conflicts, and an EGX100EWI discrepancy is retained in notes. Raw values were preserved; flagged rows are not clean OHLC evidence. This archive update does not establish full-market coverage, application-database ingestion, or production-feed readiness.
- Current `main` is `b2fa65e4ffa68cb80c27bad6e69da45e03fe126a`. Post-merge main CI run #42855711113 completed successfully with all five required jobs. The earlier main run #42855271889 was cancelled by the subsequent #472 push and is not counted as a pass.
- PR #474's evidence acceptance proposal was accepted by the owner. PR #475 is merged as `04f4dce`; its exact PR head passed all five required jobs in run #42866088424. Post-merge run #42867152618 is pending its unit-test/coverage job at this snapshot.
- Merged PR #475 adds typed source classes, scope/effective-date/retrieval metadata, hybrid artifact-retention metadata, Class A-only primary evidence checks, explicit OPEN confirmation, and exceptional-hours marker/evidence enforcement. This is not source authentication: declared publisher and artifact digest are operator-supplied; independent artifact verification is still open.
- Calendar activation, lifecycle monitoring, freshness enforcement, provider completed-bar attestation, and M61 remain disabled/blocked/paused. PR #321 remains Draft.


**Authority:** GitHub `main` + current open pull requests  
**Last reviewed:** 2026-11-10 (main at `c475b076c82c7c91a5671a91baf18a47afad105f`; PR #480 merged after all five exact-head CI jobs passed in run #42874761255. Main run #42874061006 also passed all five required jobs.)
**Repository:** palestiny/egx-stock-analyzer


### Latest verified continuation — 2026-11-10 (calendar evidence acceptance)

- PR #465 merged the immutable per-day calendar evidence registry. Records are append-only and SHA-256 verified; corrections use explicit supersession and reason. PR #471's atomic publication enforcement is merged and its exact-head CI passed. The registry does not prove source authenticity.
- PR #466 merged individual operator grants, append-only grant/revoke/bootstrap audit, durable-credential-aware permission resolution, last-operator protection, and trusted local first-operator bootstrap.
- PR #467 merged as `03d3969e19e7b73beb3b8427afb5328183d1553e`. Its exact head `2d2cdac405698d7e783a838037a588852a5cc5b2` passed all five required CI jobs before squash merge. It composes persistent calendar storage and the authenticated API, requiring an active individual operator user plus durable credential; the legacy shared operator token is rejected for calendar administration.
- PR #462 is closed unmerged as superseded by #467.
- Calendar publication remains separate from activation. PR #471's atomic per-day evidence coverage/linkage and conflict validation are merged. D1–D4 source-class acceptance, hybrid retention metadata, strict publication, claim-specific evidence matrix, exceptional-hours marker, legacy migration, and FRA-only regulatory scope are merged in PR #475 (`04f4dce`). Exact PR-head CI passed in run #42866088424; post-merge main CI run #42867152618 was pending its unit-test/coverage job at this snapshot. Artifact authenticity/byte verification, lawful retention, operational bootstrap/coverage horizon, cursor-derived validation, lifecycle integration, and provider completed-bar attestation remain open. No lifecycle monitoring or freshness enforcement is enabled.
- M61 remains paused by explicit owner request; PR #321 remains Draft and untouched.

### Calendar publication atomicity — implemented and merged (PR #471)

- The calendar-specific SQLite Unit of Work owns one `BEGIN IMMEDIATE` transaction for immutable calendar-version persistence, evidence persistence, per-day links, and policy validation.
- Rollback/isolation tests and production runtime composition are merged; PR #471 passed all five exact-head CI jobs.
- Publication remains distinct from activation. The D1–D4 source acceptance and claim-specific evidence enforcement are the separate PR #475 workstream.
- Calendar activation, lifecycle monitoring, Crash Radar freshness enforcement, and M61 remain disabled/paused.

## 1. Where We Are

### Latest verified continuation — 2026-11-09 (session calendar)

- PR #459 merged the fail-closed EGX session-calendar domain model: explicit contiguous daily records, Africa/Cairo wall-clock times, five explicit day states, and completed-session checks requiring a passed close-confirmation timestamp. No weekends, holidays, or session hours are inferred.
- PR #460 merged immutable SQLite calendar-version persistence, SHA-256 verification, a single active-version pointer, and append-only activation/deactivation/rollback audit events. No calendar has been published or activated.
- PR #467 is merged and provides authenticated calendar publication/read endpoints plus persistent runtime composition. Publication does not activate a version; no HTTP activation/deactivation/rollback endpoints are exposed. Calendar administration requires an individually attributable active operator credential.
- The session-calendar activation gate remains GAP: a durable lifecycle cursor, bootstrap policy, cursor-derived coverage validation, evidence acceptance/publication enforcement, and provider-completed-bar attestation remain unresolved. Individual operator identity is implemented for calendar administration. The calendar is not connected to lifecycle scheduling or freshness evaluation; automatic lifecycle monitoring remains disabled.
- Source review found conflicting secondary reports for EGX session boundaries and holiday dates; no complete authoritative machine-readable EGX calendar was verified. Do not import national holidays or third-party calendar rows as EGX truth.
- PR #467 exact-head CI run #42633962405 passed all five jobs: unit tests with coverage, integration tests, frontend tests/build, dependency audit, and container build. It was merged only after all exact-head checks passed.
- M61 remains paused by explicit owner request; PR #321 remains Draft and untouched.

### Prior verified continuation — 2026-11-09

- PR #455 merged the owner-accepted lifecycle monitoring policy reconciliation. The implementation gate remains open: the lifecycle orchestrator is still not wired to persisted analysis observations, and provider-specific completed-bar/freshness evidence is not verified.
- PR #456 merged the operator-configured, versioned Crash Radar universe. This identifies the configured symbol set but does not establish full EGX coverage or completed-session freshness.
- PR #457 merged the 2026-11-08 archive collection: 23 rows (17 equities, 6 indices), bringing the canonical CSV to 209 rows. Structural recheck on the exact PR head found 19 columns, 209 data rows, 23 rows for 2026-11-08, 17 equities, 6 indices, no duplicate (session_date, symbol) keys, and complete required provenance fields on the new rows.
- The two 2026-11-08 index bars (EGX30, EGX30CAP) remain explicitly flagged ohlc_inconsistency_review; ORAS and HELI remain source_conflict_review. The source values were preserved and must not be silently repaired or treated as clean OHLC. The archive is partial and does not establish application-database ingestion or production-feed readiness.
- PR #457 exact-head GitHub Actions run #4842 completed successfully. The squash merge commit is 7a65ce103b271457c9d609341ea1ffab4934ec1b; GitHub returned no workflow run associated with that merge commit at review time, so post-merge CI is not claimed.
- PR #321 remains Draft and M61 remains paused by explicit owner request. Do not use exploratory COMI results as accepted strategy-performance evidence.
- Next non-M61 priority remains Crash Radar freshness/coverage hardening without changing the 50/40/10 formula. DEC-135 requires freshness to be evaluated against completed EGX sessions; the official session/holiday calendar and authoritative completion source must be verified before enforcement. No elapsed-wall-clock approximation is allowed.

### Latest verified continuation — 2026-11-07

- PR #450 merged atomic lifecycle persistence: history, optional market-proxy outcome, and durable alert intent share one SQLite connection and transaction.
- PR #452 merged rollback failpoint tests after history, outcome, and outbox writes.
- PR #454 merged restart-recovery and transport-boundary tests. A pending event is delivered after dispatcher reconstruction and is not redelivered by a second dispatcher. A separate SQLite connection can observe committed lifecycle rows before the Telegram transport is invoked.
- PR #454 exact-head CI passed all five jobs. Post-merge `main` is `ba03d41d5741856e5cb3ab892172633058b3ffd2`; workflow run #42399538146 completed successfully with all five jobs.
- Code-path inspection confirms `GenerateSignal` reads the latest persisted analysis result, while `PublishSignalOpportunity` writes publication history/outbox. `SignalLifecycleOrchestrator` is constructed in infrastructure runtime but is not called by those publication or analysis-persistence paths. Automatic observation integration remains unimplemented.
- DEC-138 and DEC-139 now settle the product rules for completed-daily-OHLC crossing, session calendar/timing, provider completion requirements, freshness suppression, OHLC validation, entry/performance separation, 20-eligible-session Swing expiry, immutable revisions, append-only corrections, idempotent replay, and chronological recovery. Provider-specific completion/freshness evidence and the end-to-end runtime integration remain unverified/unimplemented; no automatic monitoring claim is authorized.
- M61 remains paused; PR #321 remains Draft.


### Latest repository updates — 2026-10-31

- PR #420 merged offline structural/provenance validation for the canonical daily archive. It checks the schema, ISO session dates, normalized symbols, unique `(session_date, symbol)` keys, positive finite OHLC, explicitly flagged inconsistencies, optional numeric fields, and source/quality metadata. This does not establish source-price accuracy, full EGX coverage, database ingestion, or profitability.
- PR #421 merged the 2026-10-29 archive update. The canonical CSV contains 45 rows: 22 EGAL seed rows plus 23 rows for 19 equities and 4 indices. It has 41 equity rows and 4 index rows, no duplicate keys, two explicitly flagged OHLC inconsistencies (MICH and FAIT), and one unresolved EGAL source-revision conflict for 2026-10-28. The archive is a partial, source-attributed research snapshot, not a verified production feed.
- PR #435 aligned recurring analysis with the EGX Sunday–Thursday trading week. Friday and Saturday are skipped; official exchange holidays are not modeled by this rule.
- PR #436 recorded Yahoo Finance/yfinance commercial-use and redistribution restrictions as a blocker. Do not expose Yahoo-derived data to paid/subscriber users until the applicable terms and written permissions are verified.
- PR #437 documented EGID and DirectFN as provider candidates to investigate; neither provider is approved or integrated.
- PR #439 added finite-number and timezone-aware timestamp invariants to signal domain models.
- PR #441 exposes signal-source and outcome-source timestamps in session-opportunity API responses and immutable report snapshots. These are provenance timestamps, not freshness classifications.
- PR #443 corrected terminal outcome provenance so the outcome carries the actual market observation's source-data timestamp, not the original signal-generation timestamp.
- PR #445 merged the session-ledger publication-scope fix. Reports now exclude CREATED-only signals, use the first PUBLISHED/PUBLISHED_VERSION event as the original opportunity snapshot, and assign the report session by publication time in the configured exchange timezone. Exact-head CI run #4777 passed all five jobs: 1,469 tests passed, 8 deselected, 90.73% coverage. Merge commit: `d86f418ea927c11755c821a6c1c44c736023ddca`. Post-merge main CI has not yet been verified.
- PR #444 remains open and documents the missing end-to-end lifecycle observation path and the decisions required before connecting market observations to target/invalidation transitions. Its documentation branch is being refreshed after PR #445.
- Current `main` post-merge CI for PR #443 passed all five jobs in run #41206028998. Do not infer the post-merge CI result for PR #445 from its successful PR-head run.
- M61 remains paused by owner request. PR #321 is still a draft and is not accepted strategy-performance evidence.

**Execution status (2026-10-28):** M61 is paused; continue non-M61 work only until the owner explicitly resumes M61. This is a priority change, not a change to the historical-data acceptance criteria.

The M61 — Backtesting & Strategy Validation workstream is **paused by explicit owner request on 2026-10-28**. The deterministic simulator and dataset software boundaries exist, but real historical evidence remains unaccepted and M61 is not complete. Current execution priority is to close non-M61 product and engineering gaps, including Crash Radar explainability, technical/news integration verification, Telegram/session-report workflows, and engineering quality.

### Latest verified non-M61 progress — 2026-10-28

- PR #384 merged architecture-boundary regression tests; all five CI jobs passed before merge.
- PR #385 and PR #388 reconciled the explicit M61 pause across the roadmap and current-state documentation. PR #390 updated the README to describe current capabilities and limitations.
- PR #389 fixed RSS 1.0/RDF namespace-qualified field and Dublin Core date extraction. All five CI jobs passed before merge; merge commit: 7268aa3221f30755d401c76469d816b77a999e74.
- PR #387 merged explainable Crash Radar components and per-symbol snapshot-date display. The 2026-10-28 CI run #4519 passed all five jobs: unit tests, deterministic integration tests, frontend tests/build, dependency audit, and container build. Merge commit: 1eb8e1faf598d27c69295b9a7aca31c24ff2d389.
- The Crash Radar change preserves the existing 50/40/10 heuristic and exposes component counts/shares/weighted points; it does not define a freshness threshold or change signal ranking.

Remaining non-M61 acceptance gaps:
1. Crash Radar still needs owner-approved universe, freshness-warning/enforcement, minimum-coverage, persistence/retention, and notification policies before score suppression or alerts can be implemented.
2. News ingestion supports explicit operator-configured RSS/Atom feeds, but no verified official EGX feed and source-reuse terms are accepted/configured.
3. Session reports remain manual point-in-time snapshots; automatic session finalization/scheduling and Telegram report distribution are not complete.
4. Subscription pricing/payment gateway and remaining opportunity-lifecycle semantics still require the open DEC-134 product decisions.
5. M61 remains paused and incomplete; no strategy-profitability claim is authorized.

### Latest verified progress — 2026-10-20

- PR #322 merged at `24a8193199f821e0fe4906dfdfcaa603ceb1ae73`; Strategy v0 reports profit factor, trade-sequence maximum drawdown, average winning/losing returns, and longest consecutive win/loss streaks. This is not daily portfolio drawdown.
- PR #325 merged at `1c908b0456f02dccbdc75ab9eeb5206bad30c15d`; the dashboard/API now provide a pre-breakout momentum-volume watchlist using saved analysis snapshots. It is a watchlist, not a buy signal, and snapshots may be stale.
- PR #322 CI run #4068 and PR #325 CI run #4113 were reported successful across five jobs before merge. This is implementation validation only; no strategy-performance claim follows.
- Current M61 blocker remains real, legally retainable market history and point-in-time financial evidence for the required ten-symbol cohort. No immutable accepted dataset or valid strategy-performance conclusion is claimed.

M56 — Analysis Run & Snapshot Retention and Deletion is complete.

M57 — Physical Purge is complete and hardened through PR #155.

M58 — Automatic Analysis Retention is complete through PR #157 at `f2294c34a10c994545e24175c956ee8524170142`.

M59 — Controlled Maintenance Trigger is complete through PR #159, merged at `c5c6c258508a60ac5872f4f4504fe55d440af30c`. The implementation head `9029a942c2705080f400b1b6ba7e993bd32c9ee9` passed GitHub Actions Tests Run #2687.

## 2. Authority Order

When information conflicts, use this order:

1. GitHub `main`
2. Open pull requests and their actual heads/bases
3. `docs/ROADMAP.md`
4. Current design-gate documents
5. `docs/DECISION_LOG.md`
6. Other foundational documentation
7. Conversation history / memory

Conversation history is context, not project state.

## 3. M56 Completion

M56 established the accepted logical-deletion lifecycle for AnalysisRun and AnalysisResultRecord historical snapshots.

Validated behavior includes owner-aware logical deletion, consistent read-side visibility, active-run protection, idempotency, correlated run/snapshot hiding, and SQLite-transactional lifecycle mutation/audit coordination.

Physical purge and automatic retention were intentionally separated from M56.

## 4. M57 Completion

M57 — Physical Purge is complete within the accepted design boundary.

Design gate:

`docs/DEC-120-M57-PHYSICAL-PURGE-DESIGN-GATE.md`

Status: **Accepted**.

Implementation was merged through PR #151 at `3b20199581e2a6f313e3f83ca4c65780d5a9dbba`.

The implementation provides operator-only physical purge, explicit or deterministic bounded selection, stable-ID ordering, one SQLite transaction per lifecycle unit, fail-stop handling, restart-safe idempotency, management-audit recording, dry-run support, correlated lifecycle cleanup, runless snapshot purge, and visible/active protection.

The implementation head `95abdc209e779f184cc67da49f60c97a535f109a` passed GitHub Actions Tests Run #2536.

### M57 Hardening

PR #155 was merged as `ad10be12990abdfac56ec1459b163929b23c83c6`.

It synchronized the M57 completion state and hardened:

- operation identity propagation;
- dry-run audit recording;
- global deterministic candidate ordering;
- destructive row-count checks;
- current-state / README / engineering documentation.

GitHub Actions Tests Run #2571 passed for the hardening head.

## 5. M58 Completion

M58 — Automatic Analysis Retention is **complete — implementation merged and verified**.

Design document:

`docs/DEC-122-M58-AUTOMATIC-RETENTION-DESIGN-GATE.md`

Status: **Accepted — implementation merged**.

M58 evaluates retention policy and triggering while reusing the existing M57 purge boundary rather than creating another destructive deletion path.

Accepted policy decisions:

1. Automatic retention is required.
2. Retention clock starts at logical deletion time (`deleted_at`).
3. Scope covers deleted runs/correlated lifecycle data and runless deleted snapshots, subject to M57 eligibility.
4. Preservation duration is configurable and system/operator-owned; the accepted duration is **30 days** from `deleted_at`.
5. Policy changes apply to current persisted state when retention executes.
6. Execution is controlled maintenance/scheduler-driven, not application-startup-driven; concrete trigger mapping remains an implementation-mapping task.
7. Every invocation is hard-bounded.
8. Dry-run/preview is non-destructive.
9. Automatic retention has a distinct audit operation identity.
10. Automatic retention is disabled by default and requires explicit enablement.
11. Invalid/unavailable configuration fails safe with no deletion.

Retention eligibility boundary:

- `deleted_at + 30 days <= now`.

Implementation mapping is composed in the application/infrastructure runtime, disabled by default, and not invoked from application startup. Controlled maintenance/scheduler invocation remains the trigger boundary. PR #157 is merged; no startup hook or background worker was introduced. M57 explicit privileged purge remains independently usable and authoritative for physical-reclamation semantics; M58 automatic retention reuses it.

## 6. Session Start Rule

Before project work:

1. Fetch current `main`.
2. Read the current roadmap.
3. Inspect open PRs.
4. Identify the latest proposed/accepted design gate.
5. Verify the implementation branch before changing code.
6. State the current milestone and objective from GitHub.
7. Ignore superseded milestone context.

## 7. Cleanup Rule

Historical branches and old milestone documents are history, not current execution state. Old branches should only be deleted after verifying they are no longer needed.

The repository must remain understandable without the conversation.


## 7. M59 Completion

M59 — Controlled Maintenance Trigger is **complete — implementation merged and CI validated**.

Design document:

`docs/DEC-123-M59-CONTROLLED-MAINTENANCE-TRIGGER-DESIGN-GATE.md`

Accepted boundary:

```
External scheduler
      ↓
Maintenance command
      ↓
AutomaticAnalysisRetention
      ↓
PurgeAnalysisLifecycle
      ↓
SQLite lifecycle transaction
```

The repository now provides a controlled maintenance command with explicit disabled/completed/failed outcomes, dry-run support, bounded execution through M58/M57, operator identity, and process exit semantics. No OS/container scheduler or application background worker was added.

PR #159 was merged into `main` as `c5c6c258508a60ac5872f4f4504fe55d440af30c`. GitHub Actions Tests Run #2687 passed on implementation head `9029a942c2705080f400b1b6ba7e993bd32c9ee9`.

## 8. M60 Completion

M60 — Production Maintenance Scheduling is **complete — deployment mapping merged**.

DEC-124 is accepted. PR #162 was merged into `main` at `4fbf799f6262c4179946835ef4eae47cf8ecb6f1` after implementation-head CI passed in Tests Run #2709.

The repository provides the Windows Task Scheduler wrapper, registration script, and removal script under `deploy/windows/`. The accepted contract is daily at 03:30 local host time, IgnoreNew overlap handling, a 30-minute execution ceiling, and up to 3 scheduler restarts with 10-minute spacing.

The Windows scripts were not executed on a Windows host by this session, so host-level registration/runtime verification is not claimed. This is an explicit operational verification boundary, not an application correctness failure.

No application scheduler, background worker, second destructive path, or change to M57/M58/M59 semantics was introduced.

## 9. M61 Design Gate

DEC-126 proposes M61 as the next analytical milestone. Repository review found the core analysis pipeline already implemented, including technical/fundamental analysis, scoring, stock quality, entry context, entry quality, and opportunity classification. The next unresolved boundary is historical strategy validation.

Design gate: `docs/DEC-126-M61-BACKTESTING-DESIGN-GATE.md`.

Status: **Accepted — simulator + point-in-time historical input boundary + Strategy v0 integration merged and verified**. The accepted baseline is event-driven, leakage-safe, signal-after-close, next-bar-open, single long-only simulation with strategy invalidation as the primary exit, configured maximum-holding-period safety exit, and explicit cost/slippage semantics.

### M61 Historical Input Boundary

DEC-127 is accepted and its implementation is now on `main`. Historical financial facts are consumed only through the provider-neutral `HistoricalFinancialSnapshot` boundary, where a snapshot is eligible only when its explicit `available_at` is not later than the decision date. The point-in-time provider also selects the latest revision available for each financial period end before choosing the two latest eligible periods.

Current Yahoo statement selection by period_end remains unsuitable as evidence for leakage-safe historical performance claims because it does not prove public availability at the decision time.

PR #168 integrated Strategy v0 with the production `StockAnalysisPipeline` and the point-in-time fundamental provider. PR #169 repaired the dependency-ordering mistake by restoring the accepted DEC-127 prerequisite boundary on `main`; its head `b3a5e0bcaf8015307268c0d66df351c0cca21c32` passed GitHub Actions Tests Run #2782 and PR #169 was merged at `87b121964bc782fbe6ee1f58d2b9a4682db37a7c`.

M61 is **not complete yet**. The deterministic historical-dataset schema, acquisition gate, and integrity hardening are merged. The repository still needs actual historical coverage, data-quality boundary verification, deterministic Strategy v0 evaluation against real historical observations, aggregate/trade-level review, and final reproducibility validation before any performance conclusion is made.


### M61 Historical Dataset Boundary — DEC-128

DEC-128 is accepted. M61 will use a versioned external historical dataset as the production/backtesting evidence boundary, with a small repository-owned fixture dataset for deterministic tests.

The repository owns the dataset contract, schema, manifest, immutable version identity, integrity metadata, and loading rules. Large historical artifacts remain outside Git and are consumed only through an immutable dataset version and integrity hash.

The dataset must provide daily market observations and point-in-time financial snapshots with explicit availability and revision metadata. The physical artifact format remains a follow-up implementation decision.

M61 remains in progress. No real historical performance conclusion is valid until an actual dataset version is available and the full historical evaluation path is verified.


### M61 Dataset Schema — DEC-129

DEC-129 is accepted. The first historical dataset implementation uses deterministic UTF-8 CSV artifacts with canonical Decimal text, an immutable manifest, SHA-256 integrity checks, and repository fixtures using the same contract. Financial availability is date-based for the daily Strategy v0 boundary. Parquet remains deferred pending real scale requirements.


### M61 Engineering Hardening Review — PR #201

A project-wide engineering review was completed against the GitHub repository. The accepted hardening slice merged through PR #201 addresses the highest-confidence software-quality findings that could be completed without inventing external historical evidence:

- the historical-dataset backtest runner no longer imports infrastructure adapters directly; it now consumes the existing application-facing market-data and historical-fundamental contracts;
- deterministic integration tests are now explicitly classified and run in CI;
- live EGAL and provider smoke tests are explicitly classified as external rather than being silently mixed with deterministic CI coverage;
- pytest now declares both integration and external markers;
- unit, deterministic integration, and frontend/build CI jobs all pass on the merged hardening head.

This hardening does not claim that the real M61 historical dataset is accepted. Real historical acquisition, provenance closure, immutable dataset freeze, and evidence-backed Strategy v0 evaluation remain the analytical acceptance path.

## 10. M61 Current Checkpoint

The latest functional main merge is `d3b663156cc19a223f59d44b5fab74be49adec03` through PR #204; the follow-up state-documentation commit is `c3aa161420adb309a41cdd016977e6a4d53f43fa` (2026-10-01).

M61 remains in progress. DEC-130 is accepted, but the repository does **not** contain an accepted real historical dataset version. The current blocker is acquisition and provenance validation for the bounded ten-symbol cohort.

Operational checkpoint: `docs/M61-HISTORICAL-DATASET-ACQUISITION-STATUS.md`.

Current source-validation documentation now covers EGI, Mubasher, Mansa Markets, and the separate point-in-time financial-source boundary. Mansa's non-production acquisition probe is merged and CI-verified, but Mansa remains **NOT ACCEPTED** pending authenticated cohort extraction, provenance, and licensing/storage validation.

The immediate executable work remains:
1. run the merged Mansa market-source probe with valid access when the project key has the required history entitlement and preserve evidence only within permitted terms;
2. close the COMI financial provenance chain and extract one required Strategy v0 metric deterministically;
3. expand the same evidence package across the remaining nine symbols;
4. freeze the immutable M61 dataset manifest only after DEC-130 acceptance passes.

PR #180 and PR #181 are merged. PR #182 was superseded and closed after its branch diverged from main; its unique documentation content was reconstructed and merged through PR #183.

Branch deletion is not exposed by the current GitHub integration, so no branch deletion is claimed.


### M61 Backtest Warm-up Contract — PR #202

PR #202 is merged at `b1fe311f07f15a5228ba694c4f5fe6181c825984`. The backtest domain now models `warmup_bars` explicitly in `BacktestConfiguration`. Warm-up observations remain visible to strategy history for indicator/state construction, but signals are not evaluated before the configured evaluation boundary. Negative warm-up values are rejected.

This establishes the simulator contract only. It does **not** prove that the real M61 dataset contains the required 252 valid trading observations before the evaluation window. That remains part of dataset acceptance.

CI for PR #202 passed for unit tests, deterministic integration tests, and frontend tests.

### M61.3 Operational Conflict Durability — ACCEPTED

PR #204 is merged at d3b663156cc19a223f59d44b5fab74be49adec03. DEC-131 is now implemented at the software-boundary level: operational market data has an application-facing persistence port, a SQLite durable adapter, acquisition-linked observations, and a provider-neutral MarketDataConflictEvent. A conflicting duplicate never overwrites the existing observation; the conflicted acquisition and conflict event are committed durably before MarketDataConflictError is raised. Restart-safe deterministic tests verify acquisition round-trip, idempotent duplicates, conflict durability, acquisition linkage, and preservation of the original observation.

The PR #195 draft slice is superseded by PR #204 and should not be treated as an independent acceptance target. The immutable M61 historical dataset remains a separate blocker; DEC-131 acceptance does not imply that the real ten-symbol dataset or its raw-source evidence chain is accepted.

### M61.5 Operational Acquisition Provenance — ACCEPTED

DEC-132 is now accepted. The operational acquisition provenance boundary is implemented and verified through the existing application service and durable SQLite store. Successful, incomplete, and failed acquisitions retain requested/observed coverage, provider/source-symbol identity, stable stock identity, timestamps, row counts, and optional raw-artifact hashes. Acquisition history is queryable through the application-facing store boundary. This closes the operational provenance design gate without accepting the real immutable M61 evaluation dataset.

### M61.4 Raw-source Evidence Verification — IMPLEMENTED

PR #205 is merged at 2a3babd3b7227cc17d7868f52c1f6cf1dc9ebdbe. The historical dataset loader now exposes an explicit raw-source evidence acceptance check that validates dataset-relative evidence references and recomputes the preserved evidence SHA-256. Tamper and path-escape tests are covered by CI. This closes the software-side evidence-chain verification gap, but the synthetic repository fixture is not real market evidence; a real M61 dataset still requires an authenticated source artifact, preservation/usage rights, cohort coverage validation, and a frozen manifest.


### M61.6 Exact Raw Acquisition Artifact Integrity — ACCEPTED

PR #207 is merged at 802e38617fec2ab50a5d26660c51bdd50b113710 after GitHub Actions Tests Run #3225 passed on head e4c9d00679e1b85b0d6ee584ac589c8e1bfb7b61. The M61 acquisition probe now preserves the exact provider response bytes when raw preservation is enabled, so the recorded SHA-256 is tied to the actual preserved artifact rather than a re-serialized JSON representation. Deterministic validation also requires 252 observations before the 2021-01-01 evaluation start and checks evaluation-window/coverage evidence. This is an acquisition-tool integrity gate only; it does not accept any real provider artifact or the immutable M61 dataset.

The next acceptance boundary is now real COMI acquisition and provenance closure. No Strategy v0 performance conclusion should be made before the COMI artifact passes identity, coverage, data-quality, price-semantics, raw/transformed checksum, licensing/retention, and point-in-time financial evidence requirements.


### M61.7 COMI Evidence Intake — ACCEPTED (software boundary)

PR #209 is merged at `fc60ef11e891969f26b9060bd1a9d52c9bcb2a19` after GitHub Actions Tests Run #3262 passed.

The repository now has a deterministic local COMI evidence-intake command at `tools/m61_comi_evidence_intake.py`. It consumes an already-acquired dataset and verifies the existing production historical-dataset integrity boundary, raw-source evidence, explicit COMI source-symbol mapping, single internal stock identity, 252 pre-evaluation observations, 2021–2025 evaluation coverage, corporate-action convention, licensing notes, and financial artifact presence.

The intake tool does not download data, fabricate evidence, mutate the raw artifact, silently repair rows, or accept the repository's synthetic fixture as real market evidence. Its focused tests explicitly prove rejection of the synthetic fixture and missing datasets.

This closes the remaining **software-side M61 evidence-intake path**.

### M61 Stop Checkpoint — 2026-10-01

The project is intentionally stopping here until real external evidence is available.

Completed and verified:
- M61 simulator and Strategy v0 integration;
- point-in-time financial boundary;
- versioned historical-dataset contract and loader;
- operational acquisition provenance;
- conflict durability;
- exact raw-artifact checksum preservation;
- deterministic M61 warm-up/evaluation-window validation;
- COMI evidence-intake/acceptance tooling;
- unit, deterministic integration, and frontend CI verification for the completed software slices.

Still not accepted:
- real COMI market artifact;
- real COMI point-in-time financial evidence package;
- immutable ten-symbol M61 dataset version;
- Strategy v0 historical evaluation results;
- aggregate/trade-level performance conclusions.

The current external dependency is therefore **real, legally retainable historical evidence acquisition**, not missing application architecture.

When work resumes, the sequence is fixed:
1. acquire and preserve COMI evidence under permitted terms;
2. run the M61 intake and resolve every finding;
3. add the required point-in-time financial evidence;
4. accept/freeze COMI;
5. repeat for the remaining nine cohort symbols;
6. freeze the immutable M61 dataset;
7. run Strategy v0 evaluation;
8. review trade-level and aggregate results;
9. perform reproducibility verification;
10. close M61 only after the complete evidence-backed gate passes.

No performance conclusion is valid before that final sequence completes.


## Temporary execution pause — 2026-10-28

The owner explicitly requested that M61 be deferred while the remaining non-M61 gaps are completed. This pause changes execution priority only; it does not weaken M61's evidence requirements or mark M61 complete. No historical backtest performance conclusion is authorized during the pause.

Current non-M61 review queue:
1. Crash Radar / Market Breadth & Stress Pulse: verify freshness, coverage, missing-symbol handling, and clear heuristic labeling; retain the current score formula unless separately approved.
2. Technical-analysis and news evidence: audit the merged stack end-to-end across domain calculation, API contracts, persistence, authorization, and dashboard rendering; do not infer live news coverage without an accepted provider adapter and source-rights review.
3. Opportunity lifecycle, Telegram delivery, post-session reports, subscriptions, and owner dashboard: resolve the open design decisions before production behavior or payment integrations are changed.
4. Engineering quality: architecture-boundary regression tests are now merged (PR #384); continue targeted regression/security/operational checks and keep `CURRENT_STATE.md` synchronized with verified GitHub evidence.

M61-related draft PRs and exploratory artifacts remain isolated; do not merge them as a substitute for the accepted historical-data evidence gate.

## Non-M61 quality follow-up — 2026-10-28

Verified changes merged after the explicit M61 pause:

- PR #392 adds the EGX-timezone reference date and per-symbol calendar-day snapshot age to Crash Radar. The existing 50/40/10 heuristic and its denominator are unchanged.
- PR #394 fixes RSS/Atom point-in-time semantics: Atom `updated` is no longer substituted for publication time. Updated-only items remain ineligible for as-of analysis.
- PR #395 strengthens the architecture regression guard so `from app import api`-style imports cannot bypass the domain/application dependency checks.
- PR #396 normalizes timezone-aware snapshot timestamps to the `Africa/Cairo` calendar before calculating snapshot age, and tests same-day and future-dated evidence.
- The implementation PRs above passed all five CI jobs before merge. Post-merge verification is tracked separately from PR-head CI; always inspect the latest `main` workflow before declaring closeout.

Remaining non-M61 acceptance boundaries:

1. **Crash Radar policy:** snapshot dates and ages are visible, but a configured universe, freshness warning/enforcement threshold, minimum-coverage policy, score suppression, historical score retention, and alerts remain unapproved. No score policy was silently selected.
2. **News evidence:** the RSS/Atom ingestion path is operator-triggered and provider-neutral. No official EGX feed is enabled by default; source authenticity, usage/redistribution rights, coverage, and operational polling must be verified before claiming official or comprehensive news coverage.
3. **Opportunities and Telegram:** existing signal, durable delivery, recipient, and owner/session-report foundations are not equivalent to an accepted end-to-end opportunity lifecycle with re-evaluation/invalidation and subscriber entitlements. The product policy gate in PR #344 remains a draft.
4. **Session reports and monetization:** manual report foundations exist, but automatic session-finalization/distribution and payment/subscription behavior remain behind explicit design decisions. No payment gateway, price, or paid entitlement has been chosen.
5. **Technical/news intelligence:** the merged calculation and ingestion components still require end-to-end acceptance across input quality, calculation semantics, API authorization/contracts, persistence, dashboard empty/error states, and source provenance. The draft design gate in PR #347 is not a release acceptance.
6. **Crash Radar v2:** PR #342 remains a draft for the unresolved universe/freshness/coverage/retention/alert policy. Its two-stage direction does not authorize a new predictive score.

M61 remains paused and incomplete. Its real historical-data evidence requirements and any performance-claim restrictions are unchanged.

## Verified non-M61 follow-up — 2026-10-28 (continued)

Additional changes merged after the earlier quality follow-up:

- PR #399 connects related normalized news events to the stock-analysis dashboard. The news panel has loading/empty/error states and does not replace or suppress the technical report when news retrieval fails.
- PR #400 validates source URLs at the news domain boundary: absolute HTTP(S), a hostname, and no embedded user information are required.
- PR #401 displays an explicit Crash Radar limitation next to the score: the saved-snapshot heuristic is not a crash prediction or buy/sell signal, and missing/undated/stale evidence can affect it.
- PR #402 rejects non-finite/non-positive lifecycle prices, timezone-naive market observations, and observations preceding signal generation. Validation occurs before history mutation; regression tests cover the no-side-effect guarantee.
- PR #403 adds dashboard-level news failure isolation and verifies the related-news API request contract.
- PR #404 adds deterministic ABC zigzag correction candidates to Elliott analysis, API serialization, and the technical indicator panel. Candidates use only confirmed swings and expose rule violations. Flat, triangle, combination, and complex corrections are not inferred.

Verification:
- PR-head CI succeeded for PRs #399–#404 before merge.
- Main CI succeeded for commit `1d68a4b61459a31bcd87b7121dd498a55c1e7f09` after PR #403.
- Main CI succeeded for commit `55c690adef5897645076eeb33583b7d90779c057` after PR #404 (run `40676443992`). The documentation-only closeout PR must also pass CI before it is merged.

Current feature inventory (implemented foundations, not a claim that every product gate is released):

1. **Technical analysis:** price/trend/momentum/volume analysis, candlestick patterns, technical indicator history (SMA/EMA, RSI, MACD, Bollinger, ATR, stochastic, CCI, OBV, MFI, ADX/DI, Ichimoku), confirmed swing points, Fibonacci retracements/extensions, Elliott impulse candidates, and ABC zigzag correction candidates.
2. **News intelligence:** normalized event evidence, RSS/Atom ingestion, publication/first-seen point-in-time rules, persistence/query APIs, and related-news dashboard display. The system is provider-neutral; an approved official source, usage rights, comprehensive coverage, and scheduled polling are not yet established.
3. **Market context:** Market Breadth & Stress Pulse, component-level score transparency, analyzed-universe coverage, per-symbol snapshot dates/ages, future/unknown date visibility, and an explicit heuristic limitation note. Freshness thresholds, minimum coverage, score suppression, retention, and alerts remain unapproved.
4. **Trading opportunities:** signal generation, immutable publication/outbox, lifecycle history, invalidation/trigger transitions, outcome tracking, Telegram account linking/delivery, and entitlement evaluation have implementation foundations. The final user-facing lifecycle, subscriber product rules, and live billing integration remain gated.
5. **Session reporting and owner operations:** session opportunity ledger/report and owner dashboard foundations exist. Automatic exchange-session finalization/distribution is not yet accepted or enabled.
6. **Quality and security:** dependency-boundary regression tests, point-in-time news tests, URL validation, lifecycle time/price invariants, dashboard failure-isolation tests, lint/type checks, unit/integration/frontend tests, dependency audit, and container build checks.

Owner decisions and external prerequisites still blocking release claims:

- PR #342: Crash Radar universe, freshness/coverage policy, historical retention, and alert behavior.
- PR #344: opportunity lifecycle and Telegram packaging, subscriber entitlements, session-report behavior, and commercial/payment policy.
- PR #347: approved news source/provenance and remaining technical/news intelligence acceptance, including Elliott alternatives beyond impulse/ABC zigzag.
- M61 remains paused by explicit owner request. Do not resume historical-data acquisition, backtesting, or strategy-performance claims.
- Issue #141 branch-ref deletion remains a manual GitHub UI/local Git operation because the connected integration does not expose branch deletion. Do not claim stale remote branches were deleted.

## Non-M61 closeout update — 2026-10-28 (PRs #407–#410)

The following additional corrections and operator capabilities have been merged:

- **PR #407 — manual subscription administration API:** immutable plan versions; operator-only plan/subscription reads and writes; validation that the target user exists and the plan version is active; new subscriptions start as `PENDING`; explicit status transitions require an audit reason and persist actor/time/reason; audit history is readable through an operator endpoint; invalid lifecycle and concurrent-update conflicts are mapped to HTTP conflict responses. The "latest subscription by user" query is chronological rather than active-status-prioritized.
- **PR #408 — owner subscription panel:** create immutable plan versions, provision pending subscriptions, inspect subscriptions by ID/user, load persisted audit history, and select only valid lifecycle transitions. Terminal states do not expose further transitions. This is manual administration only; the interface does not process or verify payments.
- **PR #409 — no linked Telegram recipients:** outbox events with no linked accounts are marked as a durable terminal suppression rather than being retried indefinitely or reported as delivered.
- **PR #410 — no eligible Telegram recipients:** an event is not marked delivered if every linked account is suppressed by user status or entitlement checks. This has its own durable terminal state and owner-dashboard/API metric, distinct from having no linked accounts. Partial delivery/retry behavior remains idempotent.

Latest verified CI before this documentation update:
- PR #407 latest-head CI passed all five jobs (run `40680659661`).
- PR #408 latest-head CI passed all five jobs (run `40680589130`).
- PR #410 latest-head CI passed all five jobs (run `40680309991`).
- Main CI passed after PR #410 (run `40680901413`). The combined main state after PRs #407 and #408 must be checked separately before closeout is declared.

Remaining release gates are unchanged:
- PR #342: owner decisions for Crash Radar universe, freshness/coverage policy, history retention, and alerts.
- PR #344: final opportunity lifecycle semantics, subscriber packaging, automatic session-report finalization/distribution, and commercial/payment policy.
- PR #347: approved/licensed news source and remaining end-to-end technical/news acceptance, including Elliott alternatives beyond impulse/ABC zigzag.
- Payment reconciliation, authenticated/idempotent payment webhooks, refunds/chargebacks, automatic expiry/finalization, and live Telegram send verification are not delivered by the manual subscription UI.
- M61 remains paused by explicit owner request; no historical strategy-performance claim is accepted.
- Issue #141 remote branch deletion still requires a manual GitHub UI/local Git operation because the connected integration does not expose branch deletion.

This is an implementation/status record, not a declaration that all release gates are closed.


## Owner-approved non-M61 policy baseline — 2026-10-31

DEC-135 is accepted by the owner. The accepted policies cover configurable Crash Radar universe and completed-session freshness with visible coverage/no automatic alerts; immutable EGXBot opportunity versions with completed-session re-evaluation, explicit invalidation/expiry, durable auditable Telegram delivery and manual trading only; Cairo-time idempotent session reports with traceable corrections/no duplicate distribution; manual audited subscription entitlements with billing/pricing/refunds deferred; official news disclosures only after access/reuse terms are verified; and no actionable signals from stale, missing, future-dated, or invalid data.

**Implementation boundary:** policy acceptance does not prove feature completion. The completion gap register remains authoritative for outstanding integration, tests, source-rights checks, and operational evidence. PR #422 is merged at `fa5d16a9b8a47e3cdcb9467d1e31ffd4ee6bed64`; main CI run #41185546490 passed all five jobs. M61 remains paused; PR #321 remains open Draft and is not authorized for merge.


## Telegram delivery concurrency decision — 2026-10-31 (DEC-136)

The owner approved conservative handling of ambiguous Telegram sends: persist `DELIVERY_UNKNOWN`, do not automatically resend, and require operator reconciliation. Definite failures remain a separate retry category. This is a policy decision, not an implementation claim. The current dispatcher still lacks atomic per-recipient claims and does not yet distinguish ambiguous transport exceptions from definite failures. The lease rule is approved: runtime lease = 2 × the effective configured Telegram transport timeout. Definite-failure retry schedule, attempt budget, and exhaustion behavior remain open. See `docs/TELEGRAM-DELIVERY-CONCURRENCY-DESIGN-GATE.md`.


## Verified continuation — 2026-11-07

- PR #446 merged with the authenticated per-user Telegram opportunity notification feed. It does not provide complete lifecycle history.
- PR #447 merged at `8995e8f4d5ef1420ef4d625195d187cb32397679`. The canonical EGX daily-history archive contains 186 source-attributed records through 2026-11-05; 36 rows remain flagged because reported open is below reported low. This is not clean OHLC evidence, complete market coverage, production ingestion, or accepted M61 data.
- PR #450 merged the approved SQLite lifecycle Unit of Work at `71acf708aab4b1e6c3bc87b2a6d1a1b9bc1db4a`. Exact-head CI #42377116040 and post-merge main CI #42377785229 passed all five jobs.
- PR #452 merged per-write rollback failpoint tests at `1f6594b74ba6d6814413b325d21c04395180baa2`. Exact-head CI #42377931439 passed all five jobs. Post-merge main CI #42378195751 is pending.
- Lifecycle history, optional market-proxy outcome, and alert outbox intent now commit through one SQLite connection/transaction. Telegram delivery remains a later external side effect.
- Remaining lifecycle acceptance: restart/dispatcher recovery proof and a focused regression test that guards the no-network-I/O-inside-transaction boundary.
- Automatic observation wiring remains incomplete. Observation identity, source/price selection, candle crossing precedence, expiry, opportunity revision, and entry-price basis must be resolved before monitoring is enabled.
- M61 remains paused and untouched; PR #321 remains Draft.


## Verified daily-history audit continuation — 2026-11-10 (PRs #483–#488)

- PR #483 merged the read-only calendar artifact inventory; PR #484 added SQLite WAL read-only inventory coverage. Their scope is inventory visibility, not production storage/recovery acceptance. PR #485 reconciled those changes and the daily-data status.
- PR #486 merged the 2026-11-10 daily-history rebase. It preserved the original PR #476 file changes after verifying both source file blobs matched the current main base; no daily-history rows were discarded. The archive contains 255 rows across 61 symbols and 31 session dates. The 2026-11-10 batch contains 23 rows (17 equities, six indices); eight rows remain flagged for OHLC review. The batch has no duplicate symbols, but all 23 rows have blank traded-value and execution-count fields, and EGREAL has blank volume. These blanks mean unavailable, not zero.
- PR #487 merged the read-only tools/egx_daily_history_audit.py command and regression tests. It validates the canonical CSV schema, row shape, dates, symbols, units, numeric values, source metadata shape, quality labels, duplicate (session_date, symbol) keys, OHLC geometry, missing metrics, and artifact byte count/SHA-256. It never fetches/authenticates source pages, infers sessions/instruments, repairs values, or mutates the source CSV. source_authenticity is explicitly NOT_INDEPENDENTLY_VERIFIED; review-labelled and geometrically inconsistent rows are not clean OHLC evidence.
- PR #487 post-merge main CI run #42886017424 completed successfully on 5c303ff15b97357d7ab086c921061644265ff309.
- PR #488 merged as bdef388e06b854324124f5f61099f0f5717e54e6 after all five required CI jobs passed on exact PR head fe9ba50a823f46e6965aa180d7abb4d488a17df3 in run #42887122981. It adds mutually exclusive structural row classifications and optional read-only baseline snapshot comparison. `clean_ohlc_candidates` means structural candidate only; it is not source authentication or approval for trading inputs. Post-merge main CI is running and must be checked independently.
- PR #476 was closed unmerged after its data changes were preserved in #486. PR #482 was closed unmerged as superseded. No source price rows were automatically repaired or replaced.

Current daily-history boundary: the audit is a local artifact-structure/quality check, not an EGX source verification service, ingestion scheduler, completeness guarantee, or M61 acceptance. Preserve all review flags and raw source values until independently reconciled. M61 remains paused; do not enable activation, lifecycle, freshness enforcement, or strategy-performance claims without the separately required owner decisions and evidence.


## Verified daily-history audit automation and main-line result — 2026-11-10 (PRs #493–#495)

- PR #493 merged the end-to-end CLI smoke tests as main commit `b9fcc03a35bec54fa6395109dec53da260b51880`. The tests invoke the module as a subprocess, verify stdout and persisted JSON, assert the source archive remains byte-identical, and check the report byte count and SHA-256.
- PR #494 merged as `be8b8fea246870a517f3f80bad9a8123f23efabb`. It adds a `workflow_dispatch` trigger and a `daily-history-audit-report` GitHub Actions job. The job runs the read-only CLI against the canonical archive, accepts exit code 1 only as the expected findings outcome, validates the JSON report, and uploads it as a GitHub Actions artifact with 14-day retention.
- The workflow is triggered by push, pull request, and manual dispatch; it does **not** add a scheduled cron collection or daily scheduled audit. It does not modify/commit the CSV, fetch a new provider feed, or change analysis eligibility.
- PR #494 exact-head CI passed all six jobs on `187e8970e7e0c93331353db86517c5c60f3c8a0a` in run #42893671493. Post-merge main run #42894527758 completed successfully with all six jobs on `be8b8fea246870a517f3f80bad9a8123f23efabb`.
- The actual post-merge main artifact is GitHub Actions artifact #13799198851, named `egx-daily-history-audit-be8b8fea246870a517f3f80bad9a8123f23efabb`, created 2026-11-10 20:21:51Z and expiring 2026-11-24 20:21:50Z. ZIP SHA-256: `c7e76b51d7a909a421b6437f7328b7dafad9b601743255c5367cf0b795882425`.
- The report from that main artifact says `completed_with_findings`: 255 rows parsed; zero malformed rows, invalid rows, or duplicate keys; 51 OHLC geometry inconsistencies; 70 review-required rows; 185 structural candidates; zero rejected/invalid rows; 61 symbols; 31 session dates (2026-09-28 through 2026-11-10). The latest session has 23 rows.
- Missing metrics: `executions_count` is blank in 255 rows, `traded_value_egp` in 255 rows, and `volume_thousands_reported` in 23 rows. Blank remains unavailable, not zero.
- Report eligibility remains `STRUCTURAL_CANDIDATE_ONLY_NOT_SOURCE_AUTHENTICATED`; source authenticity remains `NOT_INDEPENDENTLY_VERIFIED`. The input archive is 101,315 bytes with SHA-256 `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`.
- PR #495 merged as `2b18d2d1ac9ea54aa89b17351875802e5970a7ab`. Its exact-head CI run #42895151535 passed all six jobs on `db52eb8eefa4c54efdd804dfb16d01cd9af111c0`; it preserves the CLI case where an unlabelled OHLC inconsistency must produce exit code 1 and leave source bytes unchanged.
- PR #496 merged as `05c3d00e719b3d50c8f9e57dfc73644d54f72a0c`. Its exact-head CI run #42895373313 passed all six jobs on `7712eaa639478dd7e276b4167a9a3c172e1749e0`; it reconciles the actual main audit artifact and the workflow's trigger/retention limitations.
- Post-merge main CI after #495/#496: run #42895887814 on `2b18d2d1ac9ea54aa89b17351875802e5970a7ab` has five of six jobs passed and unit tests still running at the latest check. Run #42896314522 targets final main `05c3d00e719b3d50c8f9e57dfc73644d54f72a0c` and is queued. Do not declare post-merge main CI green until the latest run completes.

**Boundary:** this is a repeatable CI artifact check, not a scheduled data collector, market-completeness check, source-authentication service, or permission to use unauthenticated rows in trading analysis/backtests. No prices were repaired or replaced. M61 remains paused; no activation, lifecycle, freshness enforcement, or strategy behavior was enabled.

**Authority:** GitHub `main` and run #42894527758; artifact #13799198851.  
**Last reviewed:** 2026-11-10; main `be8b8fea246870a517f3f80bad9a8123f23efabb`; post-merge CI passed 6/6.


## Latest verified continuation — 2026-11-10 (daily-history reconciliation protocol merged)

- PR #497 merged as `0e9bbeccf71d75cece2585e8a95a98c3ea700617`. Its exact-head CI run #42896485869 passed all six required jobs on `fa365a2bc273ded88ccfbc54d1eeca407a35a7e1`. It reconciles the merge state and CI record for PRs #495/#496.
- PR #498 merged as `ca556e1c3dd109f6ccb0f981b1c57398ff54e1e5`. Its exact-head CI run #42897109443 passed all six required jobs on `32c4f2aee4dd59a62f583f2f1f07d9d6cbbc2e9a`. It adds `docs/EGX-DAILY-HISTORY-RECONCILIATION-PROTOCOL.md`, defining evidence hierarchy, immutable evidence capture, field-by-field comparison, explicit reviewer dispositions, and closeout criteria. It does not select a provider or authorize data correction/ingestion.
- Post-merge main CI run #42897359694 on PR #497 merge commit `0e9bbeccf71d75cece2585e8a95a98c3ea700617` completed successfully with all six jobs.
- Post-merge main CI run #42899130922 targets current main `ca556e1c3dd109f6ccb0f981b1c57398ff54e1e5`. At this documentation snapshot, five of six jobs have passed and `unit-tests (3.12)` is still running; do not mark the final post-#498 main line green until it completes successfully.
- The reconciliation protocol is process documentation only. No archive values were repaired/replaced, no provider was selected, no ingestion or eligibility promotion was enabled, and M61 remains paused.

**Authority:** GitHub `main`, PR #497/#498, and exact-head Actions runs above.  
**Last reviewed:** 2026-11-10; main `ca556e1c3dd109f6ccb0f981b1c57398ff54e1e5`; post-merge run #42899130922 pending unit tests.
