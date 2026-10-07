from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from statistics import mean, pstdev


@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    weight: Decimal

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol is required")
        if self.weight < Decimal("0") or self.weight > Decimal("1"):
            raise ValueError("weight must be between 0 and 1")


@dataclass(frozen=True)
class PortfolioConfiguration:
    max_single_name_weight: Decimal = Decimal("0.20")

    def __post_init__(self) -> None:
        if self.max_single_name_weight <= Decimal("0") or self.max_single_name_weight > Decimal("1"):
            raise ValueError("max_single_name_weight must be between 0 and 1")


@dataclass(frozen=True)
class PortfolioSnapshot:
    portfolio_return: Decimal
    invested_weight: Decimal
    cash_weight: Decimal
    concentration_ratio: Decimal


@dataclass(frozen=True)
class PortfolioMetrics:
    portfolio_returns: tuple[Decimal, ...]
    max_drawdown: Decimal
    volatility: Decimal
    average_pairwise_correlation: Decimal


@dataclass(frozen=True)
class PortfolioEvaluation:
    positions: tuple[PortfolioPosition, ...]
    snapshot: PortfolioSnapshot
    metrics: PortfolioMetrics | None = None


class PortfolioEvaluator:
    @staticmethod
    def _validate_positions(
        positions: list[PortfolioPosition],
        configuration: PortfolioConfiguration,
    ) -> Decimal:
        if not positions:
            raise ValueError("positions cannot be empty")

        symbols = [position.symbol for position in positions]
        if len(symbols) != len(set(symbols)):
            raise ValueError("positions must contain unique symbols")

        for position in positions:
            if position.weight > configuration.max_single_name_weight:
                raise ValueError("position exceeds max_single_name_weight")

        invested_weight = sum(
            (position.weight for position in positions), Decimal("0")
        )
        if invested_weight > Decimal("1"):
            raise ValueError("portfolio weights cannot exceed 1")
        return invested_weight

    @staticmethod
    def evaluate(
        positions: list[PortfolioPosition],
        *,
        configuration: PortfolioConfiguration,
        returns: dict[str, Decimal],
    ) -> PortfolioEvaluation:
        invested_weight = PortfolioEvaluator._validate_positions(
            positions, configuration
        )

        for position in positions:
            if position.symbol not in returns:
                raise ValueError(f"missing return for {position.symbol}")

        portfolio_return = sum(
            (position.weight * returns[position.symbol] for position in positions),
            Decimal("0"),
        )
        concentration_ratio = max(
            (position.weight for position in positions), default=Decimal("0")
        )

        return PortfolioEvaluation(
            positions=tuple(positions),
            snapshot=PortfolioSnapshot(
                portfolio_return=portfolio_return,
                invested_weight=invested_weight,
                cash_weight=Decimal("1") - invested_weight,
                concentration_ratio=concentration_ratio,
            ),
        )

    @staticmethod
    def evaluate_series(
        positions: list[PortfolioPosition],
        *,
        configuration: PortfolioConfiguration,
        returns_by_symbol: dict[str, list[Decimal]],
    ) -> PortfolioEvaluation:
        invested_weight = PortfolioEvaluator._validate_positions(
            positions, configuration
        )
        expected_symbols = {position.symbol for position in positions}
        if set(returns_by_symbol) != expected_symbols:
            raise ValueError("returns_by_symbol must match portfolio symbols")

        lengths = {len(values) for values in returns_by_symbol.values()}
        if len(lengths) != 1 or not lengths or next(iter(lengths)) == 0:
            raise ValueError("all return series must have the same length and be non-empty")

        portfolio_returns = tuple(
            sum(
                (position.weight * returns_by_symbol[position.symbol][index]
                 for position in positions),
                Decimal("0"),
            )
            for index in range(next(iter(lengths)))
        )

        equity = Decimal("1")
        peak = equity
        max_drawdown = Decimal("0")
        for return_ in portfolio_returns:
            equity *= Decimal("1") + return_
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / peak)

        volatility = Decimal("0")
        if len(portfolio_returns) > 1:
            volatility = Decimal(str(pstdev(portfolio_returns)))

        correlations: list[Decimal] = []
        symbols = [position.symbol for position in positions]
        for left_index, left_symbol in enumerate(symbols):
            for right_symbol in symbols[left_index + 1:]:
                left = returns_by_symbol[left_symbol]
                right = returns_by_symbol[right_symbol]
                left_mean = mean(left)
                right_mean = mean(right)
                left_deviation = [value - left_mean for value in left]
                right_deviation = [value - right_mean for value in right]
                denominator = (
                    sqrt(
                        sum(float(value * value) for value in left_deviation)
                        * sum(float(value * value) for value in right_deviation)
                    )
                )
                correlation = (
                    Decimal(str(
                        sum(
                            float(lv * rv)
                            for lv, rv in zip(left_deviation, right_deviation)
                        ) / denominator
                    ))
                    if denominator > 0
                    else Decimal("0")
                )
                correlations.append(correlation)

        average_correlation = (
            sum(correlations, Decimal("0")) / Decimal(len(correlations))
            if correlations
            else Decimal("0")
        )

        portfolio_return = portfolio_returns[-1]
        return PortfolioEvaluation(
            positions=tuple(positions),
            snapshot=PortfolioSnapshot(
                portfolio_return=portfolio_return,
                invested_weight=invested_weight,
                cash_weight=Decimal("1") - invested_weight,
                concentration_ratio=max(
                    (position.weight for position in positions),
                    default=Decimal("0"),
                ),
            ),
            metrics=PortfolioMetrics(
                portfolio_returns=portfolio_returns,
                max_drawdown=max_drawdown,
                volatility=volatility,
                average_pairwise_correlation=average_correlation,
            ),
        )
