from __future__ import annotations

from tools import m61_free_market_probe as market_probe
from tools import m61_yahoo_symbol_variant_probe as variant_probe


def test_build_url_allows_only_known_symbol_variants():
    for ticker in variant_probe.TICKER_VARIANTS:
        url = market_probe.build_url(ticker)
        assert ticker in url

    try:
        market_probe.build_url("NOTREAL.EY")
    except ValueError as exc:
        assert "fixed M61 exploratory cohort" in str(exc)
    else:
        raise AssertionError("unknown symbols must be rejected")


def test_variant_report_never_copies_price_findings(monkeypatch):
    def fake_probe(symbol, ticker, preserve_raw, output_dir):
        assert symbol == "COMI"
        assert preserve_raw is False
        return {
            "symbol": symbol,
            "ticker": ticker,
            "status_code": 200,
            "observed": {
                "instrument_type": "EQUITY",
                "currency": "EGP",
                "exchange_timezone": "Africa/Cairo",
                "row_count": 1300,
                "first_date": "2019-01-01",
                "last_date": "2025-12-31",
                "validation_findings_total": 1,
                "validation_finding_counts": {"row:invalid_close": 1},
                "validation_findings_sample": ["row[0]:invalid_close=123.45"],
            },
        }

    monkeypatch.setattr(variant_probe, "probe_ticker", fake_probe)
    report = variant_probe.run_variant_probe()

    assert len(report["results"]) == len(variant_probe.TICKER_VARIANTS)
    assert report["raw_prices_saved"] is False
    assert report["dataset_accepted"] is False
    assert "123.45" not in str(report)
    assert all(item["price_values_in_report"] is False for item in report["results"])
