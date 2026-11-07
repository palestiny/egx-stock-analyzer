from typing import Any, cast

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.market_intelligence.calculate_market_breadth import CalculateMarketBreadth
from app.application.security.identity import AuthenticatedIdentity
from app.api.market_intelligence_routes import create_market_intelligence_router


class EmptyAnalysisStore:
    def get_record(self, symbol: str) -> None:
        return None


def build_client(
    *,
    configured_symbols: tuple[str, ...] = (),
    configured_version: str | None = None,
) -> TestClient:
    store = EmptyAnalysisStore()
    router = create_market_intelligence_router(
        rank_momentum_leaders=cast(Any, None),
        run_technical_scanner=cast(Any, None),
        rank_sectors=cast(Any, None),
        scan_fibonacci=cast(Any, None),
        scan_breakouts=cast(Any, None),
        generate_signal=cast(Any, None),
        calculate_market_breadth=CalculateMarketBreadth(store),
        require_authenticated=lambda: AuthenticatedIdentity.operator(),
        configured_universe_symbols=configured_symbols,
        configured_universe_version=configured_version,
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_breadth_stress_uses_operator_configured_versioned_universe_by_default() -> None:
    client = build_client(
        configured_symbols=("COMI", "EGAL"),
        configured_version="egx-universe-2026-11-v1",
    )

    response = client.get("/api/v1/market-intelligence/breadth-stress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe"] == {
        "source": "OPERATOR_CONFIGURED",
        "version": "egx-universe-2026-11-v1",
        "symbols": ["COMI", "EGAL"],
    }
    assert payload["requested_symbols"] == 2
    assert payload["missing_symbols"] == ["COMI", "EGAL"]
    assert payload["stress_score"] is None


def test_breadth_stress_marks_caller_supplied_universe_as_custom() -> None:
    client = build_client(
        configured_symbols=("COMI", "EGAL"),
        configured_version="egx-universe-2026-11-v1",
    )

    response = client.get(
        "/api/v1/market-intelligence/breadth-stress?symbols=swdy"
    )

    assert response.status_code == 200
    assert response.json()["universe"] == {
        "source": "CALLER_SUPPLIED",
        "version": None,
        "symbols": ["SWDY"],
    }


def test_breadth_stress_without_configured_or_custom_universe_remains_invalid() -> None:
    client = build_client()

    response = client.get("/api/v1/market-intelligence/breadth-stress")

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one stock symbol is required"



def test_router_rejects_configured_universe_without_version() -> None:
    with pytest.raises(ValueError, match="symbols and version must be provided together"):
        build_client(configured_symbols=("COMI",))


def test_router_rejects_configured_universe_version_without_symbols() -> None:
    with pytest.raises(ValueError, match="symbols and version must be provided together"):
        build_client(configured_version="v1")


def test_router_rejects_duplicate_configured_symbols_after_normalization() -> None:
    with pytest.raises(ValueError, match="duplicate symbols"):
        build_client(
            configured_symbols=("COMI", " comi "),
            configured_version="v1",
        )


def test_router_rejects_empty_configured_symbol_entries() -> None:
    with pytest.raises(ValueError, match="empty symbol"):
        build_client(
            configured_symbols=("COMI", " "),
            configured_version="v1",
        )
