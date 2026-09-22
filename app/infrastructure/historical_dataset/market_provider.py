from datetime import date, datetime, timezone

from app.application.market_data.provider import MarketDataProvider
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader


class HistoricalDatasetMarketDataProvider(MarketDataProvider):
    """Adapts the versioned historical dataset to the production market-data contract."""

    def __init__(self, loader: HistoricalDatasetLoader) -> None:
        self._loader = loader

    def get_daily_observations(
        self,
        stock: Stock,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        if from_date > to_date:
            raise ValueError("from_date cannot be after to_date")

        observations = self._loader.load_market_observations()
        result: list[RawPriceBarObservation] = []
        for observation in observations:
            if observation.stock_id != stock.id or observation.timeframe != Timeframe.DAILY.value:
                continue
            observation_date = observation.timestamp.date()
            if not from_date <= observation_date <= to_date:
                continue
            if observation.volume != observation.volume.to_integral_value():
                raise ValueError("Historical market volume must be an integer")
            result.append(
                RawPriceBarObservation(
                    stock_id=observation.stock_id,
                    timeframe=Timeframe.DAILY,
                    timestamp=self._as_utc(observation.timestamp),
                    open=observation.open,
                    high=observation.high,
                    low=observation.low,
                    close=observation.close,
                    volume=int(observation.volume),
                )
            )
        return result

    @staticmethod
    def _as_utc(timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Historical market timestamp must be timezone-aware")
        return timestamp.astimezone(timezone.utc)
