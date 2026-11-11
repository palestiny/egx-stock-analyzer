# 4–5 November 2026 OHLC Evidence Register

**Status:** Read-only evidence index; no row is reconciled or accepted.  
**Baseline branch:** `main` at `cec112d9a350eb07cffbf3959726ba78e7767cf7`  
**Canonical input:** `data/market_history/egx_daily_history.csv`  
**Canonical blob:** `3c01a843c225d226dc49e7c302220a280cfafb57`  
**Canonical SHA-256:** `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`  
**Canonical size:** 101,315 bytes  
**Recorded retrieval batches:** 2026-11-04 `19:04:48+02:00`; 2026-11-05 `19:52:01+02:00`.

## 1. Purpose and scope

This register turns the existing collection README and forensic triage into a row-addressable evidence checklist for the two largest adjacent collection batches. It transcribes canonical CSV values only. It does not re-fetch historical pages, establish what a page displayed at retrieval time, infer a corrected value, or identify a root cause.

The CSV parser found **30 OHLC geometry exceptions** in these two batches: 19 on 4 November and 11 on 5 November. These are included in the repository's 51-row OHLC exception set. The following controls have source/page-header conflict notes but internally consistent stored OHLC: 2026-11-04 ETEL, 2026-11-05 FWRY, 2026-11-05 EGX30, 2026-11-05 EGX30CAP, 2026-11-05 ADIB.

## 2. Canonical row evidence — OHLC geometry exceptions

Geometry rule applied: `low <= open <= high` and `low <= close <= high`. A violation is a review trigger, not proof of which field is wrong.

| CSV row | Session | Symbol | Instrument / unit | Open | High | Low | Close | Current quality label | Recorded source page |
|---:|---|---|---|---:|---:|---:|---:|---|---|
| 138 | 2026-11-04 | EGAL | equity (EGP) | 303.00 | 328.99 | 307.00 | 318.19 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/egypt-aluminum-historical-data) |
| 139 | 2026-11-04 | ALUM | equity (EGP) | 18.49 | 19.50 | 18.61 | 19.10 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/arab-aluminum-historical-data) |
| 140 | 2026-11-04 | FWRY | equity (EGP) | 16.12 | 16.95 | 16.25 | 16.94 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/fawry-banking-and-payment-historical-data) |
| 142 | 2026-11-04 | ABUK | equity (EGP) | 77.71 | 79.24 | 77.95 | 79.00 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/abou-kir-fertilizers-historical-data) |
| 144 | 2026-11-04 | EFIC | equity (EGP) | 136.40 | 142.00 | 137.00 | 141.98 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/egyptian-fin-i-historical-data) |
| 145 | 2026-11-04 | EGCH | equity (EGP) | 9.94 | 10.35 | 10.00 | 10.34 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/egypt-chem-ind-historical-data) |
| 146 | 2026-11-04 | MBSC | equity (EGP) | 311.02 | 318.80 | 313.10 | 316.00 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/misr-beni-suef-cement-historical-data) |
| 147 | 2026-11-04 | PHAR | equity (EGP) | 98.40 | 101.80 | 99.35 | 100.40 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/egypt-intl-phr-historical-data) |
| 150 | 2026-11-04 | MFPC | equity (EGP) | 40.07 | 41.18 | 40.10 | 40.68 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/misr-fertilizers-production-co-sae-historical-data) |
| 151 | 2026-11-04 | SWDY | equity (EGP) | 108.60 | 113.00 | 110.51 | 112.00 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/elsewedy-cable-historical-data) |
| 152 | 2026-11-04 | CANA | equity (EGP) | 45.32 | 46.00 | 45.60 | 45.96 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/suez-canal-ban-historical-data) |
| 153 | 2026-11-04 | ELEC | equity (EGP) | 1.540 | 1.610 | 1.550 | 1.600 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/electro-cable-historical-data) |
| 154 | 2026-11-04 | ORHD | equity (EGP) | 10.15 | 10.50 | 10.25 | 10.35 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/orascom-hotels-and-development-historical-data) |
| 155 | 2026-11-04 | JUFO | equity (EGP) | 23.00 | 24.22 | 23.10 | 23.89 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/juhayna-food-industries-historical-data) |
| 156 | 2026-11-04 | ORAS | equity (EGP) | 790.05 | 812.00 | 796.10 | 802.00 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) |
| 157 | 2026-11-04 | EGX30 | index (points) | 49255.66 | 50650.18 | 49481.62 | 50650.18 | ohlc_inconsistency_review | [page](https://ph.investing.com/indices/egx30-historical-data) |
| 158 | 2026-11-04 | EGX70EWI | index (points) | 16648.16 | 16999.56 | 16700.27 | 16964.17 | ohlc_inconsistency_review | [page](https://ph.investing.com/indices/egx-70-historical-data) |
| 159 | 2026-11-04 | EGX100EWI | index (points) | 22344.10 | 23011.03 | 22433.40 | 23011.03 | ohlc_inconsistency_review | [page](https://ph.investing.com/indices/egx-100-ewi-historical-data) |
| 160 | 2026-11-04 | EGX33 | index (points) | 5907.64 | 6028.54 | 5928.22 | 6025.85 | ohlc_inconsistency_review | [page](https://ph.investing.com/indices/egx-33-shariah-compliant-index-historical-data) |
| 165 | 2026-11-05 | ABUK | equity (EGP) | 80 | 82.39 | 80.34 | 80.79 | ohlc_inconsistency_review | [page](https://www.investing.com/equities/abou-kir-fertilizers-historical-data) |
| 167 | 2026-11-05 | ETEL | equity (EGP) | 128 | 132.79 | 129.01 | 131.44 | ohlc_inconsistency_review | [page](https://www.investing.com/equities/telecom-egypt-historical-data) |
| 168 | 2026-11-05 | COMI | equity (EGP) | 126.51 | 128.95 | 126.52 | 128.79 | ohlc_inconsistency_review | [page](https://www.investing.com/equities/com-intl-bk-historical-data) |
| 170 | 2026-11-05 | RAYA | equity (EGP) | 5.45 | 5.65 | 5.47 | 5.58 | ohlc_inconsistency_review | [page](https://www.investing.com/equities/raya-tech---co-historical-data) |
| 172 | 2026-11-05 | ACAP | equity (EGP) | 6.99 | 7.3 | 7.05 | 7.15 | ohlc_inconsistency_review | [page](https://www.investing.com/equities/a-capital-holding-historical-data) |
| 173 | 2026-11-05 | RACC | equity (EGP) | 7.8 | 7.98 | 7.81 | 7.9 | ohlc_inconsistency_review | [page](https://www.investing.com/equities/raya-contact-center-historical-data) |
| 182 | 2026-11-05 | EGX70EWI | index (points) | 17151.55 | 17572.72 | 17188.25 | 17567.23 | ohlc_inconsistency_review | [page](https://ph.investing.com/indices/egx-70-historical-data) |
| 183 | 2026-11-05 | EGX100EWI | index (points) | 23011.03 | 23504.43 | 23067.81 | 23494.05 | ohlc_inconsistency_review | [page](https://ca.investing.com/indices/egx-100-ewi-historical-data) |
| 184 | 2026-11-05 | TMGH | equity (EGP) | 81.08 | 84.50 | 81.60 | 84.30 | ohlc_inconsistency_review | [page](https://www.investing.com/equities/t-m-g-holding-historical-data) |
| 186 | 2026-11-05 | ORAS | equity (EGP) | 797.02 | 815.00 | 805.00 | 810.02 | ohlc_inconsistency_review | [page](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) |
| 187 | 2026-11-05 | HELI | equity (EGP) | 6.61 | 6.97 | 6.62 | 6.94 | ohlc_inconsistency_review | [page](https://ca.investing.com/equities/heliopolis-housing-historical-data) |

## 3. Source-conflict controls and overlapping concerns

These are not additional OHLC geometry exceptions unless also listed in section 2. Their purpose is to prevent the investigation from treating one geometry rule as the only issue.

| CSV row | Session | Symbol | Stored OHLC (O / H / L / C) | Recorded concern | Source page |
|---:|---|---|---|---|---|
| 141 | 2026-11-04 | ETEL | 122.88 / 126.50 / 122.80 / 126.10 | Source-displayed volume=943.95K normalized to thousands. Page header quote/change differs from historical table close/change; historical table OHLC is internally consistent. | [page](https://ph.investing.com/equities/telecom-egypt-historical-data) |
| 177 | 2026-11-05 | FWRY | 17.1 / 17.38 / 17.01 / 17.32 | Main historical table reports 17.32 close and 1.68M volume; PH and CA locales report 17.36 and about 6.1-6.2M volume. Preserve selected page values pending reconciliation. | [page](https://www.investing.com/equities/fawry-banking-and-payment-historical-data) |
| 178 | 2026-11-05 | EGX30 | 50841.01 / 51546.16 / 50837.31 / 51152.73 | Selected Turkish historical row has internally consistent OHLC and 51,152.73 close, corroborated by same-day Egyptian market recap; other localized pages disagree on open and volume. Source displayed volume 260.89M is normalized to thousands; index-volume meaning is not independently validated. | [page](https://tr.investing.com/indices/egx30-historical-data) |
| 179 | 2026-11-05 | EGX30CAP | 62912.21 / 63726.68 / 62906.63 / 63261.74 | Selected main-page historical row is internally consistent; CA locale shows a different close/open/volume for the same date. Preserve selected page values pending reconciliation. | [page](https://www.investing.com/indices/egx-20-capped-historical-data) |
| 185 | 2026-11-05 | ADIB | 49.50 / 50.49 / 49.01 / 49.01 | Selected ZA historical row reports 49.01 close and 2.56M volume, matching same-day market recap change near -1.0%; main-domain historical page reports 50.00 close and 1.64M volume. Preserve selected page pending reconciliation. | [page](https://za.investing.com/equities/abu-dhabi-islamic-bank-egypt-historical-data) |

The README separately records page-header versus historical-table discrepancies for 4 November `ETEL`, `FWRY`, `PHAR`, and `MFPC`; for 5 November it records localized-page differences for `ABUK`, `ETEL`, `COMI`, `RAYA`, `FWRY`, and `ADIB`. Some concerns overlap the geometry rows above. The exact original page payloads/screenshots are not stored in the canonical archive.

## 4. What the repository evidence proves — and does not prove

### Proves

- The canonical archive contains the exact values, row identities, source URL strings, quality labels, and retrieval timestamps transcribed above.
- The 4 and 5 November records were captured in two timestamp batches from Investing.com historical-data pages, as documented in `data/market_history/README.md`.
- The collection README reports both open/low geometry concerns and selected cross-locale or page-header/table differences.
- All cited localized pages belong to the same Investing.com provider family; locale variants are not independent source corroboration.

### Does not prove

- Which raw page response or DOM/table payload was actually read at the recorded retrieval timestamp.
- Whether the discrepancy originated in the source, page rendering, locale-specific response, parser/field selection, symbol mapping, session boundary, or another mechanism.
- Whether a different open, high, low, close, or volume value is correct.
- That a prior-close match is a corrected opening price.
- That index volume is economically comparable to equity share volume.
- That current page content is historically identical to content served at the recorded retrieval time.

## 5. Required evidence package per row

Before a disposition can be assigned, preserve an immutable evidence item with:

1. Exact instrument identity and type; equity ticker or index identifier.
2. Exact EGX session date and timezone/session boundary.
3. Authorized provider identity and delivery/reference identifier.
4. Original raw response/file or officially supplied statement, unchanged; capture timestamp and SHA-256.
5. Field dictionary and units for open/high/low/close/volume; explicit index-volume semantics.
6. Whether prices are raw, split-adjusted, dividend-adjusted, or otherwise transformed.
7. Original publication timestamp and any later correction/revision history.
8. Independent corroboration from a genuinely separate source, with its own provenance and rights; another Investing.com locale does not qualify.
9. Field-by-field comparison against the canonical row, with no silent substitution.
10. Reviewer, review time, protocol disposition, rationale, and second review for any proposed correction or rejection.

Preferred first route remains an authorized EGID sample/request. This register does not authorize contacting a provider, authenticating, buying a plan, downloading vendor data, or retaining material beyond an explicitly permitted scope.

## 6. Disposition rules

Use the existing `docs/EGX-DAILY-HISTORY-RECONCILIATION-PROTOCOL.md`. Until adequate evidence exists:

- Keep every original canonical value unchanged.
- Keep each flagged row excluded from clean OHLC calculations.
- Do not average localized values, substitute prior close, forward-fill, or infer missing data.
- Do not promote source authenticity or M61 eligibility.
- Keep unresolved status explicit; absence of evidence is not a pass.

## 7. Downstream boundary

This document is documentation-only. It does not modify `egx_daily_history.csv`, change application behavior, select a provider, create an adapter, ingest data, or activate M61. DEC-130 remains the acceptance gate; M61/backtesting remains paused.

**Next useful action:** obtain a dated, authorized sample covering a small set of these exact sessions plus clean control rows, then apply the evidence package in section 5 before assigning any row disposition.
