from datetime import date
from pathlib import Path
from uuid import UUID

import pytest

from app.application.fundamental_data.historical_provider import (
    PointInTimeFundamentalDataProvider,
)
from tests.fixtures.m61.versioned_dataset import RepositoryHistoricalDatasetFixture


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "m61"
EGAL_ID = UUID("11111111-1111-1111-1111-111111111111")
COMI_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def dataset() -> RepositoryHistoricalDatasetFixture:
    return RepositoryHistoricalDatasetFixture(FIXTURE_DIR)


def test_fixture_manifest_and_artifact_are_integrity_verified(dataset):
    assert dataset.manifest.dataset_id == "egx-strategy-v0"
    assert dataset.manifest.version == "2026-09-22.1"
    assert dataset.manifest.schema_version == "1"


def test_fixture_loader_filters_market_data_by_stock_and_inclusive_date_range(dataset):
    rows = dataset.get_daily_observations(
        EGAL_ID,
        date(2026, 9, 17),
        date(2026, 9, 18),
    )

    assert [row.close for row in rows] == [101, 102]
    assert all(row.stock_id == EGAL_ID for row in rows)
    assert dataset.get_daily_observations(
        COMI_ID,
        date(2026, 9, 17),
        date(2026, 9, 18),
    )[0].close == 50.5


def test_fixture_loader_rejects_requests_outside_pinned_coverage(dataset):
    with pytest.raises(ValueError, match="outside fixture coverage"):
        dataset.get_daily_observations(
            EGAL_ID,
            date(2026, 9, 16),
            date(2026, 9, 18),
        )


def test_fixture_financial_source_preserves_revisions_for_point_in_time_selection(dataset):
    provider = PointInTimeFundamentalDataProvider(dataset)

    before_revision = provider.get_periods(EGAL_STOCK := _stock("EGAL", EGAL_ID), date(2026, 9, 19))
    after_revision = provider.get_periods(EGAL_STOCK, date(2026, 9, 21))

    assert before_revision[0].revenue == 100
    assert after_revision[0].revenue == 110
    assert before_revision[1].revenue == after_revision[1].revenue == 90


def _stock(symbol, stock_id):
    from app.domain.stocks.stock import Stock

    return Stock.reconstitute(stock_id, symbol, symbol)
