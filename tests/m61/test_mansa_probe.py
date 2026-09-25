from egx_stock_analyzer_m61_probe import build_url


def test_build_url_encodes_query_parameters():
    url = build_url(
        "/api/v1/markets/exchanges/EGX/stocks/EGAL/history",
        {"from": "2020-01-01", "to": "2025-12-31", "order": "asc", "limit": "20000"},
    )
    assert url == (
        "https://mansaapi.com/api/v1/markets/exchanges/EGX/stocks/EGAL/history"
        "?from=2020-01-01&to=2025-12-31&order=asc&limit=20000"
    )
