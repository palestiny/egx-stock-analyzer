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

- The pre-breakout proxy is not the production scanner’s nearest-swing-resistance algorithm; it is a historical approximation, not exact validation of PR #325.\n- Pooled signals overlap and are not statistically independent.
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
