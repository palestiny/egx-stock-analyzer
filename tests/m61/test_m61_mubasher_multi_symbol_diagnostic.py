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
    lines = []
    for index in range(35):
        session = date(2024, 1, 1) + timedelta(days=index)
        close = Decimal("10") + Decimal(index) / Decimal("10")
        lines.append(
            f"{session.isoformat()}/00:00:00,{close - Decimal('0.05')},"
            f"{close + Decimal('0.1')},{close - Decimal('0.1')},{close},1000"
        )
    lines.append("2024-02-05/00:00:00,20,19,18,21,1000")
    lines.append("2024-99-99/00:00:00,20,21,19,20.5,1000")
    lines.append("malformed,row")
    payload = ("\n".join(lines) + "\n").encode()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return payload

    monkeypatch.setattr(
        diagnostic.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )
    rows = diagnostic._fetch_rows(
        "COMI", "https://example.test/COMI", "https://example.test/data.csv"
    )

    assert len(rows) == 35
    assert rows[0]["date"] == "2024-01-01"
    assert rows[-1]["date"] == "2024-02-04"


def test_forward_diagnostic_aggregates_symbols_on_shared_window(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostic,
        "_fetch_rows",
        lambda _symbol, _page, _url: _rows(),
    )

    report = diagnostic.run()

    assert report["status"] == "completed"
    assert report["common_window"] == {"start": "2024-01-01", "end": "2024-03-20"}
    assert set(report["symbols"]) == set(diagnostic.SOURCES)
    assert report["pooled_by_signal_group"]["all_eligible_sessions"]["5"]["samples"] > 100
    assert not report["failures"]



def test_source_failures_return_a_report_instead_of_crashing(monkeypatch) -> None:
    def fail(_symbol, _page, _url):
        raise TimeoutError("source timed out")

    monkeypatch.setattr(diagnostic, "_fetch_rows", fail)
    report = diagnostic.run()

    assert report["status"] == "insufficient_source_data"
    assert len(report["failures"]) == len(diagnostic.SOURCES)
    assert report["symbols_retrieved"] == []



def test_cli_exits_nonzero_when_sources_are_insufficient(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        diagnostic,
        "run",
        lambda: {
            "diagnostic": "test",
            "status": "insufficient_source_data",
            "failures": {"COMI": "TimeoutError"},
        },
    )

    try:
        diagnostic.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("CLI must fail when source data is insufficient")

    assert '"status": "insufficient_source_data"' in capsys.readouterr().out


def test_pre_breakout_proxy_requires_momentum_volume_and_prior_resistance() -> None:
    rows = _rows(80)
    # Make one controlled near-resistance setup at index 30. Resistance is
    # computed from the prior 20 bars, so the current bar cannot set its own level.
    rows[30]["open"] = Decimal("12.75")
    rows[30]["high"] = Decimal("12.90")
    rows[30]["low"] = Decimal("12.70")
    rows[30]["close"] = Decimal("12.80")
    rows[30]["volume"] = Decimal("3000")

    result = diagnostic._evaluate(rows)
    group = result["pre_breakout_proxy_momentum_volume_near_20_session_resistance"]

    assert group["1"]["samples"] >= 1
    assert group["3"]["samples"] >= 1
    assert "pre_breakout_proxy" in diagnostic.run.__code__.co_consts
