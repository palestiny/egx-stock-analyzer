from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from app.application.market_data.operational_store import (
    MarketDataConflictError,
    MarketDataCoverageError,
    OperationalMarketDataService,
)
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


COMI_ID = UUID("e443c130-8f6d-50dc-b25b-45f495593138")
COMI = Stock.reconstitute(COMI_ID, "COMI", "Commercial International Bank")


def observation(day: date, close: str = "100.00") -> RawPriceBarObservation:
    value = Decimal(close)
    return RawPriceBarObservation(
        stock_id=COMI_ID,
        timeframe=Timeframe.DAILY,
        timestamp=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=1000,
    )


class FakeProvider:
    def __init__(self, observations: list[RawPriceBarObservation]) -> None:
        self._observations = observations
        self.calls: list[tuple[date, date]] = []

    def get_daily_observations(self, stock, from_date: date, to_date: date):
        assert stock.id == COMI_ID
        self.calls.append((from_date, to_date))
        return [
            item
            for item in self._observations
            if from_date <= item.timestamp.date() <= to_date
        ]


class WeekdayCalendar:
    def expected_sessions(self, from_date: date, to_date: date) -> list[date]:
        current = from_date
        sessions = []
        while current <= to_date:
            if current.weekday() < 5:
                sessions.append(current)
            current = date.fromordinal(current.toordinal() + 1)
        return sessions


class InMemoryStore:
    def __init__(self) -> None:
        self.items: dict[tuple[UUID, Timeframe, datetime], RawPriceBarObservation] = {}

    def get_daily_observations(self, stock_id, from_date: date, to_date: date):
        return sorted(
            (
                item
                for item in self.items.values()
                if item.stock_id == stock_id
                and from_date <= item.timestamp.date() <= to_date
            ),
            key=lambda item: item.timestamp,
        )

    def save(self, observations):
        for item in observations:
            key = (item.stock_id, item.timeframe, item.timestamp)
            existing = self.items.get(key)
            if existing is not None and existing != item:
                raise MarketDataConflictError(key, existing, item)
            self.items[key] = item


def service(provider, store):
    return OperationalMarketDataService(
        provider=provider,
        store=store,
        session_calendar=WeekdayCalendar(),
    )


def test_empty_store_acquires_and_persists_only_expected_sessions() -> None:
    provider = FakeProvider(
        [observation(date(2026, 9, day), str(100 + day)) for day in range(21, 26)]
    )
    store = InMemoryStore()

    service(provider, store).ensure_daily_coverage(
        COMI,
        date(2026, 9, 21),
        date(2026, 9, 27),
    )

    assert len(store.items) == 5
    assert provider.calls == [(date(2026, 9, 21), date(2026, 9, 27))]


def test_repeat_request_does_not_call_provider_for_covered_sessions() -> None:
    provider = FakeProvider(
        [observation(date(2026, 9, day), str(100 + day)) for day in range(21, 26)]
    )
    store = InMemoryStore()
    sut = service(provider, store)

    sut.ensure_daily_coverage(COMI, date(2026, 9, 21), date(2026, 9, 25))
    provider.calls.clear()

    sut.ensure_daily_coverage(COMI, date(2026, 9, 21), date(2026, 9, 25))

    assert provider.calls == []


def test_wider_request_acquires_only_the_missing_range() -> None:
    provider = FakeProvider(
        [observation(date(2026, 9, day), str(100 + day)) for day in range(21, 30)]
    )
    store = InMemoryStore()
    sut = service(provider, store)

    sut.ensure_daily_coverage(COMI, date(2026, 9, 21), date(2026, 9, 25))
    provider.calls.clear()

    sut.ensure_daily_coverage(COMI, date(2026, 9, 21), date(2026, 9, 29))

    assert provider.calls == [(date(2026, 9, 26), date(2026, 9, 29))]
    assert len(store.items) == 7


def test_weekend_dates_are_not_treated_as_missing_sessions() -> None:
    provider = FakeProvider(
        [observation(date(2026, 9, 25)), observation(date(2026, 9, 28))]
    )
    store = InMemoryStore()

    service(provider, store).ensure_daily_coverage(
        COMI,
        date(2026, 9, 25),
        date(2026, 9, 28),
    )

    assert len(store.items) == 2


def test_provider_gap_is_not_accepted_as_complete_coverage() -> None:
    provider = FakeProvider([observation(date(2026, 9, 21))])
    store = InMemoryStore()

    with pytest.raises(MarketDataCoverageError) as error:
        service(provider, store).ensure_daily_coverage(
            COMI,
            date(2026, 9, 21),
            date(2026, 9, 22),
        )

    assert error.value.missing_dates == (date(2026, 9, 22),)
    assert store.items == {}


def test_identical_duplicate_is_idempotent() -> None:
    store = InMemoryStore()
    item = observation(date(2026, 9, 25))

    store.save([item])
    store.save([item])

    assert len(store.items) == 1


def test_conflicting_duplicate_is_explicit_and_never_overwritten() -> None:
    store = InMemoryStore()
    original = observation(date(2026, 9, 25), "100.00")
    incoming = observation(date(2026, 9, 25), "101.00")
    store.save([original])

    with pytest.raises(MarketDataConflictError):
        store.save([incoming])

    assert store.items[(COMI_ID, Timeframe.DAILY, original.timestamp)] == original
