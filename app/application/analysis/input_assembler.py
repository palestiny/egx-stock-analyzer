from dataclasses import dataclass
from datetime import date, timedelta

from app.application.analysis.daily_market_analysis import StockAnalysisInput
from app.application.fundamental_data.provider import FundamentalDataProvider
from app.application.market_data.provider import MarketDataProvider
from app.domain.market_data.data_quality import DataQualityStatus
from app.domain.market_data.data_quality_assessor import DataQualityAssessor
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.price_bar_factory import PriceBarFactory
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


@dataclass(frozen=True)
class AnalysisInputAssemblyPolicy:
    timeframe: Timeframe = Timeframe.DAILY
    momentum_lookback: int = 5
    volume_lookback: int = 5
    market_data_window_days: int = 30

    def __post_init__(self) -> None:
        if self.momentum_lookback <= 0:
            raise ValueError("momentum_lookback must be positive")
        if self.volume_lookback <= 0:
            raise ValueError("volume_lookback must be positive")
        if self.market_data_window_days <= 0:
            raise ValueError("market_data_window_days must be positive")

    @property
    def minimum_price_bars(self) -> int:
        return max(self.momentum_lookback, self.volume_lookback) + 1


class AnalysisInputAssembler:
    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        fundamental_data_provider: FundamentalDataProvider,
        policy: AnalysisInputAssemblyPolicy | None = None,
    ) -> None:
        self._market_data_provider = market_data_provider
        self._fundamental_data_provider = fundamental_data_provider
        self._policy = policy or AnalysisInputAssemblyPolicy()

    def assemble(self, stock: Stock, as_of: date) -> StockAnalysisInput:
        from_date = as_of - timedelta(days=self._policy.market_data_window_days)
        observations = self._market_data_provider.get_daily_observations(
            stock,
            from_date,
            as_of,
        )
        price_bars = self.build_price_bars(
            observations,
            minimum_price_bars=self._policy.minimum_price_bars,
        )
        current_period, previous_period = self._fundamental_data_provider.get_periods(
            stock,
            as_of,
        )

        return StockAnalysisInput(
            symbol=stock.symbol,
            stock_id=stock.id,
            timeframe=self._policy.timeframe,
            price_bars=price_bars,
            current_period=current_period,
            previous_period=previous_period,
            momentum_lookback=self._policy.momentum_lookback,
            volume_lookback=self._policy.volume_lookback,
        )

    @staticmethod
    def build_price_bars(
        observations,
        *,
        minimum_price_bars: int,
    ) -> list[PriceBar]:
        if not observations:
            raise ValueError("Market data provider returned no observations")

        assessments = DataQualityAssessor.assess(observations)
        price_bars: list[PriceBar] = []
        rejected_count = 0

        for observation, assessment in zip(observations, assessments, strict=True):
            if assessment.status is not DataQualityStatus.VALID:
                rejected_count += 1
                continue

            price_bars.append(PriceBarFactory.create(observation, assessment))

        if len(price_bars) < minimum_price_bars:
            raise ValueError(
                "Insufficient valid market data observations for analysis: "
                f"required={minimum_price_bars}, "
                f"valid={len(price_bars)}, "
                f"rejected={rejected_count}"
            )

        return price_bars

    # Backward-compatible alias for existing unit-level callers.
    _build_price_bars = build_price_bars
