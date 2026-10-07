from decimal import Decimal

from app.infrastructure.synthetic_market.generator import SyntheticMarketGenerator
from app.infrastructure.synthetic_market.portfolio_harness import SyntheticPortfolioHarness


SYMBOLS = ("COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO")


def test_portfolio_harness_covers_full_synthetic_cohort():
    dataset = SyntheticMarketGenerator().generate(
        symbols=SYMBOLS, bars_per_symbol=80, seed=61001
    )
    report = SyntheticPortfolioHarness().run(dataset)
    assert len(report.positions) == 10
    assert report.metrics.portfolio_returns
    assert Decimal("0") <= report.cash_weight <= Decimal("1")


def test_portfolio_harness_is_reproducible():
    generator = SyntheticMarketGenerator()
    first = SyntheticPortfolioHarness().run(
        generator.generate(symbols=SYMBOLS, bars_per_symbol=80, seed=61001)
    )
    second = SyntheticPortfolioHarness().run(
        generator.generate(symbols=SYMBOLS, bars_per_symbol=80, seed=61001)
    )
    assert first == second


def test_portfolio_harness_uses_equal_weight_with_cash_if_cap_requires_it():
    dataset = SyntheticMarketGenerator().generate(
        symbols=SYMBOLS, bars_per_symbol=80, seed=61001
    )
    report = SyntheticPortfolioHarness(
        max_single_name_weight=Decimal("0.08")
    ).run(dataset)
    assert report.cash_weight == Decimal("0.2")
