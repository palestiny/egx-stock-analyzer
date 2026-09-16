from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from statistics import median
from typing import Callable

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.opportunity.classification import OpportunityClassification


@dataclass(frozen=True)
class BacktestOutcome:
    signal_timestamp: datetime
    execution_timestamp: datetime
    outcome_timestamp: datetime
    entry_price: Price
    outcome_price: Price
    forward_return: Decimal


@dataclass(frozen=True)
class BacktestResult:
    outcomes: tuple[BacktestOutcome, ...]
    buy_signal_count: int
    positive_outcome_count: int
    negative_outcome_count: int
    win_rate: Decimal | None
    average_forward_return: Decimal | None
    median_forward_return: Decimal | None
    minimum_forward_return: Decimal | None
    maximum_forward_return: Decimal | None


class BacktestEvaluator:
    @staticmethod
    def evaluate(
        price_bars: list[PriceBar],
        strategy: Callable[[list[PriceBar]], OpportunityClassification],
        forward_window: int,
    ) -> BacktestResult:
        if forward_window < 1:
            raise ValueError("Forward window must be at least 1")

        outcomes: list[BacktestOutcome] = []
        buy_signal_count = 0

        for signal_index in range(len(price_bars)):
            history = price_bars[: signal_index + 1]
            classification = strategy(history)

            if classification is not OpportunityClassification.BUY:
                continue

            buy_signal_count += 1

            execution_index = signal_index + 1
            outcome_index = signal_index + forward_window

            if outcome_index >= len(price_bars):
                continue

            execution_bar = price_bars[execution_index]
            outcome_bar = price_bars[outcome_index]
            entry_price = execution_bar.close

            if entry_price.value == 0:
                continue

            forward_return = (
                (outcome_bar.close.value - entry_price.value)
                / entry_price.value
            )

            outcomes.append(
                BacktestOutcome(
                    signal_timestamp=price_bars[signal_index].timestamp,
                    execution_timestamp=execution_bar.timestamp,
                    outcome_timestamp=outcome_bar.timestamp,
                    entry_price=entry_price,
                    outcome_price=outcome_bar.close,
                    forward_return=forward_return,
                )
            )

        returns = [outcome.forward_return for outcome in outcomes]
        positive_count = sum(return_ > 0 for return_ in returns)
        negative_count = sum(return_ < 0 for return_ in returns)

        return BacktestResult(
            outcomes=tuple(outcomes),
            buy_signal_count=buy_signal_count,
            positive_outcome_count=positive_count,
            negative_outcome_count=negative_count,
            win_rate=(
                Decimal(positive_count) / Decimal(len(returns))
                if returns
                else None
            ),
            average_forward_return=(
                sum(returns, Decimal("0")) / Decimal(len(returns))
                if returns
                else None
            ),
            median_forward_return=median(returns) if returns else None,
            minimum_forward_return=min(returns) if returns else None,
            maximum_forward_return=max(returns) if returns else None,
        )
