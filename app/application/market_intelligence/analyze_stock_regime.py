from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.application.clock import egx_today
from app.application.market_data.provider import MarketDataProvider
from app.application.stocks.catalog import StockCatalog
from app.domain.analysis.stock_regime import StockRegimeAnalyzer, StockRiskProfile
from app.domain.market_data.data_quality import DataQualityAssessment, DataQualityStatus
from app.domain.market_data.data_quality_assessor import DataQualityAssessor
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.price_bar_factory import PriceBarFactory
from app.domain.market_data.raw_observation import RawPriceBarObservation


@dataclass(frozen=True)
class StockRegimeAnalysis:
    symbol: str
    source: str
    requested_from: date
    requested_to: date
    latest_observation_date: date | None
    valid_observation_count: int
    excluded_observation_count: int
    profile: StockRiskProfile


@dataclass(frozen=True)
class AnalyzeStockRegime:
    stock_catalog: StockCatalog
    market_data_provider: MarketDataProvider

    LOOKBACK_CALENDAR_DAYS = 550

    def execute(self, symbol: str, as_of: date | None = None) -> StockRegimeAnalysis:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol is required")
        stock = self.stock_catalog.get(normalized)
        if stock is None:
            raise ValueError(f"Unknown stock symbol: {normalized}")

        end_date = as_of or egx_today()
        start_date = end_date - timedelta(days=self.LOOKBACK_CALENDAR_DAYS)
        observations = self.market_data_provider.get_daily_observations(
            stock, start_date, end_date
        )
        assessments = DataQualityAssessor.assess(observations)
        valid: list[tuple[RawPriceBarObservation, DataQualityAssessment]] = [
            (observation, assessment)
            for observation, assessment in zip(observations, assessments)
            if assessment.status is DataQualityStatus.VALID
            and observation.close is not None
            and observation.close > 0
        ]
        valid.sort(
            key=lambda pair: pair[0].timestamp
            or datetime.min.replace(tzinfo=timezone.utc)
        )
        bars: list[PriceBar] = [
            PriceBarFactory.create(observation, assessment)
            for observation, assessment in valid
        ]
        profile = StockRegimeAnalyzer.analyze(bars)
        latest_date = bars[-1].timestamp.date() if bars else None
        # Providers may expose a stable source_name. Fall back to the concrete
        # adapter class rather than falsely attributing every provider to Yahoo.
        source = getattr(self.market_data_provider, "source_name", None)
        if not isinstance(source, str) or not source.strip():
            source = type(self.market_data_provider).__name__
        return StockRegimeAnalysis(
            symbol=normalized,
            source=source.strip(),
            requested_from=start_date,
            requested_to=end_date,
            latest_observation_date=latest_date,
            valid_observation_count=len(bars),
            excluded_observation_count=len(observations) - len(bars),
            profile=profile,
        )
