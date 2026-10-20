"""Run a diagnostic Strategy v0 backtest on a public COMI price-history sample.

This is an exploratory test fixture, not an accepted M61 research dataset.
Market prices come from a public GitHub repository; underlying market-data
redistribution rights have not been independently verified. Financial values
are sourced from CIB's official annual/earnings disclosures for FY2020/FY2021.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from statistics import pstdev
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.backtesting.historical_dataset_runner import (
    HistoricalDatasetBacktestRunner,
)
from app.domain.backtesting.simulator import BacktestConfiguration
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.historical_financial_snapshot import (
    HistoricalFinancialSnapshot,
)
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock

EGX_TIMEZONE = ZoneInfo("Africa/Cairo")
STOCK_ID = UUID("dbd6e8d0-14b6-5f7f-9c15-84ecddf4b47e")
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "m61_public_comi_history_2019_2023.csv"
)
DATA_START = date(2020, 1, 1)
EVALUATION_START = date(2022, 3, 1)
DATA_END = date(2022, 12, 31)


class _MarketProvider:
    def __init__(self, observations: list[RawPriceBarObservation]) -> None:
        self._observations = observations

    def get_daily_observations(
        self, stock: Stock, from_date: date, to_date: date
    ) -> list[RawPriceBarObservation]:
        return [
            observation
            for observation in self._observations
            if observation.stock_id == stock.id
            and from_date
            <= observation.timestamp.astimezone(EGX_TIMEZONE).date()
            <= to_date
        ]


class _FinancialSource:
    """Two real, dated annual snapshots; no synthetic financial figures."""

    def get_snapshots(self, stock: Stock) -> list[HistoricalFinancialSnapshot]:
        if stock.id != STOCK_ID:
            return []
        return [
            HistoricalFinancialSnapshot(
                period=FinancialPeriod(
                    period_end=date(2020, 12, 31),
                    revenue=Decimal("25881"),
                    net_income=Decimal("10238.157"),
                ),
                # CIB announced FY2020 results on 2021-03-01; date-only
                # availability is conservatively moved to the following day.
                available_at=date(2021, 3, 2),
            ),
            HistoricalFinancialSnapshot(
                period=FinancialPeriod(
                    period_end=date(2021, 12, 31),
                    revenue=Decimal("26696"),
                    net_income=Decimal("13272.209"),
                ),
                # CIB announced FY2021 results on 2022-02-22; use next day.
                available_at=date(2022, 2, 23),
            ),
        ]


def _volume(value: str) -> int:
    match = re.fullmatch(r"\s*([\d,.]+)\s*([MK])?\s*", value, re.IGNORECASE)
    if match is None:
        raise ValueError(f"Unsupported source volume value: {value!r}")
    number = Decimal(match.group(1).replace(",", ""))
    suffix = (match.group(2) or "").upper()
    multiplier = Decimal("1000000") if suffix == "M" else (
        Decimal("1000") if suffix == "K" else Decimal("1")
    )
    parsed = number * multiplier
    if parsed != parsed.to_integral_value():
        raise ValueError(f"Volume does not resolve to whole shares: {value!r}")
    return int(parsed)


def _load_market_rows() -> tuple[list[RawPriceBarObservation], dict[str, Any]]:
    valid: list[tuple[date, RawPriceBarObservation]] = []
    rejected: list[dict[str, str]] = []
    seen_dates: set[date] = set()

    with FIXTURE.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Date", "Price", "Open", "High", "Low", "Vol."}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Public COMI fixture has an unexpected CSV schema")

        for line_number, row in enumerate(reader, start=2):
            session = date.fromisoformat(row["Date"])
            if not DATA_START <= session <= DATA_END:
                continue
            if session in seen_dates:
                rejected.append({"line": str(line_number), "reason": "duplicate session"})
                continue
            seen_dates.add(session)

            try:
                close = Decimal(row["Price"].replace(",", ""))
                opening = Decimal(row["Open"].replace(",", ""))
                high = Decimal(row["High"].replace(",", ""))
                low = Decimal(row["Low"].replace(",", ""))
                volume = _volume(row["Vol."])
                if min(opening, high, low, close) <= 0:
                    raise ValueError("non-positive OHLC")
                if high < max(opening, low, close) or low > min(opening, high, close):
                    raise ValueError("OHLC relationship violation")
            except (ValueError, ArithmeticError) as exc:
                rejected.append({"line": str(line_number), "reason": str(exc)})
                continue

            timestamp = datetime.combine(
                session, time(hour=12), tzinfo=EGX_TIMEZONE
            )
            valid.append(
                (
                    session,
                    RawPriceBarObservation(
                        stock_id=STOCK_ID,
                        timeframe=Timeframe.DAILY,
                        timestamp=timestamp,
                        open=opening,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume,
                    ),
                )
            )

    valid.sort(key=lambda item: item[0])
    if not valid:
        raise ValueError("No valid COMI bars found in the selected diagnostic window")

    observations = [item[1] for item in valid]
    report = {
        "source": (
            "M-Abdelmegeed/Project-EGX, "
            "EGX Stock data/COMI Historical Data.csv"
        ),
        "source_git_blob_sha": "41192e5402c5c497d03603540875d9126837ffc7",
        "fixture_rows_in_window": len(observations) + len(rejected),
        "valid_market_rows": len(observations),
        "rejected_rows": rejected,
        "data_start": valid[0][0].isoformat(),
        "data_end": valid[-1][0].isoformat(),
        "evaluation_start": EVALUATION_START.isoformat(),
        "evaluation_end": DATA_END.isoformat(),
        "source_rights": "not independently verified; diagnostic use only",
        "market_data_note": (
            "Publicly committed historical sample; corporate actions and "
            "adjustment semantics have not been independently reconciled."
        ),
    }
    return observations, report


def _risk_profile(observations: list[RawPriceBarObservation]) -> dict[str, Any]:
    """Calculate transparent price/volume risk diagnostics from observed bars."""
    ordered = sorted(observations, key=lambda item: item.timestamp)
    if len(ordered) < 2:
        return {
            "status": "insufficient_history",
            "bars": len(ordered),
            "daily_returns": 0,
        }

    returns: list[tuple[date, float]] = []
    peak = ordered[0].close
    max_drawdown = Decimal("0")
    max_drawdown_date: date | None = None
    volume_spikes = 0
    gaps: list[tuple[date, Decimal]] = []

    for index, bar in enumerate(ordered):
        session = bar.timestamp.astimezone(EGX_TIMEZONE).date()
        close = bar.close
        if close > peak:
            peak = close
        drawdown = (close - peak) / peak if peak > 0 else Decimal("0")
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            max_drawdown_date = session

        if index > 0:
            previous = ordered[index - 1]
            previous_close = previous.close
            if previous_close > 0:
                returns.append((session, float((close - previous_close) / previous_close)))
                gaps.append((session, (bar.open - previous_close) / previous_close))

        if index >= 20:
            prior_volumes = [Decimal(item.volume or 0) for item in ordered[index - 20:index]]
            average_volume = sum(prior_volumes, Decimal("0")) / Decimal(20)
            if average_volume > 0 and Decimal(bar.volume or 0) >= average_volume * Decimal("1.5"):
                volume_spikes += 1

    return_values = [value for _, value in returns]
    annualized_volatility = pstdev(return_values) * (252**0.5) if len(return_values) > 1 else 0.0
    worst_day = min(returns, key=lambda item: item[1]) if returns else None
    worst_gap = min(gaps, key=lambda item: item[1]) if gaps else None
    last_close = ordered[-1].close
    current_drawdown = (last_close - peak) / peak if peak > 0 else Decimal("0")

    return {
        "status": "completed",
        "bars": len(ordered),
        "daily_returns": len(returns),
        "annualized_realized_volatility": round(annualized_volatility, 6),
        "maximum_close_to_close_drawdown": str(max_drawdown),
        "maximum_drawdown_date": max_drawdown_date.isoformat() if max_drawdown_date else None,
        "current_drawdown_from_observed_peak": str(current_drawdown),
        "worst_daily_return": {
            "date": worst_day[0].isoformat(),
            "return": str(worst_day[1]),
        } if worst_day else None,
        "worst_overnight_gap": {
            "date": worst_gap[0].isoformat(),
            "return": str(worst_gap[1]),
        } if worst_gap else None,
        "sessions_with_volume_at_least_1_5x_prior_20_session_average": volume_spikes,
        "method_notes": [
            "Risk profile uses only the selected historical price bars; it is not a market-wide crash score.",
            "Annualized volatility is population standard deviation of close-to-close returns multiplied by sqrt(252).",
            "No corporate-action adjustment or official-source reconciliation has been performed.",
        ],
    }


def run_sample_backtest() -> dict[str, Any]:
    observations, report = _load_market_rows()
    stock = Stock(STOCK_ID, "COMI", "Commercial International Bank Egypt")
    runner = HistoricalDatasetBacktestRunner(
        stock,
        _MarketProvider(observations),
        _FinancialSource(),
    )
    configuration = BacktestConfiguration(
        max_holding_bars=10,
        transaction_cost_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.001"),
    )
    result = runner.run(
        DATA_START,
        DATA_END,
        configuration,
        evaluation_start_date=EVALUATION_START,
    )
    metrics = result.metrics
    evaluation_rows = sum(
        observation.timestamp.astimezone(EGX_TIMEZONE).date() >= EVALUATION_START
        for observation in observations
    )
    report.update(
        {
            "strategy_id": result.strategy_id,
            "strategy_version": result.strategy_version,
            "warmup_bars": result.configuration.warmup_bars,
            "evaluation_bars": evaluation_rows,
            "completed_trades": metrics.completed_trade_count,
            "open_trades": metrics.open_trade_count,
            "winning_trades": metrics.winning_trade_count,
            "losing_trades": metrics.losing_trade_count,
            "win_rate": str(metrics.win_rate),
            "average_gross_trade_return": str(metrics.average_gross_return),
            "average_net_trade_return": str(metrics.average_net_return),
            "cumulative_net_trade_return": str(metrics.cumulative_net_return),
            "cost_assumption": {
                "transaction_cost_rate": "0.001",
                "slippage_rate": "0.001",
                "max_holding_bars": 10,
            },
            "financial_evidence": {
                "FY2020_revenue_EGP_millions": "25881",
                "FY2020_net_income_EGP_millions": "10238.157",
                "FY2020_available_at": "2021-03-02",
                "FY2021_revenue_EGP_millions": "26696",
                "FY2021_net_income_EGP_millions": "13272.209",
                "FY2021_available_at": "2022-02-23",
                "note": (
                    "Only FY2020/FY2021 snapshots are supplied; stale fundamentals "
                    "are not refreshed during the 2022 evaluation window."
                ),
            },
            "interpretation": (
                "Exploratory diagnostic only. Not accepted M61 data, not a "
                "validated strategy-performance estimate, and not for investment decisions."
            ),
        }
    )
    return report


def main() -> None:
    print(json.dumps(run_sample_backtest(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
