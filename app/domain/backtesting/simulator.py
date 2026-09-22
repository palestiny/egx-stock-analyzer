from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Callable

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar


class ExitReason(Enum):
    STRATEGY_INVALIDATION = "strategy_invalidation"
    TIME_LIMIT = "time_limit"


@dataclass(frozen=True)
class BacktestConfiguration:
    max_holding_bars: int
    transaction_cost_rate: Decimal
    slippage_rate: Decimal


@dataclass(frozen=True)
class BacktestStrategy:
    strategy_id: str
    version: str
    signal: Callable[[list[PriceBar]], bool]
    position_valid: Callable[[list[PriceBar]], bool]


@dataclass(frozen=True)
class BacktestTrade:
    strategy_id: str
    strategy_version: str
    signal_timestamp: object
    execution_timestamp: object
    entry_price: Price
    gross_entry_price: Price
    exit_timestamp: object
    exit_price: Price
    gross_exit_price: Price
    exit_reason: ExitReason
    gross_return: Decimal
    total_cost: Decimal
    net_return: Decimal


@dataclass(frozen=True)
class BacktestResult:
    strategy_id: str
    strategy_version: str
    configuration: BacktestConfiguration
    trades: tuple[BacktestTrade, ...]
    open_trade_count: int

    @property
    def completed_trade_count(self) -> int:
        return len(self.trades)


class BacktestSimulator:
    @staticmethod
    def run(
        price_bars: list[PriceBar],
        strategy: BacktestStrategy,
        configuration: BacktestConfiguration,
    ) -> BacktestResult:
        BacktestSimulator._validate_configuration(configuration)
        BacktestSimulator._validate_bars(price_bars)

        trades: list[BacktestTrade] = []
        open_trade_count = 0
        position_index: int | None = None
        signal_index: int | None = None

        index = 0
        while index < len(price_bars):
            history = price_bars[: index + 1]

            if position_index is None:
                if not strategy.signal(history):
                    index += 1
                    continue

                execution_index = index + 1
                if execution_index >= len(price_bars):
                    open_trade_count += 1
                    break

                position_index = execution_index
                signal_index = index
                index = execution_index
                continue

            holding_bars = index - position_index + 1
            invalidated = not strategy.position_valid(history)
            timed_out = holding_bars >= configuration.max_holding_bars

            if not invalidated and not timed_out:
                index += 1
                continue

            exit_index = index + 1
            if exit_index >= len(price_bars):
                open_trade_count += 1
                break

            entry_bar = price_bars[position_index]
            exit_bar = price_bars[exit_index]
            signal_bar = price_bars[signal_index]  # type: ignore[index]

            reason = (
                ExitReason.STRATEGY_INVALIDATION
                if invalidated
                else ExitReason.TIME_LIMIT
            )

            trade = BacktestSimulator._build_trade(
                signal_bar=signal_bar,
                entry_bar=entry_bar,
                exit_bar=exit_bar,
                strategy=strategy,
                configuration=configuration,
                exit_reason=reason,
            )
            trades.append(trade)

            position_index = None
            signal_index = None
            index = exit_index

        return BacktestResult(
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.version,
            configuration=configuration,
            trades=tuple(trades),
            open_trade_count=open_trade_count,
        )

    @staticmethod
    def _build_trade(
        signal_bar: PriceBar,
        entry_bar: PriceBar,
        exit_bar: PriceBar,
        strategy: BacktestStrategy,
        configuration: BacktestConfiguration,
        exit_reason: ExitReason,
    ) -> BacktestTrade:
        gross_entry = entry_bar.open
        gross_exit = exit_bar.open

        entry_slippage = gross_entry.value * configuration.slippage_rate
        exit_slippage = gross_exit.value * configuration.slippage_rate

        effective_entry = gross_entry.value + entry_slippage
        effective_exit = gross_exit.value - exit_slippage

        entry_cost = effective_entry * configuration.transaction_cost_rate
        exit_cost = effective_exit * configuration.transaction_cost_rate
        total_cost = entry_cost + exit_cost

        gross_return = (
            (gross_exit.value - gross_entry.value) / gross_entry.value
        )
        net_proceeds = effective_exit - exit_cost
        net_return = (net_proceeds - effective_entry - entry_cost) / effective_entry

        return BacktestTrade(
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.version,
            signal_timestamp=signal_bar.timestamp,
            execution_timestamp=entry_bar.timestamp,
            entry_price=Price(effective_entry),
            gross_entry_price=gross_entry,
            exit_timestamp=exit_bar.timestamp,
            exit_price=Price(effective_exit),
            gross_exit_price=gross_exit,
            exit_reason=exit_reason,
            gross_return=gross_return,
            total_cost=total_cost,
            net_return=net_return,
        )

    @staticmethod
    def _validate_configuration(configuration: BacktestConfiguration) -> None:
        if configuration.max_holding_bars < 1:
            raise ValueError("max_holding_bars must be at least 1")
        if configuration.transaction_cost_rate < 0:
            raise ValueError("transaction_cost_rate cannot be negative")
        if configuration.slippage_rate < 0:
            raise ValueError("slippage_rate cannot be negative")

    @staticmethod
    def _validate_bars(price_bars: list[PriceBar]) -> None:
        for previous, current in zip(price_bars, price_bars[1:]):
            if current.timestamp <= previous.timestamp:
                raise ValueError("price_bars must be strictly time ordered")
