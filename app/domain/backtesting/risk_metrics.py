from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from statistics import mean, pstdev


@dataclass(frozen=True)
class BacktestRiskMetrics:
    trade_count: int
    total_return: Decimal
    max_drawdown: Decimal
    profit_factor: Decimal
    win_rate: Decimal
    sharpe_ratio: Decimal | None
    var_95: Decimal | None
    cvar_95: Decimal | None

    @staticmethod
    def calculate(
        returns: list[Decimal],
        *,
        periods_per_year: int,
    ) -> BacktestRiskMetrics:
        if not returns:
            raise ValueError("returns cannot be empty")
        if periods_per_year < 1:
            raise ValueError("periods_per_year must be at least 1")
        if any(return_ <= Decimal("-1") for return_ in returns):
            raise ValueError("returns must be greater than -100%")

        equity = Decimal("1")
        peak = equity
        max_drawdown = Decimal("0")
        for return_ in returns:
            equity *= Decimal("1") + return_
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)

        gains = sum((r for r in returns if r > 0), Decimal("0"))
        losses = sum((-r for r in returns if r < 0), Decimal("0"))
        profit_factor = gains / losses if losses else Decimal("Infinity")
        win_rate = Decimal(sum(r > 0 for r in returns)) / Decimal(len(returns))

        average = mean(returns)
        deviation = pstdev(returns) if len(returns) > 1 else 0.0
        sharpe_ratio = (
            Decimal(str(average / deviation * sqrt(periods_per_year)))
            if deviation > 0
            else None
        )

        ordered = sorted(returns)
        tail_count = max(1, int(len(ordered) * 0.05))
        worst_returns = ordered[:tail_count]
        var_95 = -worst_returns[-1]
        cvar_95 = -(
            sum(worst_returns, Decimal("0")) / Decimal(len(worst_returns))
        )

        return BacktestRiskMetrics(
            trade_count=len(returns),
            total_return=equity - Decimal("1"),
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
        )
