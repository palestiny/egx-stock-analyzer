# M61 public multi-symbol momentum/volume diagnostic

## Goal

Check whether the COMI-only momentum/volume observation generalizes to a small
cross-section of EGX shares. This is a temporary research diagnostic and is not
part of the production recommendation path.

## Data source and handling

The script uses five historical CSV URLs listed in
`AhmedYasserShalaby/egx-research-toolkit/data/stock_rotation/universe.csv`
(COMI, EGAL, ABUK, TMGH, EAST, FWRY, ETEL, EFIH, HRHO, ADIB). The CSV URLs point to Mubasher's public static
historical-chart files. The script requests the URLs directly, parses the
six-column no-header OHLCV format, validates dates/prices/volume, drops
malformed and duplicate rows, and reports per-symbol retrieval failures.

The source repository is a public reference for the URLs, not an assertion that
it owns the underlying market data. Redistribution rights, corporate-action
adjustments, and completeness have not been independently verified. Treat the
run as diagnostic only and do not redistribute the raw source data.

## Method

- Use the intersection of the successfully retrieved symbols' available date
  ranges, so per-symbol results refer to the same calendar window.
- Positive momentum means today's close exceeds the close five sessions earlier.
- Volume confirmation means positive momentum and today's volume is at least
  1.5 times the mean volume of the five preceding sessions; today's volume is
  excluded from the average.
- A signal is generated after the daily bar completes. Assumed entry is the next
  session's open; exits are measured at the close after 1, 3, 5, or 10 sessions.
- Report all eligible sessions as a baseline, positive momentum alone, and the
  combined momentum-plus-volume condition. Results include per-symbol and pooled
  observations, mean/median returns, win rate, sample count, and worst return.

## Run

The dedicated GitHub Actions workflow fetches the current public CSVs and
uploads a JSON report as an artifact:

- Workflow: `.github/workflows/m61-mubasher-multi-symbol.yml`
- Command: `python -m tools.m61_mubasher_multi_symbol_diagnostic`

The workflow intentionally remains separate from the main test suite because
external data availability must not make deterministic CI flaky. If fewer than
three sources are usable, the tool emits a JSON report with a non-completed
status and per-symbol errors instead of throwing away the report. A successful
GitHub Actions job therefore means the diagnostic ran and produced a report;
inspect the report's `status` before interpreting any returns.

## Limits and acceptance gates

- The pre-breakout proxy is not the production scanner’s nearest-swing-resistance algorithm; it is a historical approximation, not exact validation of PR #325.
- Pooled signals overlap and are not statistically independent.
- Gross returns exclude transaction fees, slippage, liquidity/market impact,
  portfolio sizing, and risk adjustment.
- A shared date window is not proof that each source series is corporate-action
  adjusted consistently.
- Ten symbols alone do not satisfy M61's 2021–2025 acceptance gate: the required
  point-in-time financial snapshots, reproducible data provenance, and acceptance
  checks are still separate requirements.
- This is not a live feed, news model, or investment recommendation. Promising
  results must be replicated on additional symbols and disjoint holdout periods
  before considering strategy changes.


## Observed pre-breakout proxy results

The GitHub Actions diagnostic run [39422108865](https://github.com/palestiny/egx-stock-analyzer/actions/runs/39422108865) retrieved all ten configured symbols with no source-fetch failures and used the common window 2021-10-25 through 2026-10-19. The report includes pooled forward returns across symbol-session observations.

| Signal group | Horizon | Samples | Mean gross return | Win rate |
|---|---:|---:|---:|---:|
| All eligible sessions (baseline) | 1 session | 9,607 | -0.15% | 41.5% |
| All eligible sessions (baseline) | 3 sessions | 9,587 | 0.26% | 47.6% |
| All eligible sessions (baseline) | 5 sessions | 9,567 | 0.67% | 50.5% |
| All eligible sessions (baseline) | 10 sessions | 9,517 | 1.75% | 53.6% |
| Positive momentum + volume >= 1.5x | 1 session | 1,245 | -0.16% | 39.4% |
| Positive momentum + volume >= 1.5x | 3 sessions | 1,244 | 0.36% | 44.8% |
| Positive momentum + volume >= 1.5x | 5 sessions | 1,244 | 0.65% | 49.2% |
| Positive momentum + volume >= 1.5x | 10 sessions | 1,235 | 1.85% | 53.1% |
| Pre-breakout proxy | 1 session | 541 | -0.01% | 40.3% |
| Pre-breakout proxy | 3 sessions | 541 | 0.52% | 44.7% |
| Pre-breakout proxy | 5 sessions | 541 | 0.62% | 48.4% |
| Pre-breakout proxy | 10 sessions | 536 | 1.63% | 53.2% |

All values are arithmetic forward price returns from next-session open to the horizon close, before fees and slippage. Signals overlap and the pooled sample is not a set of independent trades.

### Interpretation

This run does **not** establish a predictive edge for the pre-breakout proxy. Its mean returns are slightly above the baseline at 1 and 3 sessions, but below the baseline at 5 and 10 sessions; win rates are below baseline at every horizon. The 10-session mean is 1.63% versus 1.75% for all eligible sessions and 1.85% for momentum plus volume without the resistance filter.

There is also a material data-quality warning: some pooled groups contain extreme one-session losses (the all-session baseline's worst return is about -53.4%). These may reflect unadjusted corporate actions or source discontinuities, but that cause has not been established. Until each symbol's large gaps and corporate actions are reconciled, even these gross-return comparisons are exploratory and should not be used to tune or endorse a strategy.

This is useful negative evidence: do not promote the 1.5x/5% conditions as an edge. The next research step is per-symbol and per-period breakdown, anomaly reconciliation, cost-aware returns, and a disjoint holdout before any threshold change. This proxy is not the exact production nearest-resistance algorithm in PR #325.


### Per-symbol 10-session pre-breakout proxy breakdown

| Symbol | Samples | Mean gross return | Win rate | Worst observed return |
|---|---:|---:|---:|---:|
| ABUK | 53 | 3.28% | 56.6% | -15.09% |
| ADIB | 44 | 0.11% | 54.5% | -49.39% |
| COMI | 63 | 1.20% | 52.4% | -16.89% |
| EAST | 61 | 1.02% | 54.1% | -27.89% |
| EFIH | 45 | 0.82% | 53.3% | -37.58% |
| EGAL | 34 | 4.68% | 67.6% | -16.96% |
| ETEL | 64 | 1.50% | 50.0% | -20.86% |
| FWRY | 62 | 2.02% | 48.4% | -19.04% |
| HRHO | 55 | 0.48% | 54.5% | -21.52% |
| TMGH | 55 | 2.10% | 47.3% | -16.10% |

The per-symbol outcomes are highly heterogeneous. EGAL and ABUK look stronger in this one pooled time window, but sample counts are modest and the most extreme observed losses (especially ADIB and EFIH) are a warning that source discontinuities or corporate actions may distort the forward returns. This is not enough evidence to select those stocks or tune the rule around them; validate the underlying bars first and reserve a later, untouched holdout period.



## Price discontinuity audit

The diagnostic flags an observation for manual review when either its absolute
close-to-close change or its overnight open-versus-previous-close gap is at least
20%. Each finding includes current and previous session dates, previous close,
current OHLCV values, and both calculated changes. The JSON report includes a
per-symbol `price_discontinuities` list and a top-level count.

This is a screening threshold, not a claim that an observation is wrong.
Large moves can be genuine, can reflect corporate actions, or can come from
source gaps or inconsistent adjustment conventions. The audit preserves source
prices and does not auto-correct, drop, or adjust flagged bars. Before using
returns for strategy evaluation, manually reconcile flagged dates against
reliable exchange/company corporate-action information and source history.
The 20% threshold may miss smaller but material discontinuities and will flag
some legitimate high-volatility moves.


### Findings from the 2026-10-20 audit run

The report flagged **16 observations across 7 of 10 symbols** in the 2021-10-25 through 2026-10-19 window. Counts are screening results, not confirmed data errors.

| Symbol | Flagged observations | Dates requiring review |
|---|---:|---|
| ABUK | 2 | 2023-10-17, 2024-02-26 |
| ADIB | 2 | 2024-03-10, 2025-06-10 |
| EFIH | 2 | 2024-03-11, 2025-06-02 |
| EGAL | 3 | 2022-10-20, 2023-10-26, 2024-05-20 |
| FWRY | 2 | 2022-08-04, 2024-03-11 |
| HRHO | 1 | 2022-04-17 |
| TMGH | 4 | 2023-10-29, 2024-02-06, 2024-02-25, 2024-03-05 |
| COMI, EAST, ETEL | 0 | No observations crossed the current 20% screening threshold |

Highest-priority review candidates based on absolute close-to-close movement include ADIB on 2025-06-10 (-47.20%), EFIH on 2025-06-02 (-34.64%), EGAL on 2023-10-26 (+55.11%), TMGH on 2023-10-29 (+40.71%), and ABUK on 2023-10-17 (+26.06%). These are prioritized for investigation by magnitude only; no cause has been verified.

**Required next step:** reconcile these dates against exchange notices, company corporate-action records, and independent price history before excluding observations, adjusting prices, or claiming a strategy edge. Preserve the raw source values and record the evidence and adjustment decision for every reviewed event. A symbol with zero flags is not thereby proven clean; this rule only detects moves meeting the configured threshold.
