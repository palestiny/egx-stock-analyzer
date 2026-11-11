# EGX Daily-History Row Review Ledger

**Status:** Operational tracking ledger; all 70 items start `UNRESOLVED`.
**Canonical input:** `data/market_history/egx_daily_history.csv`
**Canonical Git blob:** `3c01a843c225d226dc49e7c302220a280cfafb57`
**Canonical file SHA-256:** `c2b6cc78dd2e661bc3936e9cac4891d8af0b93ce117a354e5c3638683efa4ef3`
**Canonical snapshot:** main commit `d15f4dee79ca80ef4aadbcee4e68323fc04c866a`
**Protocol:** `docs/EGX-DAILY-HISTORY-RECONCILIATION-PROTOCOL.md`

## Rules

- This ledger is a review queue, not a correction or acceptance record.
- Original OHLC and source metadata below are transcribed from the canonical snapshot; do not edit them in this ledger to make a row pass.
- `UNRESOLVED` is the initial disposition for every row. Do not change it without evidence and attributable human review.
- Record an exact evidence reference and artifact SHA-256 for each source artifact. Mark independence as `independent`, `same-provider`, or `unknown` with a reason.
- A disposition of `CONFIRMED_AS_REPORTED`, `CONFIRMED_ALTERNATIVE`, or `REJECTED_OBSERVATION` requires field-by-field evidence and a second reviewer for any proposed alternative/rejection.
- Blank market fields remain unavailable, not zero. This ledger does not authorize provider contact, credentials, purchase, ingestion, CSV edits, eligibility promotion, or M61 activation.

## Queue

| CSV row | Session | Symbol | Instrument | Class | Open | High | Low | Close | Unit | Retrieved at | Source | Disposition | Evidence ref | Evidence SHA-256 | Independence | Reviewer | Reviewed at | Rationale / follow-up |
|---:|---|---|---|---|---:|---:|---:|---:|---|---|---|---|---|---|---|---|---|---|
| 2 | 2026-10-28 | EGAL | equity | source_revision_conflict | 303.50 | 307.00 | 301.00 | 303.01 | EGP | 2026-10-28 | [Investing.com](https://ng.investing.com/equities/egypt-aluminum-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 3 | 2026-10-29 | MICH | equity | ohlc_inconsistency_review | 40.57 | 41.44 | 40.60 | 40.60 | EGP | 2026-10-29T19:53:01+03:00 | [Investing.com](https://ng.investing.com/equities/misr-chem-indu-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 4 | 2026-10-29 | FAIT | equity | ohlc_inconsistency_review | 43.07 | 43.70 | 43.30 | 43.40 | EGP | 2026-10-29T19:53:01+03:00 | [Investing.com](https://ng.investing.com/equities/faisal-islmc-e-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 5 | 2026-11-01 | VERT | equity | source_conflict_review | 4.2 | 4.37 | 3.88 | 4.05 | EGP | 2026-11-01T19:40:41+02:00 | [Investing.com](https://ng.investing.com/equities/vertika-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 6 | 2026-11-01 | EGX30 | index | source_conflict_review | 49507.2 | 49650.94 | 48557.54 | 48744.01 | points | 2026-11-01T19:40:41+02:00 | [Investing.com](https://ng.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 7 | 2026-11-01 | EGX30CAP | index | source_conflict_review | 61608.91 | 61772.33 | 60450.89 | 60676.62 | points | 2026-11-01T19:40:41+02:00 | [Investing.com](https://ng.investing.com/indices/egx-20-capped-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 8 | 2026-11-01 | EGX33 | index | source_conflict_review | 5903.61 | 5926.48 | 5835.49 | 5861.52 | points | 2026-11-01T19:40:41+02:00 | [Investing.com](https://ng.investing.com/indices/egx-33-shariah-compliant-index-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 9 | 2026-11-02 | ABUK | equity | ohlc_inconsistency_review | 84.55 | 85.5 | 84.6 | 84.97 | EGP | 2026-11-02T19:08:12+02:00 | [Investing.com](https://ng.investing.com/equities/abou-kir-fertilizers-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 10 | 2026-11-02 | ETEL | equity | ohlc_inconsistency_review | 117.82 | 123.06 | 118 | 119.82 | EGP | 2026-11-02T19:08:12+02:00 | [Investing.com](https://ng.investing.com/equities/telecom-egypt-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 11 | 2026-11-02 | CIEB | equity | source_conflict_review | 22.64 | 22.9 | 22.35 | 22.5 | EGP | 2026-11-02T19:08:12+02:00 | [Investing.com](https://www.investing.com/equities/credit-agricol-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 12 | 2026-11-02 | ELEC | equity | source_conflict_review | 1.5 | 1.55 | 1.48 | 1.49 | EGP | 2026-11-02T19:08:12+02:00 | [Investing.com](https://www.investing.com/equities/electro-cable-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 13 | 2026-11-02 | FAIT | equity | source_conflict_review | 43.2 | 43.67 | 43.2 | 43.6 | EGP | 2026-11-02T19:08:12+02:00 | [Investing.com](https://pl.investing.com/equities/faisal-islmc-e-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 14 | 2026-11-02 | EGX30 | index | source_conflict_review | 48744.01 | 49295.7 | 47791.47 | 48403.14 | points | 2026-11-02T19:08:12+02:00 | [Investing.com](https://ng.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 15 | 2026-11-02 | EGX100EWI | index | ohlc_inconsistency_review | 22410.52 | 22442.14 | 22426.26 | 22434.64 | points | 2026-11-02T19:08:12+02:00 | [Investing.com](https://ng.investing.com/indices/egx-100-ewi-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 16 | 2026-11-03 | COMI | equity | ohlc_inconsistency_review | 121.40 | 123.00 | 121.51 | 123.00 | EGP | 2026-11-03T19:11:18+02:00 | [Investing.com](https://ng.investing.com/equities/com-intl-bk-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 17 | 2026-11-03 | EGX30 | index | source_conflict_review | 48403.14 | 49255.66 | 48029.83 | 49255.66 | points | 2026-11-03T19:11:18+02:00 | [Investing.com](https://ng.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 18 | 2026-11-03 | EGBASC | index | ohlc_inconsistency_review | 4623.49 | 4585.49 | 4505.27 | 4521.70 | points | 2026-11-03T19:11:18+02:00 | [Investing.com](https://ng.investing.com/indices/egx-basic-r-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 19 | 2026-11-04 | EGAL | equity | ohlc_inconsistency_review | 303.00 | 328.99 | 307.00 | 318.19 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/egypt-aluminum-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 20 | 2026-11-04 | ALUM | equity | ohlc_inconsistency_review | 18.49 | 19.50 | 18.61 | 19.10 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/arab-aluminum-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 21 | 2026-11-04 | FWRY | equity | ohlc_inconsistency_review | 16.12 | 16.95 | 16.25 | 16.94 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/fawry-banking-and-payment-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 22 | 2026-11-04 | ETEL | equity | source_conflict_review | 122.88 | 126.50 | 122.80 | 126.10 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/telecom-egypt-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 23 | 2026-11-04 | ABUK | equity | ohlc_inconsistency_review | 77.71 | 79.24 | 77.95 | 79.00 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/abou-kir-fertilizers-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 24 | 2026-11-04 | EFIC | equity | ohlc_inconsistency_review | 136.40 | 142.00 | 137.00 | 141.98 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/egyptian-fin-i-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 25 | 2026-11-04 | EGCH | equity | ohlc_inconsistency_review | 9.94 | 10.35 | 10.00 | 10.34 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/egypt-chem-ind-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 26 | 2026-11-04 | MBSC | equity | ohlc_inconsistency_review | 311.02 | 318.80 | 313.10 | 316.00 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/misr-beni-suef-cement-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 27 | 2026-11-04 | PHAR | equity | ohlc_inconsistency_review | 98.40 | 101.80 | 99.35 | 100.40 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/egypt-intl-phr-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 28 | 2026-11-04 | MFPC | equity | ohlc_inconsistency_review | 40.07 | 41.18 | 40.10 | 40.68 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/misr-fertilizers-production-co-sae-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 29 | 2026-11-04 | SWDY | equity | ohlc_inconsistency_review | 108.60 | 113.00 | 110.51 | 112.00 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/elsewedy-cable-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 30 | 2026-11-04 | CANA | equity | ohlc_inconsistency_review | 45.32 | 46.00 | 45.60 | 45.96 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/suez-canal-ban-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 31 | 2026-11-04 | ELEC | equity | ohlc_inconsistency_review | 1.540 | 1.610 | 1.550 | 1.600 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/electro-cable-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 32 | 2026-11-04 | ORHD | equity | ohlc_inconsistency_review | 10.15 | 10.50 | 10.25 | 10.35 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/orascom-hotels-and-development-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 33 | 2026-11-04 | JUFO | equity | ohlc_inconsistency_review | 23.00 | 24.22 | 23.10 | 23.89 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/juhayna-food-industries-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 34 | 2026-11-04 | ORAS | equity | ohlc_inconsistency_review | 790.05 | 812.00 | 796.10 | 802.00 | EGP | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 35 | 2026-11-04 | EGX30 | index | ohlc_inconsistency_review | 49255.66 | 50650.18 | 49481.62 | 50650.18 | points | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 36 | 2026-11-04 | EGX70EWI | index | ohlc_inconsistency_review | 16648.16 | 16999.56 | 16700.27 | 16964.17 | points | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/indices/egx-70-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 37 | 2026-11-04 | EGX100EWI | index | ohlc_inconsistency_review | 22344.10 | 23011.03 | 22433.40 | 23011.03 | points | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/indices/egx-100-ewi-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 38 | 2026-11-04 | EGX33 | index | ohlc_inconsistency_review | 5907.64 | 6028.54 | 5928.22 | 6025.85 | points | 2026-11-04T19:04:48+02:00 | [Investing.com](https://ph.investing.com/indices/egx-33-shariah-compliant-index-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 39 | 2026-11-05 | ABUK | equity | ohlc_inconsistency_review | 80 | 82.39 | 80.34 | 80.79 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/abou-kir-fertilizers-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 40 | 2026-11-05 | ETEL | equity | ohlc_inconsistency_review | 128 | 132.79 | 129.01 | 131.44 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/telecom-egypt-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 41 | 2026-11-05 | COMI | equity | ohlc_inconsistency_review | 126.51 | 128.95 | 126.52 | 128.79 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/com-intl-bk-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 42 | 2026-11-05 | RAYA | equity | ohlc_inconsistency_review | 5.45 | 5.65 | 5.47 | 5.58 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/raya-tech---co-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 43 | 2026-11-05 | ACAP | equity | ohlc_inconsistency_review | 6.99 | 7.3 | 7.05 | 7.15 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/a-capital-holding-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 44 | 2026-11-05 | RACC | equity | ohlc_inconsistency_review | 7.8 | 7.98 | 7.81 | 7.9 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/raya-contact-center-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 45 | 2026-11-05 | FWRY | equity | source_conflict_review | 17.1 | 17.38 | 17.01 | 17.32 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/fawry-banking-and-payment-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 46 | 2026-11-05 | EGX30 | index | source_conflict_review | 50841.01 | 51546.16 | 50837.31 | 51152.73 | points | 2026-11-05T19:52:01+02:00 | [Investing.com](https://tr.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 47 | 2026-11-05 | EGX30CAP | index | source_conflict_review | 62912.21 | 63726.68 | 62906.63 | 63261.74 | points | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/indices/egx-20-capped-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 48 | 2026-11-05 | EGX70EWI | index | ohlc_inconsistency_review | 17151.55 | 17572.72 | 17188.25 | 17567.23 | points | 2026-11-05T19:52:01+02:00 | [Investing.com](https://ph.investing.com/indices/egx-70-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 49 | 2026-11-05 | EGX100EWI | index | ohlc_inconsistency_review | 23011.03 | 23504.43 | 23067.81 | 23494.05 | points | 2026-11-05T19:52:01+02:00 | [Investing.com](https://ca.investing.com/indices/egx-100-ewi-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 50 | 2026-11-05 | TMGH | equity | ohlc_inconsistency_review | 81.08 | 84.50 | 81.60 | 84.30 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://www.investing.com/equities/t-m-g-holding-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 51 | 2026-11-05 | ADIB | equity | source_conflict_review | 49.50 | 50.49 | 49.01 | 49.01 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://za.investing.com/equities/abu-dhabi-islamic-bank-egypt-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 52 | 2026-11-05 | ORAS | equity | ohlc_inconsistency_review | 797.02 | 815.00 | 805.00 | 810.02 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 53 | 2026-11-05 | HELI | equity | ohlc_inconsistency_review | 6.61 | 6.97 | 6.62 | 6.94 | EGP | 2026-11-05T19:52:01+02:00 | [Investing.com](https://ca.investing.com/equities/heliopolis-housing-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 54 | 2026-11-08 | ORAS | equity | source_conflict_review | 810.02 | 818.40 | 800.01 | 801.00 | EGP | 2026-11-08T19:45:44+02:00 | [Investing.com](https://ph.investing.com/equities/orascom-construction-ltd-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 55 | 2026-11-08 | HELI | equity | source_conflict_review | 6.94 | 7.09 | 6.74 | 6.90 | EGP | 2026-11-08T19:45:44+02:00 | [Investing.com](https://ca.investing.com/equities/heliopolis-housing-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 56 | 2026-11-08 | EGX30 | index | ohlc_inconsistency_review | 51152.73 | 51030.09 | 50426.32 | 50812.07 | points | 2026-11-08T19:45:44+02:00 | [Investing.com](https://nl.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 57 | 2026-11-08 | EGX30CAP | index | ohlc_inconsistency_review | 63219.99 | 63034.92 | 62216.59 | 62781.23 | points | 2026-11-08T19:45:44+02:00 | [Investing.com](https://www.investing.com/indices/egx-20-capped-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 58 | 2026-11-09 | PHDC | equity | source_conflict_review | 12.010 | 12.100 | 11.940 | 11.940 | EGP | 2026-11-09T19:41:47+02:00 | [Investing.com](https://www.investing.com/equities/palm-hill-dev-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 59 | 2026-11-09 | EGX30 | index | source_conflict_review | 50841.73 | 51432.95 | 50831.06 | 51414.93 | points | 2026-11-09T19:41:47+02:00 | [Investing.com](https://www.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 60 | 2026-11-09 | EGX30CAP | index | ohlc_inconsistency_review | 62781.23 | 63610.19 | 62836.13 | 63610.19 | points | 2026-11-09T19:41:47+02:00 | [Investing.com](https://www.investing.com/indices/egx-20-capped-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 61 | 2026-11-09 | SHARIAH | index | ohlc_inconsistency_review | 6117.71 | 6234.38 | 6131.15 | 6222.51 | points | 2026-11-09T19:41:47+02:00 | [Investing.com](https://www.investing.com/indices/egx-33-shariah-compliant-index-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 62 | 2026-11-09 | EGX70EWI | index | ohlc_inconsistency_review | 17687.34 | 17959.58 | 17719.01 | 17959.58 | points | 2026-11-09T19:41:47+02:00 | [Investing.com](https://www.investing.com/indices/egx-70-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 63 | 2026-11-09 | EGX100EWI | index | ohlc_inconsistency_review | 23526.51 | 23869.07 | 23568.12 | 23869.07 | points | 2026-11-09T19:41:47+02:00 | [Investing.com](https://www.investing.com/indices/egx-100-ewi-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 64 | 2026-11-10 | HDBK | equity | ohlc_inconsistency_review | 99.46 | 104.64 | 100.00 | 102.81 | EGP | 2026-11-10T19:16:35+02:00 | [Investing.com](https://www.investing.com/equities/housing---dev-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 65 | 2026-11-10 | ORAS | equity | ohlc_inconsistency_review | 795.94 | 832.00 | 797.10 | 815.15 | EGP | 2026-11-10T19:16:35+02:00 | [Investing.com](https://www.investing.com/equities/orascom-construction-ltd-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 66 | 2026-11-10 | PHDC | equity | ohlc_inconsistency_review | 11.880 | 12.100 | 11.930 | 12.070 | EGP | 2026-11-10T19:16:35+02:00 | [Investing.com](https://ph.investing.com/equities/palm-hill-dev-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 67 | 2026-11-10 | RAYA | equity | ohlc_inconsistency_review | 5.88 | 6.28 | 5.94 | 6.25 | EGP | 2026-11-10T19:16:35+02:00 | [Investing.com](https://www.investing.com/equities/raya-tech---co-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 68 | 2026-11-10 | TMGH | equity | ohlc_inconsistency_review | 83.50 | 86.48 | 83.75 | 86.00 | EGP | 2026-11-10T19:16:35+02:00 | [Investing.com](https://www.investing.com/equities/t-m-g-holding-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 69 | 2026-11-10 | EGX30 | index | ohlc_inconsistency_review | 51414.93 | 52508.16 | 51542.88 | 52483.46 | points | 2026-11-10T19:16:35+02:00 | [Investing.com](https://www.investing.com/indices/egx30-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 70 | 2026-11-10 | EGX70EWI | index | ohlc_inconsistency_review | 17959.58 | 18495.97 | 17999.03 | 18495.97 | points | 2026-11-10T19:16:35+02:00 | [Investing.com](https://www.investing.com/indices/egx-70-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |
| 71 | 2026-11-10 | EGX100EWI | index | ohlc_inconsistency_review | 23869.07 | 24495.46 | 23939.07 | 24495.46 | points | 2026-11-10T19:16:35+02:00 | [Investing.com](https://www.investing.com/indices/egx-100-ewi-historical-data) | UNRESOLVED |  |  | unknown |  |  |  |

## Queue totals

- OHLC inconsistency review: 51
- Source conflict review: 18
- Source revision conflict: 1
- Total: 70
- Dispositions assigned: 0
- Independently evidenced items: 0 (not yet established)

**No canonical CSV values were changed to create this ledger.**