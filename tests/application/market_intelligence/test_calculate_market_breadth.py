from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.market_intelligence.calculate_market_breadth import CalculateMarketBreadth
from app.domain.technical_analysis.momentum import MomentumStatus
from app.domain.technical_analysis.trend import TrendStatus
from app.domain.technical_analysis.volume import VolumeStatus


class StubStore:
    def __init__(self, records):
        self.records = records

    def get_record(self, symbol):
        return self.records.get(symbol)


def record(trend, momentum, volume, analysis_date=None):
    return SimpleNamespace(
        analysis_date=analysis_date,
        result=SimpleNamespace(
            technical_analysis=SimpleNamespace(
                trend=SimpleNamespace(status=trend),
                momentum=SimpleNamespace(status=momentum),
                volume=SimpleNamespace(status=volume),
            )
        )
    )


def test_market_breadth_reports_coverage_and_heuristic_stress():
    store = StubStore({
        "AAA": record(TrendStatus.DOWNTREND, MomentumStatus.NEGATIVE, VolumeStatus.ABOVE_AVERAGE),
        "BBB": record(TrendStatus.UPTREND, MomentumStatus.POSITIVE, VolumeStatus.ABOVE_AVERAGE),
        "CCC": record(TrendStatus.SIDEWAYS, MomentumStatus.NEGATIVE, VolumeStatus.BELOW_AVERAGE),
    })

    result = CalculateMarketBreadth(store).execute(["aaa", "bbb", "ccc", "missing"])

    assert result.requested_symbols == 4
    assert result.analyzed_symbols == 3
    assert result.missing_symbols == ("MISSING",)
    assert result.stress_score == 47
    assert result.stress_level == "mixed"
    assert result.bullish_breadth_percent == Decimal("33.33")
    assert result.to_dict()["coverage_percent"] == "75.00"
    assert result.to_dict()["is_trading_signal"] is False


def test_market_breadth_without_any_saved_analysis_is_explicitly_insufficient():
    result = CalculateMarketBreadth(StubStore({})).execute(["AAA", "BBB"])

    assert result.stress_score is None
    assert result.stress_level == "insufficient_data"
    assert result.analyzed_symbols == 0
    assert result.missing_symbols == ("AAA", "BBB")


@pytest.mark.parametrize("symbols, message", [
    ([], "At least one stock symbol is required"),
    (["AAA", " aaa "], "Duplicate stock symbol in market breadth request"),
])
def test_market_breadth_rejects_invalid_symbol_universe(symbols, message):
    with pytest.raises(ValueError, match=message):
        CalculateMarketBreadth(StubStore({})).execute(symbols)



def test_market_breadth_exposes_consistent_analysis_date_evidence():
    observed_date = date(2026, 10, 25)
    store = StubStore({
        "AAA": record(TrendStatus.DOWNTREND, MomentumStatus.NEGATIVE, VolumeStatus.ABOVE_AVERAGE, observed_date),
        "BBB": record(TrendStatus.UPTREND, MomentumStatus.POSITIVE, VolumeStatus.ABOVE_AVERAGE, observed_date),
    })

    payload = CalculateMarketBreadth(store).execute(["AAA", "BBB"]).to_dict()

    assert payload["analysis_dates_by_symbol"] == {
        "AAA": "2026-10-25",
        "BBB": "2026-10-25",
    }
    assert payload["analysis_date_status"] == "CONSISTENT"
    assert payload["latest_analysis_date"] == "2026-10-25"
    assert payload["undated_symbols"] == []
    assert payload["methodology_version"] == "stress-heuristic-v1"


def test_market_breadth_marks_mixed_analysis_dates_without_hiding_the_mismatch():
    store = StubStore({
        "AAA": record(TrendStatus.DOWNTREND, MomentumStatus.NEGATIVE, VolumeStatus.ABOVE_AVERAGE, date(2026, 10, 23)),
        "BBB": record(TrendStatus.UPTREND, MomentumStatus.POSITIVE, VolumeStatus.ABOVE_AVERAGE, date(2026, 10, 25)),
    })

    payload = CalculateMarketBreadth(store).execute(["AAA", "BBB"]).to_dict()

    assert payload["analysis_date_status"] == "MIXED"
    assert payload["latest_analysis_date"] == "2026-10-25"
    assert payload["analysis_dates_by_symbol"]["AAA"] == "2026-10-23"
    assert payload["analysis_dates_by_symbol"]["BBB"] == "2026-10-25"


def test_market_breadth_marks_partial_and_unknown_analysis_dates_explicitly():
    partial_store = StubStore({
        "AAA": record(TrendStatus.DOWNTREND, MomentumStatus.NEGATIVE, VolumeStatus.ABOVE_AVERAGE, date(2026, 10, 25)),
        "BBB": record(TrendStatus.UPTREND, MomentumStatus.POSITIVE, VolumeStatus.ABOVE_AVERAGE),
    })
    partial = CalculateMarketBreadth(partial_store).execute(["AAA", "BBB"]).to_dict()
    assert partial["analysis_date_status"] == "PARTIAL"
    assert partial["undated_symbols"] == ["BBB"]
    assert partial["analysis_dates_by_symbol"]["BBB"] is None

    unknown = CalculateMarketBreadth(StubStore({
        "AAA": record(TrendStatus.DOWNTREND, MomentumStatus.NEGATIVE, VolumeStatus.ABOVE_AVERAGE),
    })).execute(["AAA"]).to_dict()
    assert unknown["analysis_date_status"] == "UNKNOWN"
    assert unknown["latest_analysis_date"] is None
    assert unknown["undated_symbols"] == ["AAA"]
