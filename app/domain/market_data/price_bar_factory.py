from app.domain.market_data.data_quality import DataQualityAssessment, DataQualityStatus
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.volume import Volume


class PriceBarFactory:
    @staticmethod
    def create(
        observation: RawPriceBarObservation,
        assessment: DataQualityAssessment,
    ) -> PriceBar:
        if assessment.status is not DataQualityStatus.VALID:
            raise ValueError("Data quality must be VALID before creating a PriceBar")

        if any(
            value is None
            for value in (
                observation.stock_id,
                observation.timeframe,
                observation.timestamp,
                observation.open,
                observation.high,
                observation.low,
                observation.close,
                observation.volume,
            )
        ):
            raise ValueError("VALID observation must contain all PriceBar values")

        return PriceBar.create(
            stock_id=observation.stock_id,
            timeframe=observation.timeframe,
            timestamp=observation.timestamp,
            open=Price(observation.open),
            high=Price(observation.high),
            low=Price(observation.low),
            close=Price(observation.close),
            volume=Volume(observation.volume),
        )
