from dataclasses import dataclass
from datetime import date, timedelta

from app.application.market_data.provider import MarketDataProvider
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.stocks.stock import Stock


class MarketDataConflictError(ValueError):
    def __init__(self, key, existing, incoming) -> None:
        super().__init__(f"Market data conflict for identity {key}")
        self.key = key
        self.existing = existing
        self.incoming = incoming


class MarketDataCoverageError(ValueError):
    def __init__(self, missing_dates: list[date]) -> None:
        super().__init__(
            "Provider did not return all expected market sessions: "
            + ", ".join(day.isoformat() for day in missing_dates)
        )
        self.missing_dates = tuple(missing_dates)


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
        stock: Stock,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        if from_date > to_date:
            raise ValueError("from_date cannot be after to_date")

        existing = self._store.get_daily_observations(
            stock.id, from_date, to_date
        )
        existing_dates = {item.timestamp.date() for item in existing}
        expected = self._session_calendar.expected_sessions(from_date, to_date)
        missing = [day for day in expected if day not in existing_dates]

        for range_start, range_end in self._contiguous_ranges(missing):
            incoming = self._provider.get_daily_observations(
                stock,
                range_start,
                range_end,
            )
            incoming_dates = {
                item.timestamp.date()
                for item in incoming
                if item.stock_id == stock.id
            }
            requested_sessions = [
                day for day in expected if range_start <= day <= range_end
            ]
            unresolved = [
                day for day in requested_sessions if day not in incoming_dates
            ]
            if unresolved:
                raise MarketDataCoverageError(unresolved)
            self._store.save(incoming)

        return self._store.get_daily_observations(
            stock.id, from_date, to_date
        )

    @staticmethod
    def _contiguous_ranges(days: list[date]) -> list[tuple[date, date]]:
        if not days:
            return []

        ordered = sorted(set(days))
        ranges: list[tuple[date, date]] = []
        start = previous = ordered[0]

        for current in ordered[1:]:
            if current != previous + timedelta(days=1):
                ranges.append((start, previous))
                start = current
            previous = current

        ranges.append((start, previous))
        return ranges
