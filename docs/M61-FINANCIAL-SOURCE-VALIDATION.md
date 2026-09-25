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

## COMI — first end-to-end evidence package

- **Internal symbol:** COMI
- **Issuer/security:** Commercial International Bank-Egypt (CIB) S.A.E.; EGX Reuters code COMI
- **Statement type:** consolidated
- **period_end:** 2024-12-31
- **Document:** CIB Annual Report 2024 / consolidated financial statements
- **Approval/publication evidence date:** 2025-02-18
- **available_at:** 2025-02-18 (date-level evidence; exact intraday publication time not established)
- **Evidence:** the consolidated statement says the financial statements were approved by the Board of Directors on February 18, 2025; the same issuer date is independently present on CIB's 4Q24 results release.
- **Primary-provenance status:** issuer evidence proven; EGX disclosure-chain linkage still **not proven**.
- **Point-in-time rule:** with date-level evidence only, do not make the statement eligible for a decision earlier on 2025-02-18; use the next eligible trading session unless exact intraday availability is later proven.
- **Raw checksum:** not yet recorded; generate from the legally storable source artifact before dataset freeze.
- **Metric extraction:** not yet promoted into the accepted historical dataset.

This is a provenance evidence success, not cohort-wide financial-source acceptance.

## Current status

**NOT ACCEPTED.**

Next:
1. establish matching EGX/FRA disclosure identity for COMI, if publicly retrievable;
2. generate/preserve checksum where licensing permits;
3. extract one required Strategy v0 metric deterministically;
4. prove decision-date eligibility;
5. repeat for the remaining nine symbols.

## Non-goals

This checkpoint does not change Strategy v0, define new financial metrics, introduce look-ahead handling outside DEC-127, substitute third-party normalized values for primary disclosure evidence, or claim current statements are valid for historical backtesting.

## Verified EGX/FRA boundary — 2026-09-25

Fresh public-source verification confirms that the current EGX site exposes separate **Disclosures** and **Financial Statements** areas alongside market-watch data. The live market-watch page identifies COMI by Reuters code. This is useful provenance evidence, but does not prove a complete historical COMI disclosure chain for 2021–2025.

References:
- https://beta.egx.com.eg/en/market/market-watch
- https://beta.egx.com.eg/en
- https://www.cibeg.com/en/investor-relations
