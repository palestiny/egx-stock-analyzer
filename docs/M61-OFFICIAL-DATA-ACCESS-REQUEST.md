# M61 — Official Historical Data Access Request

**Purpose:** obtain a lawful, reproducible, no-cost route to validate the first real EGX research dataset.
**Current state:** no accepted market artifact is available in the repository or user-provided files. No source should be treated as accepted until access, coverage, semantics, and intended use are confirmed.

## Why this request is necessary

The free Yahoo chart probe returned invalid provider identity / OHLCV findings and is rejected. EGID's public Swagger documents history endpoints, but an unauthenticated history request returned HTTP 401. Public documentation is not proof of free access or permission to retain data. Paid datasets are currently out of scope.

EGID identifies itself as a market-data provider associated with the Egyptian Exchange. The request below asks for a free developer/sample path or explicit guidance, not an assumption that the service is free.

## Ready-to-send request

**Subject:** Request for EGX historical daily OHLCV sample / developer access for research validation

Hello EGID Market Data Team,

I am developing an independent Egyptian Exchange stock-analysis research application. I am currently validating the data pipeline and reproducible historical evaluation methodology, and I do not have a budget for a paid historical-data subscription at this stage.

Could you please advise whether EGID or the Egyptian Exchange offers any of the following for a small, non-brokerage research project?

1. A free developer/sandbox account or a limited historical-data trial.
2. A small sample of daily OHLCV data for **COMI** covering **2019-01-01 through 2025-12-31**, or the longest available range.
3. If a sample is available, the source symbol, trading date/time convention, price/volume units, missing-session and suspension semantics, and whether prices are raw/as-published or corporate-action adjusted.
4. The applicable terms for local retention, repeatable research/backtesting, derived analytical results, and any public display or redistribution. We will not redistribute raw data unless explicitly licensed.
5. Whether historical financial statements/disclosures can be obtained with publication/availability dates, or where the official archive for those documents is located.
6. If no free access is available, the minimum product/permission required for this limited research use and whether there is an official public alternative.

A small COMI sample is sufficient for an initial technical validation; we would only expand to the fixed ten-symbol cohort after confirming coverage and permitted use.

Thank you for your guidance.

Regards,
EGX Stock Analyzer project

## Required response evidence

Do not treat a verbal/API response as dataset acceptance by itself. Record:

- provider/contact and response date;
- access method and entitlement/account type;
- explicit allowed use, retention, and redistribution boundaries;
- artifact delivery method and checksum;
- symbol mapping, coverage, OHLCV schema, timezone, and adjustment convention;
- availability-date provenance for financial statements.

## Minimal acquisition order

1. Obtain explicit no-cost access / sample permission from EGID or EGX.
2. Acquire **COMI only** first; preserve the original artifact and source evidence.
3. Run `python -m tools.m61_vendor_csv_evidence_inspector` on the original market CSV.
4. Package market and point-in-time financial evidence using `python -m tools.m61_build_candidate_dataset`.
5. Run `python -m tools.m61_comi_evidence_intake <dataset-directory>`.
6. Proceed to the ten-symbol cohort only after COMI has an accepted report and the same source/rights path covers the remaining symbols.

## Hard stop conditions

- Do not scrape a site whose terms prohibit automated collection or algorithmic use.
- Do not use synthetic fixtures, Yahoo candidates, or unlicensed TradingView data for strategy evaluation.
- Do not fabricate missing prices, infer unknown corporate actions, or substitute period-end dates for financial publication dates.
- If access is denied or no free licensed path exists, keep real-market evaluation blocked and report the exact external dependency. That is a source-access blocker, not a reason to weaken the acceptance gate.
