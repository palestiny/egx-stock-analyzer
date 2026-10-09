from collections.abc import Callable
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.breakout_response import BreakoutResponse
from app.api.fibonacci_response import FibonacciResponse
from app.api.market_intelligence_response import MarketMoverRankingResponse
from app.api.sector_intelligence_response import SectorRankingResponse
from app.api.signal_response import signal_to_dict
from app.api.technical_scanner_response import TechnicalScannerResponse
from app.application.market_intelligence.rank_momentum import RankMomentumLeaders
from app.application.market_intelligence.rank_sectors import RankSectors, SectorInput
from app.application.market_intelligence.run_technical_scanner import RunTechnicalScanner
from app.application.market_intelligence.scan_breakouts import ScanBreakouts
from app.application.market_intelligence.scan_fibonacci import ScanFibonacciOpportunities
from app.application.security.identity import AuthenticatedIdentity
from app.application.signals.generate_signal import GenerateSignal
from app.domain.market_intelligence.sectors import SectorDirection


def create_market_intelligence_router(
    *,
    rank_momentum_leaders: RankMomentumLeaders,
    run_technical_scanner: RunTechnicalScanner,
    rank_sectors: RankSectors,
    scan_fibonacci: ScanFibonacciOpportunities,
    scan_breakouts: ScanBreakouts,
    generate_signal: GenerateSignal,
    require_authenticated: Callable[..., AuthenticatedIdentity],
) -> APIRouter:
    """Register deterministic market-intelligence routes behind the app's auth boundary."""
    router = APIRouter()

    # The dependency object must be attached directly to each route parameter; this
    # local alias only keeps the route declarations readable.
    @router.get("/api/v1/market-intelligence/momentum")
    def get_market_momentum(
        symbols: str = "",
        limit: int = 10,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        requested_symbols = [
            symbol.strip().upper()
            for symbol in symbols.split(",")
            if symbol.strip()
        ]
        try:
            ranking = rank_momentum_leaders.execute(requested_symbols, limit=limit)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return MarketMoverRankingResponse.from_ranking(ranking).to_dict()

    @router.get("/api/v1/market-intelligence/scanners/technical")
    def run_technical_scanner_route(
        symbols: str = "",
        scanner_id: str = "trend-momentum-volume",
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        requested_symbols = [
            symbol.strip().upper()
            for symbol in symbols.split(",")
            if symbol.strip()
        ]
        try:
            result = run_technical_scanner.execute(requested_symbols, scanner_id=scanner_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return TechnicalScannerResponse.from_result(result).to_dict()

    @router.get("/api/v1/market-intelligence/sectors")
    def get_sector_intelligence(
        symbols: str = "",
        direction: str = "leading",
        limit: int = 10,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        pairs = []
        for raw in symbols.split(","):
            parts = raw.split(":", 1)
            if len(parts) == 2:
                pairs.append(SectorInput(parts[0], parts[1]))
        try:
            sector_direction = SectorDirection(direction.strip().lower())
            result = rank_sectors.execute(pairs, direction=sector_direction, limit=limit)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return SectorRankingResponse.from_ranking(result).to_dict()

    @router.get("/api/v1/market-intelligence/fibonacci")
    def scan_fibonacci_route(
        levels: str = "",
        tolerance_percent: Decimal = Decimal("1"),
        limit: int = 20,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        parsed: dict[str, Decimal] = {}
        for raw in levels.split(","):
            parts = raw.split(":", 1)
            if len(parts) == 2:
                try:
                    parsed[parts[0].strip().upper()] = Decimal(parts[1].strip())
                except Exception as error:
                    raise HTTPException(status_code=400, detail="Invalid fibonacci level") from error
        try:
            result = scan_fibonacci.execute(parsed, tolerance_percent=tolerance_percent, limit=limit)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return FibonacciResponse.from_result(result).to_dict()

    @router.get("/api/v1/market-intelligence/breakouts")
    def scan_breakouts_route(
        symbols: str = "",
        tolerance_percent: Decimal = Decimal("1"),
        limit: int = 20,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        requested_symbols = [
            symbol.strip().upper()
            for symbol in symbols.split(",")
            if symbol.strip()
        ]
        try:
            result = scan_breakouts.execute(
                requested_symbols,
                tolerance_percent=tolerance_percent,
                limit=limit,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return BreakoutResponse.from_result(result).to_dict()

    @router.get("/api/v1/signals/{symbol}")
    def get_signal(
        symbol: str,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        try:
            signal = generate_signal.execute(symbol)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if signal is None:
            raise HTTPException(status_code=404, detail=f"No actionable signal for {symbol.upper()}")
        return signal_to_dict(signal)


    return router
