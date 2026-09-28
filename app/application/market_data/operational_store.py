from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from app.application.market_data.provider import MarketDataProvider
from app.domain.market_data.raw_observation import RawPriceBarObservation


class MarketDataConflictError(ValueError):
    def __init__(self, key, existing, incoming) -> None:
        super().__init__(f"Market data conflict for identity {key}")
        self.key = key
        self.existing = existing
        self.incoming = incoming


@dataclass(frozen=True)
class MarketCoverage:
    start: date
    end: date
    observation_dates: frozenset[date]


class OperationalMarketDataService:
    def __init__(self, provider: MarketDataProvider, store, session_calendar) -> None:
        self._provider = provider
        self._store = store
        self._session_calendar = session_calendar

    def ensure_daily_coverage(
        self,
        stock_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        if from_date > to_date:
            raise ValueError("from_date cannot be after to_date")

        existing = self._store.get_daily_observations(
            stock_id, from_date, to_date
        )
        existing_dates = {item.timestamp.date() for item in existing}
        expected = self._session_calendar.expected_sessions(from_date, to_date)
        missing = [day for day in expected if day not in existing_dates]

        if missing:
            requested_from = min(missing)
            requested_to = max(missing)
            incoming = self._provider.get_daily_observations(
                _StockIdentity(stock_id),
                requested_from,
                requested_to,
            )
            self._store.save(incoming)

        return self._store.get_daily_observations(stock_id, from_date, to_date)


@dataclass(frozen=True)
class _StockIdentity:
    id: UUID
