# M61 — Point-in-Time Financial Source Validation

**Status:** Candidate validation in progress; no financial source accepted for Strategy v0.
**Decision boundary:** DEC-127 / DEC-130
**Updated:** 2026-09-25

## Purpose

This checkpoint isolates the financial-data acquisition problem from market OHLCV acquisition.

M61 requires financial values to be evaluated using only information that was available to the system on the historical decision date. A later publication or a later restatement must not silently become historical knowledge.

The accepted financial artifact therefore needs two distinct dates:

- **period_end** — the accounting period the value describes;
- **available_at** — when the value became available to an investor/system through the selected source.

The period end alone is never sufficient for point-in-time evaluation.

## Required financial evidence

For each historical snapshot used by Strategy v0, preserve:

1. internal stock identity;
2. source company/security identity;
3. statement type (standalone/consolidated);
4. fiscal/reporting period;
5. period_end;
6. publication/disclosure timestamp or defensible publication date;
7. available_at derived from that publication evidence;
8. metric name and normalized value;
9. source document URL/reference;
10. raw document checksum where legally storable;
11. extraction/normalization rules;
12. restatement/revision status when observable;
13. currency and reporting unit;
14. missing/excluded reason when a value is unavailable.

## Source hierarchy

### 1. EGX/FRA-published disclosures — primary provenance target

EGX disclosures and financial-statement publications are the preferred provenance boundary because the historical availability event must be tied to an actual market disclosure.

The current regulatory record confirms that listed companies submit periodic financial statements to the FRA/market-regulatory framework and that filing deadlines are explicitly defined and periodically amended. This establishes the regulatory filing boundary, but it does **not** by itself provide the historical artifact or its exact publication timestamp for each company.

M61 therefore requires direct retrieval of the actual historical disclosure/financial-statement artifact and its publication metadata before acceptance.

### 2. Issuer investor-relations archives — secondary provenance/cross-check

Issuer investor-relations pages commonly publish dated quarterly/annual financial statements. They can provide useful document copies and publication dates, but M61 must verify that the date represents public availability and that the document corresponds to the same filing/disclosure used for the market-facing historical event.

Issuer archives may therefore support evidence and cross-checking, but they do not automatically replace the EGX disclosure provenance boundary.

### 3. Third-party normalized archives — extraction/cross-check only

Services such as AskBorsa can normalize historical Egyptian listed-company statements and preserve links to source documents. This is useful for accelerating extraction and cross-checking, but a third-party normalized number is not accepted as primary point-in-time evidence unless the underlying source document and its availability date can be independently verified.

## Acceptance rules

A financial source is accepted for M61 only when all of the following are proven for the bounded ten-symbol cohort:

- required metrics are available for the Strategy v0 fundamental boundary;
- every accepted snapshot has a defensible `available_at`;
- the source document can be identified and traced to the issuer/security;
- standalone vs consolidated semantics are explicit;
- units/currency are explicit;
- missing periods are represented rather than forward-filled;
- revisions/restatements are not silently collapsed into the first publication;
- extraction is deterministic and reproducible;
- raw artifacts/checksums are preserved when licensing permits;
- the source permits the intended internal research/backtest storage and use.

## Important regulatory-date distinction

A filing deadline is not the same thing as `available_at`.

For example, a regulator may extend the deadline for a reporting period. That deadline is evidence about when a filing was permitted/required, not proof that a particular company's statement became publicly available on that date.

M61 must use the actual disclosure/publication evidence for each accepted snapshot.

## Current research evidence

- The FRA currently publishes regulatory notices concerning listed-company financial-statement filing deadlines. A 2026 notice explicitly covers listed companies and describes deadlines for periodic consolidated statements. This is useful as regulatory context, but is not itself a company financial dataset.
- Issuer investor-relations archives demonstrate that dated quarterly/annual financial statements can be exposed with publication dates. These archives are useful for cross-checking availability and document identity.
- AskBorsa currently states that it aggregates published financial statements for EGX-listed companies, provides normalized five-year data, and links figures back to source pages. It remains a third-party extraction/cross-check candidate rather than accepted primary provenance.

## Current status

**NOT ACCEPTED.**

The next executable step is to prove the point-in-time acquisition path for one complete cohort member end-to-end:

EGX disclosure -> publication evidence -> immutable document identity -> extracted metric -> available_at -> historical decision-date eligibility

Only after that path is reproducible should it be scaled across all ten symbols.

## Non-goals

This checkpoint does not:

- change Strategy v0;
- define new financial metrics;
- introduce look-ahead handling outside the existing DEC-127 boundary;
- substitute third-party normalized values for primary disclosure evidence;
- claim that current financial statements are valid for historical backtesting.
