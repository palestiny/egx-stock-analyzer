import pytest
from uuid import UUID
from app.domain.stocks.stock import Stock

def test_stock_has_symbol_and_name():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert stock.symbol == "COMI"
    assert stock.name == "Commercial International Bank"

def test_stock_cannot_have_empty_symbol():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="",
            name="Commercial International Bank",
        )

def test_stock_cannot_have_whitespace_only_symbol():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="   ",
            name="Commercial International Bank",
        )

def test_stock_normalizes_symbol():
    stock = Stock.create(
        symbol="  comi  ",
        name="Commercial International Bank",
    )

    assert stock.symbol == "COMI"

def test_stock_cannot_have_empty_name():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="COMI",
            name="",
        )

def test_stock_cannot_have_whitespace_only_name():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="COMI",
            name="   ",
        )

def test_stock_normalizes_name():
    stock = Stock.create(
        symbol="COMI",
        name="  Commercial International Bank  ",
    )

    assert stock.name == "Commercial International Bank"

def test_stocks_with_different_ids_are_not_equal():
    stock1 = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    stock2 = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert stock1 != stock2

def test_stocks_with_different_symbols_are_not_equal():
    stock1 = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    stock2 = Stock.create   (
        symbol="SWDY",
        name="Elsewedy Electric",
    )

    assert stock1 != stock2

def test_stock_has_id():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert isinstance(stock.id, UUID)

def test_stock_can_be_reconstituted_with_existing_id():
    original = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    restored = Stock.reconstitute(
        id=original.id,
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert restored.id == original.id

def test_stocks_with_same_id_are_equal():
    original = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    restored = Stock.reconstitute(
        id=original.id,
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert original == restored

def test_stock_create_generates_id():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert isinstance(stock.id, UUID)

def test_stock_create_and_reconstitute_are_the_creation_paths():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    restored = Stock.reconstitute(
        id=stock.id,
        symbol=stock.symbol,
        name=stock.name,
    )

    assert restored.id == stock.id