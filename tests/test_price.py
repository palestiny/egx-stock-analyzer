from decimal import Decimal
from dataclasses import FrozenInstanceError
import pytest

from app.domain.market_data.price import Price


def test_price_accepts_positive_value():
    price = Price(Decimal("125.50"))

    assert price.value == Decimal("125.50")


def test_price_accepts_zero():
    price = Price(Decimal("0"))

    assert price.value == Decimal("0")


def test_price_accepts_three_decimal_places():
    price = Price(Decimal("0.123"))

    assert price.value == Decimal("0.123")


def test_price_rejects_negative_value():
    with pytest.raises(ValueError):
        Price(Decimal("-0.001"))

def test_price_is_immutable():
    price = Price(Decimal("100"))

    with pytest.raises(FrozenInstanceError):
        price.value = Decimal("200")