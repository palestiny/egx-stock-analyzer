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
class BacktestMetrics:
    completed_trade_count: int
    open_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    win_rate: Decimal
    average_gross_return: Decimal
    average_net_return: Decimal
    cumulative_net_return: Decimal


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

    @property
    def metrics(self) -> BacktestMetrics:
        completed = len(self.trades)
        winning = sum(trade.net_return > 0 for trade in self.trades)
        losing = sum(trade.net_return < 0 for trade in self.trades)
        win_rate = Decimal(winning) / Decimal(completed) if completed else Decimal("0")
        average_gross = (
            sum((trade.gross_return for trade in self.trades), Decimal("0")) / Decimal(completed)
            if completed
            else Decimal("0")
        )
        average_net = (
            sum((trade.net_return for trade in self.trades), Decimal("0")) / Decimal(completed)
            if completed
            else Decimal("0")
        )
        cumulative_net = Decimal("1")
        for trade in self.trades:
            cumulative_net *= Decimal("1") + trade.net_return
        cumulative_net -= Decimal("1")

        return BacktestMetrics(
            completed_trade_count=completed,
            open_trade_count=self.open_trade_count,
            winning_trade_count=winning,
            losing_trade_count=losing,
            win_rate=win_rate,
            average_gross_return=average_gross,
            average_net_return=average_net,
            cumulative_net_return=cumulative_net,
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
