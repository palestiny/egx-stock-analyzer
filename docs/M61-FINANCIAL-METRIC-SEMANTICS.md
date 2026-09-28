# M61 Financial Metric Semantics

## Purpose

M61 must not treat the existing FinancialPeriod.revenue field as a universal semantic across all EGX issuers. Banking disclosures expose distinct concepts such as Net Operating Income, Net Interest Income, Net Profit, and other revenue presentations. CIB official FY2024 materials report these concepts separately.

## Domain boundary

FinancialMetric preserves:

- explicit metric code;
- source metric label;
- consolidated/standalone statement scope;
- currency;
- unit;
- numeric value.

The source identity is therefore not lost when data crosses into the domain.

## Strategy v0 comparability policy

The current policy intentionally accepts only FinancialMetricCode.REVENUE as the generic Strategy v0 comparable growth metric.

Banking metrics such as NET_OPERATING_INCOME, NET_INTEREST_INCOME, and NET_PROFIT are not substituted into REVENUE.

An unsupported metric produces an explicit UNSUPPORTED result instead of silently changing the accounting meaning.

This is an interim safety boundary, not evidence that all issuers' revenue definitions are economically comparable.

## CIB / COMI

CIB official FY2024 Financial Highlights report Net Operating Income of EGP 98,956 million and Net Profits of EGP 55,196 million. Its FY2024 Board report also describes standalone revenues separately from consolidated banking income concepts.

Therefore M61 must preserve source metric identity and statement scope. No COMI financial snapshot is promoted into the accepted historical dataset until a documented cohort-level comparability rule is established.

## Gate status

- Financial metric identity: PASS
- Silent banking-to-revenue substitution: PASS — prohibited by code/tests
- Cohort-wide comparable metric policy: NOT PROVEN
- COMI financial acceptance: BLOCKED
- Strategy v0 validation: BLOCKED
