# M61 — Existing EGX archive technical diagnostic

## Purpose

Run an exploratory, multi-symbol technical-analysis diagnostic on the existing
validated Yahoo-derived archive instead of waiting for the accepted M61
market-plus-fundamentals dataset. The tool is a research bridge, not a new
production recommendation path.

## Input currently available

The private egx-market-data-private repository contains a compressed
structurally validated daily archive at
data/normalized/yahoo/daily_prices_ohlc_validated.csv.gz. Its latest recorded
audit (2026-10-20) reports 181,203 rows across 195 symbols, covering
2021-10-20 through 2026-10-20. The source archive contains 233,361 rows; 52,158
rows were excluded for structural OHLC inconsistencies. The source is Yahoo
Finance's unofficial chart endpoint and the seed symbol list is not an
authoritative EGX instrument register.

## Run locally

After cloning both repositories and making the private data repository available
locally:

~~~powershell
python tools/m61_archive_technical_diagnostic.py --csv "G:\path\to\egx-market-data-private\data\normalized\yahoo\daily_prices_ohlc_validated.csv.gz" --output ".\artifacts\m61-archive-technical-diagnostic.json"
~~~

The tool uses Python's standard library only. It independently checks required
columns, numeric values, duplicate symbol/date keys, and OHLC bounds; malformed
and structurally invalid rows are excluded rather than repaired.

## Method

- Baseline: all eligible sessions with a complete forward-return horizon.
- Positive momentum: signal close above the close five observed bars earlier.
- Momentum + volume: positive momentum and signal-day volume at least 1.5 times
  the average volume of the five preceding bars (signal-day volume excluded).
- Pre-breakout proxy: momentum + volume confirmation + close within 5% below
  the highest high of the preceding 20 observed bars.
- Signal is known after the bar closes; entry is the next observed bar's open.
- Exit is the close of the signal bar plus 1, 3, 5, or 10 observed bars.
- Reports sample count, mean/median forward return, win rate, best/worst return,
  and per-symbol coverage.

## Interpretation boundary

This diagnostic deliberately does not use financial statements, does not run
the production Strategy v0 BUY/SELL classifier, and does not claim that any
signal is profitable. Returns exclude transaction costs, slippage, dividends,
liquidity limits, and portfolio constraints. Overlapping observations are not
independent. Yahoo's price adjustment semantics and historical gaps are not
reconciled by this tool. Results are for functional exploration only; they do
not pass DEC-130 or replace the required point-in-time financial evidence.
