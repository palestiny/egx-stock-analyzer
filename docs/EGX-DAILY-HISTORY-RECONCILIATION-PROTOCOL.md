# EGX Daily-History Reconciliation Protocol

**Status:** Proposed review protocol — not a source acceptance or data-correction decision  
**Reviewed:** 2026-11-10  
**Canonical input:** `data/market_history/egx_daily_history.csv`  
**Related:** `MARKET-DATA-PROVIDER-RELIABILITY-DESIGN-GATE.md`, `M61-HISTORICAL-SOURCE-ACCEPTANCE-MATRIX.md`

## 1. Purpose and boundary

Define a reproducible, auditable process for resolving rows already marked for review in the daily-history archive. This protocol is deliberately separate from the structural CSV audit.

It does **not**:
- select or approve a market-data provider;
- establish that Investing.com values are authoritative;
- authorize scraping, redistribution, or long-term retention beyond applicable terms;
- repair, replace, delete, or normalize historical price observations;
- promote rows to M61, backtesting, analysis, or trading eligibility;
- activate calendar, freshness, lifecycle, or strategy behavior.

The canonical CSV remains immutable during review. Any eventual correction or accepted replacement requires a separately reviewed change with the original row preserved in version history and an explicit evidence trail.

## 2. Current review population

The latest verified archive audit contains 255 parsed rows and 70 review-required rows, partitioned by the existing mutually exclusive `quality_status` values:

| Review class | Rows | Meaning |
|---|---:|---|
| `ohlc_inconsistency_review` | 51 | OHLC geometry violates the canonical high/low envelope |
| `source_conflict_review` | 18 | More than one retrieved representation conflicts |
| `source_revision_conflict` | 1 | A later same-provider representation differs from the archived observation |
| **Total** | **70** | **All require explicit disposition** |

The 51 OHLC cases comprise 48 observations where open is below low and three where open is above high. These counts are structural findings, not proof of which field or source is wrong.

The remaining 185 rows are only structural candidates under the audit contract. They are not independently source-authenticated.

## 3. Review queue identity and immutable evidence

Every review item is identified by the canonical key:

`(session_date, symbol)`

The reviewer must capture the exact canonical row before comparing anything:

- session date, instrument type, symbol, and price unit;
- original OHLC values and reported volume/change values;
- source name, exact source URL/locale, retrieval timestamp, and stated delay status;
- original quality status and notes;
- canonical archive commit SHA and file SHA-256 at review start.

Never overwrite the original values in a working note. A candidate comparison is a separate evidence record.

## 4. Evidence hierarchy

Use evidence in this order, subject to access rights and instrument-specific applicability:

1. **Primary exchange evidence:** an official EGX notice, official market record, or authorized exchange data response that identifies the instrument and session.
2. **Contractually authorized provider evidence:** a dated raw response or downloadable record with provider identity, instrument mapping, session semantics, retrieval timestamp, and documented correction/revision behavior.
3. **Independent secondary evidence:** a separately operated provider or brokerage export with clear instrument/session identity and permitted use.
4. **Same-provider alternate page or locale:** useful to detect a discrepancy, but not independent corroboration.
5. **Search snippets, quote widgets, or undated summaries:** discovery clues only; never sufficient for acceptance.

Two localized pages from the same provider must not be counted as two independent sources. A matching close alone does not authenticate open, high, low, or volume.

## 5. Field-by-field comparison

For each candidate observation, compare independently:

- instrument identity and symbol mapping;
- session date in the EGX market timezone;
- open, high, low, close, and price unit;
- volume, preserving the provider's original unit and displayed precision;
- traded value and executions only when explicitly supplied for that instrument;
- adjusted versus unadjusted price convention;
- source timestamp, retrieval timestamp, and any correction/revision identifier.

Do not infer a missing field from a neighboring session, an index-wide aggregate, another security, or a market recap. Blank values remain unavailable, not zero.

For index observations, do not assume displayed volume is comparable to equity share volume. Record the provider's definition or leave comparability unresolved.

## 6. Disposition vocabulary

Each review item must receive exactly one current disposition:

- **UNRESOLVED** — insufficient evidence or conflicting evidence remains.
- **CONFIRMED_AS_REPORTED** — independent, sufficiently authoritative evidence supports every field under review.
- **CONFIRMED_ALTERNATIVE** — evidence supports a different value; the original remains preserved and a proposed replacement is recorded separately.
- **REJECTED_OBSERVATION** — evidence demonstrates the observation is not valid for the stated instrument/session.
- **NOT_COMPARABLE** — candidate sources use different instrument, session, adjustment, or metric semantics.
- **WAIVED_WITH_RATIONALE** — an authorized reviewer explicitly accepts a documented limitation for a narrowly stated purpose; this does not imply M61 or trading eligibility.

No item may be marked confirmed solely because its OHLC values satisfy geometry. No item may be marked rejected solely because it differs from another provider.

## 7. Required review record

For every item, retain:

| Field | Requirement |
|---|---|
| Review key | `session_date + symbol` |
| Original archive commit / digest | Exact immutable snapshot identity |
| Original row | Exact original values and metadata |
| Candidate evidence | Source, URL/reference, locale, raw artifact identity/checksum |
| Retrieval time | Timezone-aware timestamp |
| Comparison | Field-by-field differences, including units/precision |
| Source independence | Independent / same provider / unknown, with reason |
| Disposition | One vocabulary value from section 6 |
| Rationale | Short, evidence-linked explanation |
| Reviewer | Attributable human identity |
| Review timestamp | Timezone-aware |
| Follow-up | Open question or required next evidence |

A batch-level report may summarize results, but it must link to the individual records and preserve unresolved rows.

## 8. Recommended review order

Prioritize the queue to maximize diagnostic value without assuming a root cause:

1. **2026-11-04 and 2026-11-05 OHLC cohorts:** 19 and 11 flagged rows respectively. Compare a mix of equities and indices to determine whether the pattern is broad, instrument-specific, or source/locale-specific.
2. **Remaining OHLC cohorts:** 29 October, 2–3 November, and 8–10 November.
3. **Source conflicts:** resolve the 18 conflicts by field, including the documented ADIB, FWRY, ORAS, PHDC and index examples.
4. **EGAL revision:** compare the archived 28 October observation against dated evidence for both versions and determine whether the difference is a provider correction, page revision, or incomparable capture.

The order is an investigation priority only; it does not rank the reliability of individual observations.

## 9. Exit criteria and downstream boundary

A review batch is complete only when every item has a disposition, evidence references/checksums are retained, unresolved differences are explicit, and a second reviewer has checked any proposed alternative or rejection.

Even a fully reconciled batch does not automatically pass M61. Historical research acceptance still requires the separate dataset contract: coverage, session completeness, symbol mapping, adjustment semantics, reproducible transformation, licensing/storage rights, immutable artifact checksum, and point-in-time financial data where required.

**Current gate result:** OPEN — the 70-row review population is inventoried, but independent source evidence and item-level human dispositions are not established. Preserve the source archive unchanged and keep all review rows excluded from clean OHLC analysis.
