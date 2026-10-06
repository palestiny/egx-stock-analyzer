from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import random
from uuid import UUID, uuid5

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume

class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    CRASH = "crash"

@dataclass(frozen=True)
class SyntheticScenario:
    name: str
    description: str
    seed: int
    symbols: tuple[str, ...]
    bars_per_symbol: int

@dataclass(frozen=True)
class SyntheticSymbolSeries:
    symbol: str
    stock_id: UUID
    bars: tuple[PriceBar, ...]
    regimes: tuple[MarketRegime, ...]

@dataclass(frozen=True)
class SyntheticDataset:
    scenario: SyntheticScenario
    series: tuple[SyntheticSymbolSeries, ...]

class SyntheticMarketGenerator:
    """Deterministic market generator for feature/backtest validation.

    Output is development/test evidence only and must never be accepted
    as real historical evidence.
    """

    NAMESPACE = UUID("3e4e7e7b-2c77-4baf-8c6b-5b4c8b1b0d51")

    def generate(
        self, *, symbols: tuple[str, ...], bars_per_symbol: int = 1260,
        seed: int = 61001,
        start: datetime = datetime(2021, 1, 3, tzinfo=timezone.utc),
    ) -> SyntheticDataset:
        if not symbols:
            raise ValueError("symbols cannot be empty")
        if bars_per_symbol < 30:
            raise ValueError("bars_per_symbol must be at least 30")
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("start must be timezone-aware")

        scenario = SyntheticScenario(
            name="m61-controlled-egx-research",
            description=(
                "Controlled synthetic daily market paths covering trend, "
                "range, volatility, breakout/pullback and crash regimes."
            ),
            seed=seed, symbols=symbols, bars_per_symbol=bars_per_symbol,
        )
        series = tuple(
            self._generate_symbol(symbol=symbol, bars_per_symbol=bars_per_symbol,
                                  seed=seed + index * 1009, start=start)
            for index, symbol in enumerate(symbols)
        )
        return SyntheticDataset(scenario=scenario, series=series)

    def _generate_symbol(self, *, symbol: str, bars_per_symbol: int,
                         seed: int, start: datetime) -> SyntheticSymbolSeries:
        rng = random.Random(seed)
        stock_id = uuid5(self.NAMESPACE, symbol)
        price = Decimal(str(40 + rng.randrange(20, 180)))
        bars: list[PriceBar] = []
        regimes: list[MarketRegime] = []

        for index in range(bars_per_symbol):
            regime = self._regime_for(index, bars_per_symbol)
            regimes.append(regime)
            drift, volatility = self._parameters(regime)
            shock = rng.gauss(0.0, volatility)
            if rng.random() < 0.025:
                shock += rng.gauss(0.0, volatility * 4)
            if regime is MarketRegime.CRASH:
                shock -= 0.035 + abs(rng.gauss(0.0, 0.012))

            daily_return = Decimal(str(max(-0.75, drift + shock)))
            open_price = price
            close_price = max(Decimal("0.01"), open_price * (Decimal("1") + daily_return))
            intraday = abs(float(daily_return)) + volatility * 2.0
            high = max(open_price, close_price) * Decimal(str(1 + abs(rng.gauss(0, intraday / 3))))
            low = min(open_price, close_price) * Decimal(str(max(0.01, 1 - abs(rng.gauss(0, intraday / 3)))))
            volume = 100_000 + rng.randrange(0, 900_000)
            if regime in (MarketRegime.HIGH_VOLATILITY, MarketRegime.CRASH):
                volume *= 2
            if index in (180, 181, 182, 183):
                volume *= 4

            bars.append(PriceBar.create(
                stock_id=stock_id, timeframe=Timeframe.DAILY,
                timestamp=start + timedelta(days=index),
                open=Price(open_price), high=Price(max(high, open_price, close_price)),
                low=Price(min(low, open_price, close_price)), close=Price(close_price),
                volume=Volume(volume),
            ))
            price = close_price

        return SyntheticSymbolSeries(symbol=symbol, stock_id=stock_id,
                                     bars=tuple(bars), regimes=tuple(regimes))

    @staticmethod
    def _regime_for(index: int, total: int) -> MarketRegime:
        ratio = index / max(total - 1, 1)
        if 0.10 <= ratio < 0.22: return MarketRegime.SIDEWAYS
        if 0.22 <= ratio < 0.38: return MarketRegime.BULL
        if 0.38 <= ratio < 0.50: return MarketRegime.HIGH_VOLATILITY
        if 0.50 <= ratio < 0.56: return MarketRegime.CRASH
        if 0.56 <= ratio < 0.72: return MarketRegime.BEAR
        if 0.72 <= ratio < 0.88: return MarketRegime.BULL
        return MarketRegime.SIDEWAYS

    @staticmethod
    def _parameters(regime: MarketRegime) -> tuple[float, float]:
        return {
            MarketRegime.BULL: (0.0012, 0.012),
            MarketRegime.BEAR: (-0.0010, 0.015),
            MarketRegime.SIDEWAYS: (0.0001, 0.009),
            MarketRegime.HIGH_VOLATILITY: (0.0002, 0.032),
            MarketRegime.CRASH: (-0.008, 0.045),
        }[regime]