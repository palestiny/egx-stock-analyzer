from decimal import Decimal
from dataclasses import FrozenInstanceError
import pytest

from app.domain.market_data.price import Price


# Tests that a normal positive market price is accepted and stored unchanged.
# This protects the basic valid case required for Price to represent real prices.
# Its function is to verify that valid positive input reaches the Value Object correctly.
def test_price_accepts_positive_value():
    price = Price(Decimal("125.50"))

    assert price.value == Decimal("125.50")


# Tests that zero is a valid Price value.
# This exists because the domain decision explicitly allows zero and should not accidentally become positive-only.
# Its function is to protect the lower valid boundary of Price.
def test_price_accepts_zero():
    price = Price(Decimal("0"))

    assert price.value == Decimal("0")


# Tests that Price does not impose a fixed decimal scale.
# This exists because market prices may require different decimal precision and the Value Object should preserve it.
# Its function is to verify that a value with three decimal places is accepted unchanged.
def test_price_accepts_three_decimal_places():
    price = Price(Decimal("0.123"))

    assert price.value == Decimal("0.123")


# Tests that negative prices are rejected.
# This exists because a negative market Price violates the current domain invariant.
# Its function is to verify that invalid negative input raises ValueError.
def test_price_rejects_negative_value():
    with pytest.raises(ValueError):
        Price(Decimal("-0.001"))


# Tests that Price is immutable after creation.
# This exists because Price is a Value Object and its value must not change after construction.
# Its function is to protect the frozen Value Object contract.
def test_price_is_immutable():
    price = Price(Decimal("100"))

    with pytest.raises(FrozenInstanceError):
        price.value = Decimal("200")