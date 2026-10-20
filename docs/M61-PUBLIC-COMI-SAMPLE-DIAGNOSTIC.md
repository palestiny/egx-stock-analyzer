# M61 public COMI sample — diagnostic only

## Source

A 2019–2023 excerpt from the public repository file:

- Repository: https://github.com/M-Abdelmegeed/Project-EGX
- File: `EGX Stock data/COMI Historical Data.csv`
- Upstream Git blob SHA: `41192e5402c5c497d03603540875d9126837ffc7`
- Upstream CSV schema: `Date, Price, Open, High, Low, Vol., Change %`
- Excerpt: 1,201 daily rows, 2019-01-02 through 2023-12-11.

The upstream repository is public and identifies an MIT license for its project. That does not independently establish the underlying market-data provider's rights, retention permissions, adjustment methodology, or completeness. This fixture is therefore for exploratory software testing only and is not accepted M61 evidence.

## Financial snapshots used for the diagnostic

The smoke backtest uses actual published CIB consolidated annual figures, not generated financial values:

- FY2020: revenue/operating-income measure EGP 25,881 million; net income EGP 10,238.157 million. CIB announced FY2020 results on 2021-03-01; availability is conservatively set to 2021-03-02.
- FY2021: revenue/operating-income measure EGP 26,696 million; net income EGP 13,272.209 million. CIB announced FY2021 results on 2022-02-22; availability is conservatively set to 2022-02-23.

References:
- https://www.cibeg.com/en/investor-relations/ir-library/financial-highlights
- https://www.investegate.co.uk/announcement/rns/commercial-international-bank-egypt-sae-gdr-reg-s---cbkd/cib-fy20-year-end-earnings-release/6487853
- https://www.lse.co.uk/rns/cib-fy2021-earnings-release-xq9bn2gku9e4njk.html

Only FY2020 and FY2021 financial snapshots are provided. They remain unchanged throughout the 2022 evaluation window, so this is not a complete point-in-time fundamental dataset. Current-assets/current-liabilities are not fabricated and are left absent.

## How to run

```powershell
python -m tools.m61_public_comi_sample_backtest
python -m pytest tests/m61/test_public_comi_sample_backtest.py -q
```

The runner uses daily COMI prices from 2020-01-01 through 2022-12-31, a warm-up period before 2022-03-01, and a diagnostic evaluation window from 2022-03-01 through 2022-12-31. It validates OHLC relationships and volume parsing; it does not repair invalid source rows.

## Interpretation boundary

The run is intended to unblock functional verification with real, EGX-specific price observations. It does not satisfy the M61 ten-symbol/2021–2025 data acceptance gate, and the source's corporate-action adjustment semantics have not been independently reconciled. Any strategy metrics are exploratory only and must not be used to infer real-world profitability or make investment decisions.
