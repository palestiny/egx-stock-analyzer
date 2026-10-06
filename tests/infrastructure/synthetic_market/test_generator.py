from app.infrastructure.synthetic_market.generator import MarketRegime, SyntheticMarketGenerator

SYMBOLS = ("COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO")

def test_generator_is_deterministic_and_covers_controlled_regimes():
    generator = SyntheticMarketGenerator()
    first = generator.generate(symbols=SYMBOLS, bars_per_symbol=300, seed=123)
    second = generator.generate(symbols=SYMBOLS, bars_per_symbol=300, seed=123)
    assert first == second
    assert len(first.series) == 10
    assert all(len(series.bars) == 300 for series in first.series)
    regimes = set(first.series[0].regimes)
    assert {MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.SIDEWAYS, MarketRegime.HIGH_VOLATILITY, MarketRegime.CRASH} <= regimes

def test_generator_produces_valid_ohlcv_and_unique_stock_identity():
    dataset = SyntheticMarketGenerator().generate(symbols=("COMI", "EGAL"), bars_per_symbol=120, seed=77)
    assert dataset.series[0].stock_id != dataset.series[1].stock_id
    for series in dataset.series:
        previous = None
        for bar in series.bars:
            assert bar.low.value <= bar.open.value <= bar.high.value
            assert bar.low.value <= bar.close.value <= bar.high.value
            assert bar.volume.value >= 0
            if previous is not None:
                assert bar.timestamp > previous
            previous = bar.timestamp

def test_generator_rejects_invalid_inputs():
    generator = SyntheticMarketGenerator()
    try:
        generator.generate(symbols=(), bars_per_symbol=100)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        generator.generate(symbols=("COMI",), bars_per_symbol=29)
        assert False, "expected ValueError"
    except ValueError:
        pass