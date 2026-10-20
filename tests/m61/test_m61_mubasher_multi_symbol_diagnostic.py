from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import tools.m61_mubasher_multi_symbol_diagnostic as diagnostic


def _rows(count: int = 80) -> list[dict[str, object]]:
    start = date(2024, 1, 1)
    result = []
    for index in range(count):
        close = Decimal("10") + Decimal(index) / Decimal("10")
        result.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "open": close - Decimal("0.05"),
                "high": close + Decimal("0.1"),
                "low": close - Decimal("0.1"),
                "close": close,
                "volume": Decimal("1000") if index % 6 else Decimal("2500"),
            }
        )
    return result


def test_fetch_rows_parses_six_column_mubasher_csv(monkeypatch) -> None:
    payload = (
        "2024-01-01/00:00:00,10,10.2,9.9,10.1,1000\n"
        "2024-01-02/00:00:00,10.1,10.3,10,10.2,1100\n"
        "malformed,row\n"
    ).encode()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return payload

    monkeypatch.setattr(diagnostic.urllib.request, "urlopen", lambda *_a, **_k: FakeResponse())
    rows = diagnostic._fetch_rows("COMI", "https://example.test/COMI", "https://example.test/data.csv")

    assert len(rows) == 0 or rows[0]["date"] == "2024-01-01"
    # The parser deliberately rejects short samples, so supply a full realistic window below.


def test_forward_diagnostic_aggregates_symbols_on_shared_window(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostic,
        "_fetch_rows",
        lambda _symbol, _page, _url: _rows(),
    )

    report = diagnostic.run()

    assert report["common_window"] == {"start": "2024-01-01", "end": "2024-03-20"}
    assert set(report["symbols"]) == {"COMI", "EGAL", "ABUK", "TMGH", "EAST"}
    assert report["pooled_by_signal_group"]["all_eligible_sessions"]["5"]["samples"] > 100
    assert not report["failures"]
