from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from app.application.market_data.acquisition import AcquisitionStatus
from app.application.market_data.operational_store import MarketDataConflictError
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock
from app.infrastructure.persistence.sqlite_operational_market_data_store import (
    SQLiteOperationalMarketDataStore,
)


COMI_ID = UUID("e443c130-8f6d-50dc-b25b-45f495593138")
COMI = Stock.reconstitute(COMI_ID, "COMI", "Commercial International Bank")


def observation(day: date, close: str) -> RawPriceBarObservation:
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


def acquisition():
    from app.application.market_data.acquisition import AcquisitionRecord

    return AcquisitionRecord.success(
        provider="fixture",
        source_symbol="COMI",
        stock_id=COMI_ID,
        requested_from=date(2026, 9, 25),
        requested_to=date(2026, 9, 25),
        actual_from=date(2026, 9, 25),
        actual_to=date(2026, 9, 25),
        requested_at=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
        completed_at=datetime(2026, 9, 25, 10, 1, tzinfo=timezone.utc),
        row_count=1,
    )


def test_sqlite_round_trip_survives_store_recreation(tmp_path):
    database = tmp_path / "market-data.db"
    store = SQLiteOperationalMarketDataStore(database)
    item = observation(date(2026, 9, 25), "100.00")
    record = acquisition()

    store.persist_successful_acquisition(record, [item])

    recreated = SQLiteOperationalMarketDataStore(database)
    assert recreated.get_daily_observations(
        COMI_ID, date(2026, 9, 25), date(2026, 9, 25)
    ) == [item]
    assert recreated.get_acquisitions(
        COMI_ID, date(2026, 9, 25), date(2026, 9, 25)
    )[0] == record


def test_conflict_is_durable_and_original_observation_is_unchanged(tmp_path):
    database = tmp_path / "market-data.db"
    store = SQLiteOperationalMarketDataStore(database)
    original = observation(date(2026, 9, 25), "100.00")
    incoming = observation(date(2026, 9, 25), "101.00")
    first = acquisition()
    second = acquisition()

    store.persist_successful_acquisition(first, [original])

    with pytest.raises(MarketDataConflictError) as error:
        store.persist_successful_acquisition(second, [incoming])

    assert error.value.acquisition_id == second.acquisition_id

    recreated = SQLiteOperationalMarketDataStore(database)
    assert recreated.get_daily_observations(
        COMI_ID, date(2026, 9, 25), date(2026, 9, 25)
    ) == [original]

    acquisitions = recreated.get_acquisitions(
        COMI_ID, date(2026, 9, 25), date(2026, 9, 25)
    )
    conflicted = [item for item in acquisitions if item.acquisition_id == second.acquisition_id]
    assert len(conflicted) == 1
    assert conflicted[0].status is AcquisitionStatus.CONFLICTED

    events = recreated.get_conflict_events(
        COMI_ID, date(2026, 9, 25), date(2026, 9, 25)
    )
    assert len(events) == 1
    assert events[0].acquisition_id == second.acquisition_id
    assert events[0].detected_at.tzinfo == timezone.utc
    assert events[0].existing_acquisition_id == first.acquisition_id
    assert events[0].existing_observation == original
    assert events[0].incoming_observation == incoming


def test_identical_duplicate_does_not_overwrite_and_remains_queryable(tmp_path):
    database = tmp_path / "market-data.db"
    store = SQLiteOperationalMarketDataStore(database)
    item = observation(date(2026, 9, 25), "100.00")
    first = acquisition()
    second = acquisition()

    store.persist_successful_acquisition(first, [item])
    store.persist_successful_acquisition(second, [item])

    assert store.get_daily_observations(
        COMI_ID, date(2026, 9, 25), date(2026, 9, 25)
    ) == [item]
    assert store.get_conflict_events(
        COMI_ID, date(2026, 9, 25), date(2026, 9, 25)
    ) == []
