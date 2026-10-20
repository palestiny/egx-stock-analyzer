# M61 public multi-symbol momentum/volume diagnostic

## Goal

Check whether the COMI-only momentum/volume observation generalizes to a small
cross-section of EGX shares. This is a temporary research diagnostic and is not
part of the production recommendation path.

## Data source and handling

The script uses five historical CSV URLs listed in
`AhmedYasserShalaby/egx-research-toolkit/data/stock_rotation/universe.csv`
(COMI, EGAL, ABUK, TMGH, EAST). The CSV URLs point to Mubasher's public static
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

- Pooled signals overlap and are not statistically independent.
- Gross returns exclude transaction fees, slippage, liquidity/market impact,
  portfolio sizing, and risk adjustment.
- A shared date window is not proof that each source series is corporate-action
  adjusted consistently.
- Five symbols do not satisfy M61's ten-symbol 2021–2025 acceptance gate.
- This is not a live feed, news model, or investment recommendation. Promising
  results must be replicated on additional symbols and disjoint holdout periods
  before considering strategy changes.
