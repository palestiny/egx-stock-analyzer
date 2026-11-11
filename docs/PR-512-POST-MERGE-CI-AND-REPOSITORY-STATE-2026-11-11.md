# PR #512 Post-Merge CI and Repository State — 2026-11-11

**Status:** Verified documentation checkpoint. No market-data values or application behavior changed.

## Canonical repository state

- Repository: `palestiny/egx-stock-analyzer`
- `main` points to merge commit `a1b5851bd1f71dace92f3a2796f63d3d3e12fef6` (PR #512).
- The merge commit is GitHub-verified.
- PR #512 adds `docs/EGX-DAILY-HISTORY-ROW-REVIEW-LEDGER.md`, a row-addressable ledger for all 70 review items. All 70 dispositions remain `UNRESOLVED`.
- The ledger's 70 rows were checked against the canonical CSV snapshot before merge: row coordinates, dates, symbols, instrument types, quality classes, OHLC values, units, retrieval metadata, and source URLs matched. No ledger field mismatch was found.
- Canonical CSV identity remains Git blob `3c01a843c225d226dc49e7c302220a280cfafb57`, SHA-256 `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`. No CSV edit was included.

## Post-merge CI

Workflow run [#43005110145](https://github.com/palestiny/egx-stock-analyzer/actions/runs/43005110145) completed with conclusion `success` on the exact merge SHA `a1b5851bd1f71dace92f3a2796f63d3d3e12fef6`.

All six jobs passed:
- `unit-tests (3.12)`
- `integration-tests (3.12)`
- `frontend-tests`
- `dependency-audit`
- `container-build`
- `daily-history-audit-report`

The Python suite completed with 1,661 passed, 8 deselected, and 90.58% coverage. Ruff and mypy passed in the unit-test job. The daily-history audit remains a structural/read-only audit; a successful audit job does not authenticate the underlying market source.

## Historical-data gate

- Canonical archive: 255 rows, 61 symbols, 31 sessions.
- Review population: 51 OHLC geometry exceptions plus 19 source/revision conflicts = 70 unresolved items.
- P1 cohort: 30 OHLC exceptions from 4–5 November (19 on 4 November; 11 on 5 November).
- The 4–5 November evidence register and the row-review ledger are evidence indexes, not source authentication. The captured URLs are Investing.com localized pages; locales are not independent sources.
- No original page snapshots from collection time or authorized EGID sample are currently established by these artifacts.
- DEC-130 remains open. No source or dataset is accepted for M61. Do not correct or promote any row based on OHLC geometry, prior-close correlation, or a localized page alone.
- The EGID request remains an internal draft and has not been sent. No provider contact, credentials, paid plan, data ingestion, production adapter, or M61 activation is authorized.

## Open M61 experiment

PR #321 remains open and Draft: [test(m61): run Strategy v0 on public COMI history sample](https://github.com/palestiny/egx-stock-analyzer/pull/321). Its public COMI sample and exploratory diagnostics remain unaccepted evidence because provenance, adjustment/corporate-action semantics, point-in-time integrity, and intended-use rights are not established. Do not merge it or present its results as profitability evidence. DEC-130 must pass first.

## Repository governance finding

GitHub's branch endpoint reported `main.protected = false` and `protection.enabled = false` at this checkpoint. The separate branch-protection endpoint returned HTTP 403 to the connected integration, so detailed protection settings could not be inspected.

This is a governance risk: the repository does not currently report branch protection enabled. Recommended owner-admin action, not performed here:
1. Protect `main` and require pull requests.
2. Require all six named CI checks on the latest commit before merge.
3. Require branch up-to-date status before merge where appropriate.
4. Restrict bypass/direct pushes to a documented emergency-admin path.

No repository settings were changed because this requires owner/admin authorization and the connected integration could not inspect or configure the protection resource.

## Next evidence-driven actions

1. Obtain explicit owner approval before sending the prepared EGID no-cost evidence inquiry.
2. If an authorized, permitted sample is supplied, preserve the original bytes and checksum, then compare a small P1 subset plus controls field-by-field.
3. Keep all 70 ledger items unresolved until evidence and attributable human review support a disposition.
4. Keep M61 and PR #321 blocked until DEC-130 passes.

**Verification boundary:** This checkpoint records GitHub state observed on 2026-11-11. It does not claim any external provider response, source acceptance, branch-protection change, or data correction.
