"""Evaluate whether existing COMI momentum/volume signals precede forward price moves.

Diagnostic only: uses the public COMI fixture and existing production analysis
components. Entry is the next session's open to avoid assuming execution at the
same close that generated the signal.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from statistics import median
from typing import Any

from app.application.analysis.input_assembler import (
    AnalysisInputAssembler,
    AnalysisInputAssemblyPolicy,
)
from app.application.analysis.stock_analysis import StockAnalysisPipeline
from app.application.clock import EGX_TIMEZONE
from app.application.fundamental_data.historical_provider import (
    PointInTimeFundamentalDataProvider,
)
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.technical_analysis.momentum import MomentumStatus
from app.domain.technical_analysis.volume import VolumeStatus
from tools.m61_public_comi_sample_backtest import (
    DATA_END,
    EVALUATION_START,
    STOCK_ID,
    _FinancialSource,
    _load_market_rows,
)
from app.domain.stocks.stock import Stock

HORIZONS = (1, 3, 5, 10)
HIGH_VOLUME_RATIO = Decimal("1.5")


def _summarize(returns: list[Decimal]) -> dict[str, Any]:
    if not returns:
        return {
            "samples": 0,
            "mean_return": None,
            "median_return": None,
            "win_rate": None,
            "best_return": None,
            "worst_return": None,
        }
    return {
        "samples": len(returns),
        "mean_return": str(sum(returns, Decimal("0")) / len(returns)),
        "median_return": str(Decimal(str(median(returns)))),
        "win_rate": str(Decimal(sum(value > 0 for value in returns)) / len(returns)),
        "best_return": str(max(returns)),
        "worst_return": str(min(returns)),
    }


def run_signal_diagnostic() -> dict[str, Any]:
    observations, source_report = _load_market_rows()
    policy = AnalysisInputAssemblyPolicy()
    bars = AnalysisInputAssembler.build_price_bars(
        observations,
        minimum_price_bars=policy.minimum_price_bars,
    )
    stock = Stock(STOCK_ID, "COMI", "Commercial International Bank Egypt")
    fundamentals = PointInTimeFundamentalDataProvider(_FinancialSource())
    signal_groups: dict[str, list[int]] = {
        "all_eligible_sessions": [],
        "positive_momentum": [],
        "positive_momentum_and_volume_at_least_1_5x": [],
        "strategy_buy": [],
    }

    for index, bar in enumerate(bars):
        session = bar.timestamp.astimezone(EGX_TIMEZONE).date()
        if session < EVALUATION_START or session > DATA_END:
            continue
        if index < policy.minimum_price_bars - 1:
            continue

        history = bars[: index + 1]
        current_period, previous_period = fundamentals.get_periods(stock, session)
        result = StockAnalysisPipeline.analyze(
            stock.id,
            policy.timeframe,
            history,
            current_period,
            previous_period,
            policy.momentum_lookback,
            policy.volume_lookback,
        )
        signal_groups["all_eligible_sessions"].append(index)

        momentum_positive = (
            result.technical_analysis.momentum.status is MomentumStatus.POSITIVE
        )
        volume_ratio = result.technical_analysis.volume.volume_ratio
        high_volume = (
            volume_ratio is not None and volume_ratio >= HIGH_VOLUME_RATIO
        )
        if momentum_positive:
            signal_groups["positive_momentum"].append(index)
        if momentum_positive and high_volume:
            signal_groups["positive_momentum_and_volume_at_least_1_5x"].append(index)
        if result.opportunity.classification is OpportunityClassification.BUY:
            signal_groups["strategy_buy"].append(index)

    forward_results: dict[str, dict[str, Any]] = {}
    for group_name, indexes in signal_groups.items():
        horizon_results: dict[str, Any] = {}
        for horizon in HORIZONS:
            returns: list[Decimal] = []
            for index in indexes:
                entry_index = index + 1
                exit_index = index + horizon
                if exit_index >= len(bars):
                    continue
                entry_open = bars[entry_index].open.value
                exit_close = bars[exit_index].close.value
                if entry_open <= 0:
                    continue
                returns.append((exit_close - entry_open) / entry_open)
            horizon_results[str(horizon)] = _summarize(returns)
        forward_results[group_name] = horizon_results

    return {
        "diagnostic": "COMI momentum/volume forward-return evaluation",
        "source": source_report["source"],
        "data_window": {
            "start": source_report["data_start"],
            "end": source_report["data_end"],
            "evaluation_start": EVALUATION_START.isoformat(),
            "evaluation_end": DATA_END.isoformat(),
        },
        "signal_definitions": {
            "positive_momentum": "existing production MomentumAnalyzer reports positive 5-session rate of change",
            "positive_momentum_and_volume_at_least_1_5x": "positive momentum and current volume / preceding 5-session average volume >= 1.5",
            "strategy_buy": "existing production StockAnalysisPipeline classifies the opportunity as BUY",
            "execution_assumption": "entry at next session open; exit at close after the specified horizon",
        },
        "forward_returns_by_group_and_horizon": forward_results,
        "limitations": [
            "single symbol and limited evaluation window",
            "public source market-data rights and corporate-action adjustments are not independently verified",
            "signals overlap and are not independent observations",
            "no benchmark risk adjustment or full portfolio simulation",
            "diagnostic metrics are not an investment recommendation or profitability claim",
        ],
    }


def main() -> None:
    print(json.dumps(run_signal_diagnostic(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
