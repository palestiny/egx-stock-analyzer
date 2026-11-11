# EGX Daily-History Review Inventory — 2026-11-11

**Status:** Inventory only; independent source reconciliation is not complete.  
**Canonical input:** `data/market_history/egx_daily_history.csv`  
**Canonical Git blob:** `3c01a843c225d226dc49e7c302220a280cfafb57`  
**Canonical file SHA-256:** `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`  
**Canonical file size:** 101,315 bytes  
**Audit workflow:** [run #42946596578](https://github.com/palestiny/egx-stock-analyzer/actions/runs/42946596578)  
**Audit artifact:** `13823266584` (generated from audit-tool PR head `a747e775e2acf239f4b07b1ebf7cf9f445bf1369`)

## 1. Verified structural snapshot

The read-only GitHub Actions audit completed with findings:

| Measure | Result |
|---|---:|
| Parsed rows | 255 |
| Symbols | 61 |
| Sessions | 31 |
| Session range | 2026-09-28 to 2026-11-10 |
| Malformed rows | 0 |
| Duplicate keys | 0 |
| Structurally invalid/rejected rows | 0 |
| OHLC geometry exceptions | 51 |
| Source-conflict review rows | 18 |
| Source-revision conflict rows | 1 |
| Total review queue | 70 |
| Structural candidates only | 185 |

Classification counts: `ohlc_inconsistency_review=51`, `source_conflict_review=18`, and `source_revision_conflict=1`.

The 51 OHLC exceptions comprise 48 rows where open is below low and three where open is above high. The audit does not determine which field or source is wrong.

The 185 structural candidates are **not source-authenticated**. Audit output explicitly records `analysis_eligibility=STRUCTURAL_CANDIDATE_ONLY_NOT_SOURCE_AUTHENTICATED` and `source_authenticity=NOT_INDEPENDENTLY_VERIFIED`.

## 2. Missing-field and retrieval-precision findings

| Field/metadata | Rows |
|---|---:|
| Missing traded value | 255 |
| Missing executions count | 255 |
| Missing volume | 23 |
| Timezone-aware retrieval timestamp | 233 |
| Date-only retrieval metadata | 22 |

All 22 date-only retrieval values belong to the initial EGAL seed and carry the unchanged retrieval date `2026-10-28`. No time or timezone is inferred.

### Date-only retrieval rows

| CSV row | Session date | Symbol | Retrieved at |
|---:|---|---|---|
| 2 | 2026-10-28 | EGAL | 2026-10-28 |
| 3 | 2026-10-27 | EGAL | 2026-10-28 |
| 4 | 2026-10-26 | EGAL | 2026-10-28 |
| 5 | 2026-10-25 | EGAL | 2026-10-28 |
| 6 | 2026-10-22 | EGAL | 2026-10-28 |
| 7 | 2026-10-21 | EGAL | 2026-10-28 |
| 8 | 2026-10-20 | EGAL | 2026-10-28 |
| 9 | 2026-10-19 | EGAL | 2026-10-28 |
| 10 | 2026-10-18 | EGAL | 2026-10-28 |
| 11 | 2026-10-15 | EGAL | 2026-10-28 |
| 12 | 2026-10-14 | EGAL | 2026-10-28 |
| 13 | 2026-10-13 | EGAL | 2026-10-28 |
| 14 | 2026-10-12 | EGAL | 2026-10-28 |
| 15 | 2026-10-11 | EGAL | 2026-10-28 |
| 16 | 2026-10-07 | EGAL | 2026-10-28 |
| 17 | 2026-10-06 | EGAL | 2026-10-28 |
| 18 | 2026-10-05 | EGAL | 2026-10-28 |
| 19 | 2026-10-04 | EGAL | 2026-10-28 |
| 20 | 2026-10-01 | EGAL | 2026-10-28 |
| 21 | 2026-09-30 | EGAL | 2026-10-28 |
| 22 | 2026-09-29 | EGAL | 2026-10-28 |
| 23 | 2026-09-28 | EGAL | 2026-10-28 |

## 3. Row-level review queue

CSV row numbers below include the header as row 1. Original OHLC values, retrieval metadata, and source URLs are transcribed from the canonical CSV without alteration.

Every item remains pending evidence review. This inventory does not assign a formal confirmation, rejection, alternative value, or waiver.

| CSV row | Session | Symbol | Review class | Open | High | Low | Close | Geometry | Retrieved at | Original source |
|---:|---|---|---|---:|---:|---:|---:|---|---|---|
| 2 | 2026-10-28 | EGAL | Source revision conflict | 303.50 | 307.00 | 301.00 | 303.01 | — | 2026-10-28 | [source](https://ng.investing.com/equities/egypt-aluminum-historical-data) |
| 25 | 2026-10-29 | MICH | OHLC inconsistency | 40.57 | 41.44 | 40.60 | 40.60 | Open < Low | 2026-10-29T19:53:01+03:00 | [source](https://ng.investing.com/equities/misr-chem-indu-historical-data) |
| 42 | 2026-10-29 | FAIT | OHLC inconsistency | 43.07 | 43.70 | 43.30 | 43.40 | Open < Low | 2026-10-29T19:53:01+03:00 | [source](https://ng.investing.com/equities/faisal-islmc-e-historical-data) |
| 56 | 2026-11-01 | VERT | Source conflict | 4.2 | 4.37 | 3.88 | 4.05 | — | 2026-11-01T19:40:41+02:00 | [source](https://ng.investing.com/equities/vertika-historical-data) |
| 67 | 2026-11-01 | EGX30 | Source conflict | 49507.2 | 49650.94 | 48557.54 | 48744.01 | — | 2026-11-01T19:40:41+02:00 | [source](https://ng.investing.com/indices/egx30-historical-data) |
| 68 | 2026-11-01 | EGX30CAP | Source conflict | 61608.91 | 61772.33 | 60450.89 | 60676.62 | — | 2026-11-01T19:40:41+02:00 | [source](https://ng.investing.com/indices/egx-20-capped-historical-data) |
| 69 | 2026-11-01 | EGX33 | Source conflict | 5903.61 | 5926.48 | 5835.49 | 5861.52 | — | 2026-11-01T19:40:41+02:00 | [source](https://ng.investing.com/indices/egx-33-shariah-compliant-index-historical-data) |
| 78 | 2026-11-02 | ABUK | OHLC inconsistency | 84.55 | 85.5 | 84.6 | 84.97 | Open < Low | 2026-11-02T19:08:12+02:00 | [source](https://ng.investing.com/equities/abou-kir-fertilizers-historical-data) |
| 81 | 2026-11-02 | ETEL | OHLC inconsistency | 117.82 | 123.06 | 118 | 119.82 | Open < Low | 2026-11-02T19:08:12+02:00 | [source](https://ng.investing.com/equities/telecom-egypt-historical-data) |
| 95 | 2026-11-02 | CIEB | Source conflict | 22.64 | 22.9 | 22.35 | 22.5 | — | 2026-11-02T19:08:12+02:00 | [source](https://www.investing.com/equities/credit-agricol-historical-data) |
| 96 | 2026-11-02 | ELEC | Source conflict | 1.5 | 1.55 | 1.48 | 1.49 | — | 2026-11-02T19:08:12+02:00 | [source](https://www.investing.com/equities/electro-cable-historical-data) |
| 97 | 2026-11-02 | FAIT | Source conflict | 43.2 | 43.67 | 43.2 | 43.6 | — | 2026-11-02T19:08:12+02:00 | [source](https://pl.investing.com/equities/faisal-islmc-e-historical-data) |
| 98 | 2026-11-02 | EGX30 | Source conflict | 48744.01 | 49295.7 | 47791.47 | 48403.14 | — | 2026-11-02T19:08:12+02:00 | [source](https://ng.investing.com/indices/egx30-historical-data) |
| 106 | 2026-11-02 | EGX100EWI | OHLC inconsistency | 22410.52 | 22442.14 | 22426.26 | 22434.64 | Open < Low | 2026-11-02T19:08:12+02:00 | [source](https://ng.investing.com/indices/egx-100-ewi-historical-data) |
| 115 | 2026-11-03 | COMI | OHLC inconsistency | 121.40 | 123.00 | 121.51 | 123.00 | Open < Low | 2026-11-03T19:11:18+02:00 | [source](https://ng.investing.com/equities/com-intl-bk-historical-data) |
| 127 | 2026-11-03 | EGX30 | Source conflict | 48403.14 | 49255.66 | 48029.83 | 49255.66 | — | 2026-11-03T19:11:18+02:00 | [source](https://ng.investing.com/indices/egx30-historical-data) |
| 137 | 2026-11-03 | EGBASC | OHLC inconsistency | 4623.49 | 4585.49 | 4505.27 | 4521.70 | Open > High | 2026-11-03T19:11:18+02:00 | [source](https://ng.investing.com/indices/egx-basic-r-historical-data) |
| 138 | 2026-11-04 | EGAL | OHLC inconsistency | 303.00 | 328.99 | 307.00 | 318.19 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/egypt-aluminum-historical-data) |
| 139 | 2026-11-04 | ALUM | OHLC inconsistency | 18.49 | 19.50 | 18.61 | 19.10 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/arab-aluminum-historical-data) |
| 140 | 2026-11-04 | FWRY | OHLC inconsistency | 16.12 | 16.95 | 16.25 | 16.94 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/fawry-banking-and-payment-historical-data) |
| 141 | 2026-11-04 | ETEL | Source conflict | 122.88 | 126.50 | 122.80 | 126.10 | — | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/telecom-egypt-historical-data) |
| 142 | 2026-11-04 | ABUK | OHLC inconsistency | 77.71 | 79.24 | 77.95 | 79.00 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/abou-kir-fertilizers-historical-data) |
| 144 | 2026-11-04 | EFIC | OHLC inconsistency | 136.40 | 142.00 | 137.00 | 141.98 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/egyptian-fin-i-historical-data) |
| 145 | 2026-11-04 | EGCH | OHLC inconsistency | 9.94 | 10.35 | 10.00 | 10.34 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/egypt-chem-ind-historical-data) |
| 146 | 2026-11-04 | MBSC | OHLC inconsistency | 311.02 | 318.80 | 313.10 | 316.00 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/misr-beni-suef-cement-historical-data) |
| 147 | 2026-11-04 | PHAR | OHLC inconsistency | 98.40 | 101.80 | 99.35 | 100.40 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/egypt-intl-phr-historical-data) |
| 150 | 2026-11-04 | MFPC | OHLC inconsistency | 40.07 | 41.18 | 40.10 | 40.68 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/misr-fertilizers-production-co-sae-historical-data) |
| 151 | 2026-11-04 | SWDY | OHLC inconsistency | 108.60 | 113.00 | 110.51 | 112.00 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/elsewedy-cable-historical-data) |
| 152 | 2026-11-04 | CANA | OHLC inconsistency | 45.32 | 46.00 | 45.60 | 45.96 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/suez-canal-ban-historical-data) |
| 153 | 2026-11-04 | ELEC | OHLC inconsistency | 1.540 | 1.610 | 1.550 | 1.600 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/electro-cable-historical-data) |
| 154 | 2026-11-04 | ORHD | OHLC inconsistency | 10.15 | 10.50 | 10.25 | 10.35 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/orascom-hotels-and-development-historical-data) |
| 155 | 2026-11-04 | JUFO | OHLC inconsistency | 23.00 | 24.22 | 23.10 | 23.89 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/juhayna-food-industries-historical-data) |
| 156 | 2026-11-04 | ORAS | OHLC inconsistency | 790.05 | 812.00 | 796.10 | 802.00 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) |
| 157 | 2026-11-04 | EGX30 | OHLC inconsistency | 49255.66 | 50650.18 | 49481.62 | 50650.18 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/indices/egx30-historical-data) |
| 158 | 2026-11-04 | EGX70EWI | OHLC inconsistency | 16648.16 | 16999.56 | 16700.27 | 16964.17 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/indices/egx-70-historical-data) |
| 159 | 2026-11-04 | EGX100EWI | OHLC inconsistency | 22344.10 | 23011.03 | 22433.40 | 23011.03 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/indices/egx-100-ewi-historical-data) |
| 160 | 2026-11-04 | EGX33 | OHLC inconsistency | 5907.64 | 6028.54 | 5928.22 | 6025.85 | Open < Low | 2026-11-04T19:04:48+02:00 | [source](https://ph.investing.com/indices/egx-33-shariah-compliant-index-historical-data) |
| 165 | 2026-11-05 | ABUK | OHLC inconsistency | 80 | 82.39 | 80.34 | 80.79 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/abou-kir-fertilizers-historical-data) |
| 167 | 2026-11-05 | ETEL | OHLC inconsistency | 128 | 132.79 | 129.01 | 131.44 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/telecom-egypt-historical-data) |
| 168 | 2026-11-05 | COMI | OHLC inconsistency | 126.51 | 128.95 | 126.52 | 128.79 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/com-intl-bk-historical-data) |
| 170 | 2026-11-05 | RAYA | OHLC inconsistency | 5.45 | 5.65 | 5.47 | 5.58 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/raya-tech---co-historical-data) |
| 172 | 2026-11-05 | ACAP | OHLC inconsistency | 6.99 | 7.3 | 7.05 | 7.15 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/a-capital-holding-historical-data) |
| 173 | 2026-11-05 | RACC | OHLC inconsistency | 7.8 | 7.98 | 7.81 | 7.9 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/raya-contact-center-historical-data) |
| 177 | 2026-11-05 | FWRY | Source conflict | 17.1 | 17.38 | 17.01 | 17.32 | — | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/fawry-banking-and-payment-historical-data) |
| 178 | 2026-11-05 | EGX30 | Source conflict | 50841.01 | 51546.16 | 50837.31 | 51152.73 | — | 2026-11-05T19:52:01+02:00 | [source](https://tr.investing.com/indices/egx30-historical-data) |
| 179 | 2026-11-05 | EGX30CAP | Source conflict | 62912.21 | 63726.68 | 62906.63 | 63261.74 | — | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/indices/egx-20-capped-historical-data) |
| 182 | 2026-11-05 | EGX70EWI | OHLC inconsistency | 17151.55 | 17572.72 | 17188.25 | 17567.23 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://ph.investing.com/indices/egx-70-historical-data) |
| 183 | 2026-11-05 | EGX100EWI | OHLC inconsistency | 23011.03 | 23504.43 | 23067.81 | 23494.05 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://ca.investing.com/indices/egx-100-ewi-historical-data) |
| 184 | 2026-11-05 | TMGH | OHLC inconsistency | 81.08 | 84.50 | 81.60 | 84.30 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://www.investing.com/equities/t-m-g-holding-historical-data) |
| 185 | 2026-11-05 | ADIB | Source conflict | 49.50 | 50.49 | 49.01 | 49.01 | — | 2026-11-05T19:52:01+02:00 | [source](https://za.investing.com/equities/abu-dhabi-islamic-bank-egypt-historical-data) |
| 186 | 2026-11-05 | ORAS | OHLC inconsistency | 797.02 | 815.00 | 805.00 | 810.02 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) |
| 187 | 2026-11-05 | HELI | OHLC inconsistency | 6.61 | 6.97 | 6.62 | 6.94 | Open < Low | 2026-11-05T19:52:01+02:00 | [source](https://ca.investing.com/equities/heliopolis-housing-historical-data) |
| 203 | 2026-11-08 | ORAS | Source conflict | 810.02 | 818.40 | 800.01 | 801.00 | — | 2026-11-08T19:45:44+02:00 | [source](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) |
| 204 | 2026-11-08 | HELI | Source conflict | 6.94 | 7.09 | 6.74 | 6.90 | — | 2026-11-08T19:45:44+02:00 | [source](https://ca.investing.com/equities/heliopolis-housing-historical-data) |
| 205 | 2026-11-08 | EGX30 | OHLC inconsistency | 51152.73 | 51030.09 | 50426.32 | 50812.07 | Open > High | 2026-11-08T19:45:44+02:00 | [source](https://nl.investing.com/indices/egx30-historical-data) |
| 206 | 2026-11-08 | EGX30CAP | OHLC inconsistency | 63219.99 | 63034.92 | 62216.59 | 62781.23 | Open > High | 2026-11-08T19:45:44+02:00 | [source](https://www.investing.com/indices/egx-20-capped-historical-data) |
| 217 | 2026-11-09 | PHDC | Source conflict | 12.010 | 12.100 | 11.940 | 11.940 | — | 2026-11-09T19:41:47+02:00 | [source](https://www.investing.com/equities/palm-hill-dev-historical-data) |
| 228 | 2026-11-09 | EGX30 | Source conflict | 50841.73 | 51432.95 | 50831.06 | 51414.93 | — | 2026-11-09T19:41:47+02:00 | [source](https://www.investing.com/indices/egx30-historical-data) |
| 229 | 2026-11-09 | EGX30CAP | OHLC inconsistency | 62781.23 | 63610.19 | 62836.13 | 63610.19 | Open < Low | 2026-11-09T19:41:47+02:00 | [source](https://www.investing.com/indices/egx-20-capped-historical-data) |
| 230 | 2026-11-09 | SHARIAH | OHLC inconsistency | 6117.71 | 6234.38 | 6131.15 | 6222.51 | Open < Low | 2026-11-09T19:41:47+02:00 | [source](https://www.investing.com/indices/egx-33-shariah-compliant-index-historical-data) |
| 232 | 2026-11-09 | EGX70EWI | OHLC inconsistency | 17687.34 | 17959.58 | 17719.01 | 17959.58 | Open < Low | 2026-11-09T19:41:47+02:00 | [source](https://www.investing.com/indices/egx-70-historical-data) |
| 233 | 2026-11-09 | EGX100EWI | OHLC inconsistency | 23526.51 | 23869.07 | 23568.12 | 23869.07 | Open < Low | 2026-11-09T19:41:47+02:00 | [source](https://www.investing.com/indices/egx-100-ewi-historical-data) |
| 244 | 2026-11-10 | HDBK | OHLC inconsistency | 99.46 | 104.64 | 100.00 | 102.81 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://www.investing.com/equities/housing---dev-historical-data) |
| 246 | 2026-11-10 | ORAS | OHLC inconsistency | 795.94 | 832.00 | 797.10 | 815.15 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://www.investing.com/equities/orascom-construction-ltd-historical-data) |
| 247 | 2026-11-10 | PHDC | OHLC inconsistency | 11.880 | 12.100 | 11.930 | 12.070 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://ph.investing.com/equities/palm-hill-dev-historical-data) |
| 249 | 2026-11-10 | RAYA | OHLC inconsistency | 5.88 | 6.28 | 5.94 | 6.25 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://www.investing.com/equities/raya-tech---co-historical-data) |
| 250 | 2026-11-10 | TMGH | OHLC inconsistency | 83.50 | 86.48 | 83.75 | 86.00 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://www.investing.com/equities/t-m-g-holding-historical-data) |
| 251 | 2026-11-10 | EGX30 | OHLC inconsistency | 51414.93 | 52508.16 | 51542.88 | 52483.46 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://www.investing.com/indices/egx30-historical-data) |
| 255 | 2026-11-10 | EGX70EWI | OHLC inconsistency | 17959.58 | 18495.97 | 17999.03 | 18495.97 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://www.investing.com/indices/egx-70-historical-data) |
| 256 | 2026-11-10 | EGX100EWI | OHLC inconsistency | 23869.07 | 24495.46 | 23939.07 | 24495.46 | Open < Low | 2026-11-10T19:16:35+02:00 | [source](https://www.investing.com/indices/egx-100-ewi-historical-data) |

## 4. Preserved source-conflict notes

The notes below retain the conflict descriptions already present in the canonical CSV. They are observations and comparison leads, not independently verified conclusions. Localized pages from Investing.com remain same-provider evidence and are not independent corroboration.

| CSV row | Session | Symbol | Original canonical note | Selected source |
|---:|---|---|---|---|
| 2 | 2026-10-28 | EGAL | Archived values retained. Current same-provider page shows open=305.00 high=307.20 volume=191.13K versus archived open=303.50 high=307.00 volume=189.55K. Reconciliation pending. | [source](https://ng.investing.com/equities/egypt-aluminum-historical-data) |
| 56 | 2026-11-01 | VERT | Historical-data table reports close=4.050 and volume=224.90K; another Investing.com quote result showed 4.130 and 177.65K. Preserved the historical-table row pending reconciliation. | [source](https://ng.investing.com/equities/vertika-historical-data) |
| 67 | 2026-11-01 | EGX30 | Source displayed volume=222.10M, normalized to thousands. Other Investing.com result variants reported a different open and/or volume for this date; values retained from the NG historical-data result pending reconciliation. | [source](https://ng.investing.com/indices/egx30-historical-data) |
| 68 | 2026-11-01 | EGX30CAP | Source displayed volume=222.10M, normalized to thousands. Other Investing.com result variants reported a different open and/or volume for this date; values retained from the NG historical-data result pending reconciliation. | [source](https://ng.investing.com/indices/egx-20-capped-historical-data) |
| 69 | 2026-11-01 | EGX33 | Source displayed volume=126.07M, normalized to thousands. Another Investing.com result variant reported close=5876.90 with different range and volume; retained this historical-data result pending reconciliation. | [source](https://ng.investing.com/indices/egx-33-shariah-compliant-index-historical-data) |
| 95 | 2026-11-02 | CIEB | Selected global Investing.com table reports close=22.50 and volume=220.37K. Another regional Investing.com result reports close=22.48 and volume=315.61K; retain selected row pending reconciliation. | [source](https://www.investing.com/equities/credit-agricol-historical-data) |
| 96 | 2026-11-02 | ELEC | Selected global Investing.com table reports close=1.490 and volume=21.89M. Other regional results report materially different close and volume; retain selected row pending reconciliation. | [source](https://www.investing.com/equities/electro-cable-historical-data) |
| 97 | 2026-11-02 | FAIT | Polish Investing.com result reports close=43.60 and volume=3.66K. Turkish result reports close=42.50 and volume=16.13K; retain selected row pending reconciliation. | [source](https://pl.investing.com/equities/faisal-islmc-e-historical-data) |
| 98 | 2026-11-02 | EGX30 | Source displayed volume=202.52M normalized to thousands. Another retrieved Investing.com result variant reported close=47,862.37 and volume=162.94M; preserve this selected result pending reconciliation. | [source](https://ng.investing.com/indices/egx30-historical-data) |
| 127 | 2026-11-03 | EGX30 | Source displayed volume=176.08M; normalized to thousands in volume_thousands_reported. Selected NG historical table reports these values. Other regional Investing.com result variants disagree on the 2026-11-03 close and/or volume; reconciliation pending. | [source](https://ng.investing.com/indices/egx30-historical-data) |
| 141 | 2026-11-04 | ETEL | Source-displayed volume=943.95K normalized to thousands. Page header quote/change differs from historical table close/change; historical table OHLC is internally consistent. | [source](https://ph.investing.com/equities/telecom-egypt-historical-data) |
| 177 | 2026-11-05 | FWRY | Main historical table reports 17.32 close and 1.68M volume; PH and CA locales report 17.36 and about 6.1-6.2M volume. Preserve selected page values pending reconciliation. | [source](https://www.investing.com/equities/fawry-banking-and-payment-historical-data) |
| 178 | 2026-11-05 | EGX30 | Selected Turkish historical row has internally consistent OHLC and 51,152.73 close, corroborated by same-day Egyptian market recap; other localized pages disagree on open and volume. Source displayed volume 260.89M is normalized to thousands; index-volume meaning is not independently validated. | [source](https://tr.investing.com/indices/egx30-historical-data) |
| 179 | 2026-11-05 | EGX30CAP | Selected main-page historical row is internally consistent; CA locale shows a different close/open/volume for the same date. Preserve selected page values pending reconciliation. | [source](https://www.investing.com/indices/egx-20-capped-historical-data) |
| 185 | 2026-11-05 | ADIB | Selected ZA historical row reports 49.01 close and 2.56M volume, matching same-day market recap change near -1.0%; main-domain historical page reports 50.00 close and 1.64M volume. Preserve selected page pending reconciliation. | [source](https://za.investing.com/equities/abu-dhabi-islamic-bank-egypt-historical-data) |
| 203 | 2026-11-08 | ORAS | Selected PH historical row reports close=801.00 and volume=124.43K. An Italian localized page reports close=811.00 and volume=1.94K (+0.12%). Preserved the PH row pending reconciliation; volume normalized to thousands. | [source](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) |
| 204 | 2026-11-08 | HELI | Selected CA historical row reports close=6.90 and volume=5.68M (-0.58%). A Dutch localized page reports close=6.88 and volume=5.47M (-0.86%). Preserved the CA row pending reconciliation; volume normalized to thousands. | [source](https://ca.investing.com/equities/heliopolis-housing-historical-data) |
| 217 | 2026-11-09 | PHDC | Source displayed volume=2.02M; normalized to thousands. Per-security traded value and execution count were not supplied by the retrieved daily row. Selected English historical row reports close=11.940, low=11.940, volume=2.02M and -0.58%. A Philippines-localized Investing.com page reports close=11.900, low=11.820, volume=5.33M and -0.92%. Preserved the selected English row pending reconciliation. | [source](https://www.investing.com/equities/palm-hill-dev-historical-data) |
| 228 | 2026-11-09 | EGX30 | Source displayed index-page volume=186.17M; normalized to thousands. Index-page volume comparability is not independently verified; per-instrument traded value and execution count were not supplied. Selected English historical row reports open=50,841.73, high=51,432.95, low=50,831.06, close=51,414.93 and volume=186.17M. NG-localized page reports different open/high/low (50,812.07/51,433.14/50,827.90) with the same close, change and volume. Preserved English row pending reconciliation; index-page volume comparability is unverified. | [source](https://www.investing.com/indices/egx30-historical-data) |

## 5. Evidence and disposition rules

Follow `docs/EGX-DAILY-HISTORY-RECONCILIATION-PROTOCOL.md`:

1. Preserve the canonical CSV and all original source values.
2. Prefer official EGX evidence, then contractually authorized provider evidence, then independent secondary evidence.
3. Do not count two locales/pages from the same provider as independent corroboration.
4. Compare instrument identity, session date, OHLC, units, volume semantics, adjusted/unadjusted convention, and revision metadata field by field.
5. Record raw evidence identity/checksum, retrieval timestamp, source independence, reviewer, rationale, and one disposition per review item.
6. A geometrically valid OHLC bar is not proof of source accuracy. A mismatch with another provider is not, by itself, proof of invalidity.
7. Keep unresolved/review rows excluded from clean OHLC analysis and backtesting until the relevant evidence and acceptance checks pass.

## 6. Downstream boundary

- No source data was changed by this inventory.
- No price, volume, traded value, or executions count was repaired or inferred.
- No provider was selected or approved.
- No ingestion or automatic correction is authorized.
- No row is promoted to authenticated analysis or backtesting eligibility.
- M61 remains paused pending the separate historical-data acceptance gate.

**Audit interpretation:** structural validation passed its format/arithmetic checks with 70 explicit findings; source authenticity and row-level reconciliation remain open.
