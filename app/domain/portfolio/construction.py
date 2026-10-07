from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


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
class PortfolioEvaluation:
    positions: tuple[PortfolioPosition, ...]
    snapshot: PortfolioSnapshot


class PortfolioEvaluator:
    @staticmethod
    def evaluate(
        positions: list[PortfolioPosition],
        *,
        configuration: PortfolioConfiguration,
        returns: dict[str, Decimal],
    ) -> PortfolioEvaluation:
        if not positions:
            raise ValueError("positions cannot be empty")

        symbols = [position.symbol for position in positions]
        if len(symbols) != len(set(symbols)):
            raise ValueError("positions must contain unique symbols")

        for position in positions:
            if position.weight > configuration.max_single_name_weight:
                raise ValueError("position exceeds max_single_name_weight")
            if position.symbol not in returns:
                raise ValueError(f"missing return for {position.symbol}")

        invested_weight = sum(
            (position.weight for position in positions), Decimal("0")
        )
        if invested_weight > Decimal("1"):
            raise ValueError("portfolio weights cannot exceed 1")

        portfolio_return = sum(
            (position.weight * returns[position.symbol] for position in positions),
            Decimal("0"),
        )
        concentration_ratio = max(
            (position.weight for position in positions),
            default=Decimal("0"),
        )

        snapshot = PortfolioSnapshot(
            portfolio_return=portfolio_return,
            invested_weight=invested_weight,
            cash_weight=Decimal("1") - invested_weight,
            concentration_ratio=concentration_ratio,
        )
        return PortfolioEvaluation(
            positions=tuple(positions),
            snapshot=snapshot,
        )
