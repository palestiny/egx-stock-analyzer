from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
from typing import Callable

from app.application.research.evaluation import ExitEvaluation, evaluate_exit_bar, next_open_entry
from app.domain.research.dataset import (
    ResearchBar,
    ResearchRunConfig,
    validate_research_bars,
)


class BacktestStatus(StrEnum):
    COMPLETED = "COMPLETED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class EntryIntent:
    """An entry decision emitted after a bar closes; it may only fill on a later bar."""
    side: str
    target: Decimal
    invalidation: Decimal
    signal_id: str

    def __post_init__(self) -> None:
        if self.side not in ("LONG", "SHORT"):
            raise ValueError("side must be LONG or SHORT")
        if min(self.target, self.invalidation) <= 0:
            raise ValueError("target and invalidation must be positive")
        if not self.signal_id.strip():
            raise ValueError("signal_id is required")
        if self.side == "LONG" and self.invalidation >= self.target:
            raise ValueError("long invalidation must be below target")
        if self.side == "SHORT" and self.target >= self.invalidation:
            raise ValueError("short target must be below invalidation")


@dataclass(frozen=True)
class TradeRecord:
    signal_id: str
    side: str
    decision_timestamp: datetime
    entry_timestamp: datetime
    entry_reference_price: Decimal
    entry_price: Decimal
    entry_commission: Decimal
    exit_timestamp: datetime
    exit_price: Decimal
    exit_reason: str
    exit_commission: Decimal
    gross_return: Decimal
    net_return: Decimal
    notional: Decimal
    quantity: Decimal
    net_pnl: Decimal


@dataclass(frozen=True)
class UnfilledDecision:
    signal_id: str
    decision_timestamp: datetime
    reason: str


@dataclass(frozen=True)
class EquityPoint:
    timestamp: datetime
    equity: Decimal
    realized_equity: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class BacktestMetrics:
    completed_trades: int
    unfilled_decisions: int
    wins: int
    win_rate: Decimal
    cumulative_net_return: Decimal
    max_drawdown: Decimal
    exposure_bars: int
    total_bars: int
    time_in_market_ratio: Decimal


@dataclass(frozen=True)
class BacktestResult:
    status: BacktestStatus
    run_id: str
    reason: str | None
    dataset_version: str
    provider: str
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    trades: tuple[TradeRecord, ...]
    unfilled_decisions: tuple[UnfilledDecision, ...]
    equity_curve: tuple[EquityPoint, ...]
    metrics: BacktestMetrics


Strategy = Callable[[tuple[ResearchBar, ...]], EntryIntent | None]


def _run_id(bars: tuple[ResearchBar, ...], config: ResearchRunConfig, initial_capital: Decimal, parameters_json: str) -> str:
    try:
        parameters = json.loads(parameters_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("parameters_json must be valid JSON") from exc
    canonical_parameters = json.dumps(parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    manifest = {
        "dataset_version": config.dataset_version,
        "provider": config.provider,
        "strategy_id": config.strategy_id,
        "strategy_version": config.strategy_version,
        "evaluator_version": config.evaluator_version,
        "execution_model": config.execution_model.value,
        "ambiguity_policy": config.ambiguity_policy.value,
        "adjustment": config.adjustment.value,
        "commission_rate": str(config.costs.commission_rate),
        "slippage_rate": str(config.costs.slippage_rate),
        "initial_capital": str(initial_capital),
        "parameters": canonical_parameters,
        "bars": [
            [bar.symbol, bar.timeframe, bar.source_timestamp.isoformat(), bar.ingestion_timestamp.isoformat(),
             str(bar.open), str(bar.high), str(bar.low), str(bar.close), str(bar.volume), bar.provider,
             bar.dataset_version, bar.quality.value, bar.adjustment.value]
            for bar in bars
        ],
    }
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _metrics(trades: tuple[TradeRecord, ...], unfilled: tuple[UnfilledDecision, ...], curve: tuple[EquityPoint, ...], exposure_bars: int, initial_capital: Decimal) -> BacktestMetrics:
    wins = sum(1 for trade in trades if trade.net_pnl > 0)
    count = len(trades)
    peak = initial_capital
    max_drawdown = Decimal("0")
    for point in curve:
        peak = max(peak, point.equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - point.equity) / peak)
    final_equity = curve[-1].equity if curve else initial_capital
    return BacktestMetrics(
        completed_trades=count,
        unfilled_decisions=len(unfilled),
        wins=wins,
        win_rate=Decimal(wins) / Decimal(count) if count else Decimal("0"),
        cumulative_net_return=(final_equity - initial_capital) / initial_capital,
        max_drawdown=max_drawdown,
        exposure_bars=exposure_bars,
        total_bars=len(curve),
        time_in_market_ratio=Decimal(exposure_bars) / Decimal(len(curve)) if curve else Decimal("0"),
    )


def run_backtest(
    bars: tuple[ResearchBar, ...],
    *,
    config: ResearchRunConfig,
    strategy: Strategy,
    initial_capital: Decimal = Decimal("100000"),
    parameters_json: str = "{}",
) -> BacktestResult:
    """Run a deterministic, single-position replay. Strategy receives only the closed prefix."""
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    run_id = _run_id(bars, config, initial_capital, parameters_json)

    def invalid(reason: str) -> BacktestResult:
        metrics = BacktestMetrics(0, 0, 0, Decimal("0"), Decimal("0"), Decimal("0"), 0, 0, Decimal("0"))
        return BacktestResult(
            BacktestStatus.INVALID, run_id, reason, config.dataset_version, config.provider,
            bars[0].source_timestamp if bars else None, bars[-1].source_timestamp if bars else None,
            (), (), (), metrics,
        )

    if not bars:
        return invalid("dataset is empty")
    try:
        validate_research_bars(bars)
        for bar in bars:
            if bar.provider != config.provider or bar.dataset_version != config.dataset_version:
                raise ValueError("run config provider/dataset version does not match input bars")
            if bar.adjustment is not config.adjustment:
                raise ValueError("run config adjustment does not match input bars")
    except ValueError as exc:
        return invalid(str(exc))

    trades: list[TradeRecord] = []
    unfilled: list[UnfilledDecision] = []
    curve: list[EquityPoint] = []
    realized_equity = initial_capital
    position: dict | None = None
    pending: tuple[int, EntryIntent] | None = None
    exposure_bars = 0

    for index, bar in enumerate(bars):
        # A decision from the prior closed bar may fill at this bar's open only.
        if pending is not None and pending[0] + 1 == index:
            decision_index, intent = pending
            fill = next_open_entry(
                bars[decision_index:index + 1], 0, side=intent.side, costs=config.costs,
                execution_model=config.execution_model,
            )
            if fill is None:
                unfilled.append(UnfilledDecision(intent.signal_id, bars[decision_index].source_timestamp, "next bar unavailable"))
            else:
                if intent.side == "LONG" and not intent.invalidation < fill.fill_price < intent.target:
                    unfilled.append(UnfilledDecision(intent.signal_id, fill.decision_timestamp, "target/invalidation do not bracket long entry fill"))
                elif intent.side == "SHORT" and not intent.target < fill.fill_price < intent.invalidation:
                    unfilled.append(UnfilledDecision(intent.signal_id, fill.decision_timestamp, "target/invalidation do not bracket short entry fill"))
                else:
                    notional = realized_equity
                    quantity = notional / fill.fill_price
                    position = {
                        "intent": intent, "fill": fill, "quantity": quantity, "notional": notional,
                        "target": intent.target, "invalidation": intent.invalidation,
                    }
            pending = None

        if position is not None:
            exposure_bars += 1
            intent = position["intent"]
            exit_eval = evaluate_exit_bar(
                bar, side=intent.side, target=position["target"], invalidation=position["invalidation"],
                entry_price=position["fill"].fill_price, costs=config.costs,
                ambiguity_policy=config.ambiguity_policy,
            )
            if exit_eval is not None:
                net_pnl = position["notional"] * exit_eval.net_return
                realized_equity += net_pnl
                trades.append(TradeRecord(
                    intent.signal_id, intent.side, position["fill"].decision_timestamp,
                    position["fill"].fill_timestamp, position["fill"].reference_price, position["fill"].fill_price,
                    position["fill"].commission, exit_eval.exit_timestamp, exit_eval.exit_price, exit_eval.reason,
                    exit_eval.commission, exit_eval.gross_return, exit_eval.net_return, position["notional"], position["quantity"], net_pnl,
                ))
                position = None

        # Only the prefix ending at this closed bar is exposed to the strategy.
        if position is None and pending is None:
            intent = strategy(bars[: index + 1])
            if intent is not None:
                if index + 1 >= len(bars):
                    unfilled.append(UnfilledDecision(intent.signal_id, bar.source_timestamp, "signal on final bar has no next bar"))
                else:
                    # Keep the decision index; the next loop iteration fills at the next bar open.
                    pending = (index, intent)

        if position is None:
            equity = realized_equity
            unrealized = Decimal("0")
        else:
            intent = position["intent"]
            mark = bar.close * (Decimal("1") - config.costs.slippage_rate if intent.side == "LONG" else Decimal("1") + config.costs.slippage_rate)
            gross = (mark - position["fill"].fill_price) / position["fill"].fill_price if intent.side == "LONG" else (position["fill"].fill_price - mark) / position["fill"].fill_price
            unrealized = position["notional"] * (gross - config.costs.commission_rate - (mark * config.costs.commission_rate / position["fill"].fill_price))
            equity = realized_equity + unrealized
        curve.append(EquityPoint(bar.source_timestamp, equity, realized_equity, unrealized))

    trades_tuple, unfilled_tuple, curve_tuple = tuple(trades), tuple(unfilled), tuple(curve)
    return BacktestResult(
        BacktestStatus.COMPLETED, run_id, None, config.dataset_version, config.provider,
        bars[0].source_timestamp, bars[-1].source_timestamp, trades_tuple, unfilled_tuple, curve_tuple,
        _metrics(trades_tuple, unfilled_tuple, curve_tuple, exposure_bars, initial_capital),
    )
