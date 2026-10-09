from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from app.application.market_data.acquisition import AcquisitionRecord
from app.application.market_data.provider import MarketDataProvider
from app.application.market_data.store import OperationalMarketDataStore
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.stocks.stock import Stock

if TYPE_CHECKING:
    from app.application.market_data.conflict import MarketDataConflictEvent


class MarketDataConflictError(ValueError):
    def __init__(
        self,
        key,
        existing: RawPriceBarObservation,
        incoming: RawPriceBarObservation,
        *,
        acquisition_id: UUID | None = None,
        conflict_event: "MarketDataConflictEvent | None" = None,
    ) -> None:
        super().__init__(f"Market data conflict for identity {key}")
        self.key = key
        self.existing = existing
        self.incoming = incoming
        self.acquisition_id = acquisition_id
        self.conflict_event = conflict_event


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
    def __init__(
        self,
        provider: MarketDataProvider,
        store: OperationalMarketDataStore,
        session_calendar,
        provider_name: str = "unknown",
    ) -> None:
        self._provider = provider
        self._store = store
        self._session_calendar = session_calendar
        self._provider_name = provider_name

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
        existing_dates = {
            item.timestamp.date()
            for item in existing
            if item.timestamp is not None
        }
        expected = self._session_calendar.expected_sessions(from_date, to_date)
        missing = [day for day in expected if day not in existing_dates]

        for range_start, range_end in self._contiguous_ranges(missing):
            self._acquire_range(stock, range_start, range_end, expected)

        return self._store.get_daily_observations(
            stock.id, from_date, to_date
        )

    def _acquire_range(
        self,
        stock: Stock,
        range_start: date,
        range_end: date,
        expected: list[date],
    ) -> None:
        requested_at = datetime.now(timezone.utc)
        try:
            incoming = self._provider.get_daily_observations(
                stock,
                range_start,
                range_end,
            )
            incoming_dates = {
                item.timestamp.date()
                for item in incoming
                if item.stock_id == stock.id and item.timestamp is not None
            }
            requested_sessions = [
                day for day in expected if range_start <= day <= range_end
            ]
            unresolved = [
                day for day in requested_sessions if day not in incoming_dates
            ]
            if unresolved:
                error = MarketDataCoverageError(unresolved)
                self._store.save_acquisition(
                    AcquisitionRecord.failure(
                        provider=self._provider_name,
                        source_symbol=stock.symbol,
                        stock_id=stock.id,
                        requested_from=range_start,
                        requested_to=range_end,
                        requested_at=requested_at,
                        completed_at=datetime.now(timezone.utc),
                        error=str(error),
                        row_count=len(incoming),
                        actual_from=self._actual_date(incoming),
                        actual_to=self._actual_date(incoming, latest=True),
                    )
                )
                raise error

            record = AcquisitionRecord.success(
                provider=self._provider_name,
                source_symbol=stock.symbol,
                stock_id=stock.id,
                requested_from=range_start,
                requested_to=range_end,
                actual_from=self._actual_date(incoming),
                actual_to=self._actual_date(incoming, latest=True),
                requested_at=requested_at,
                completed_at=datetime.now(timezone.utc),
                row_count=len(incoming),
            )
            self._store.persist_successful_acquisition(record, incoming)
        except MarketDataCoverageError:
            raise
        except MarketDataConflictError:
            raise
        except Exception as exc:
            self._store.save_acquisition(
                AcquisitionRecord.failure(
                    provider=self._provider_name,
                    source_symbol=stock.symbol,
                    stock_id=stock.id,
                    requested_from=range_start,
                    requested_to=range_end,
                    requested_at=requested_at,
                    completed_at=datetime.now(timezone.utc),
                    error=str(exc),
                )
            )
            raise

    @staticmethod
    def _actual_date(
        observations: list[RawPriceBarObservation],
        *,
        latest: bool = False,
    ) -> date | None:
        dates = [
            item.timestamp.date()
            for item in observations
            if item.timestamp is not None
        ]
        if not dates:
            return None
        return max(dates) if latest else min(dates)

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
