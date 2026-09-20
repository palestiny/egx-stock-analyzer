import pytest
from uuid import UUID
from app.domain.stocks.stock import Stock


# Tests that a Stock exposes its two core business attributes: symbol and name.
# This exists to protect the basic Stock entity contract.
# Its function is to verify that valid creation preserves the supplied business data.
def test_stock_has_symbol_and_name():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert stock.symbol == "COMI"
    assert stock.name == "Commercial International Bank"


# Tests that an empty symbol is rejected.
# This exists because symbol is a required business identifier for Stock.
# Its function is to prevent invalid empty identifiers from entering the domain.
def test_stock_cannot_have_empty_symbol():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="",
            name="Commercial International Bank",
        )


# Tests that a whitespace-only symbol is rejected.
# This exists because whitespace has no business meaning and should not bypass the empty-symbol rule.
# Its function is to verify validation after normalization of meaningless whitespace.
def test_stock_cannot_have_whitespace_only_symbol():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="   ",
            name="Commercial International Bank",
        )


# Tests that Stock normalizes the symbol by trimming whitespace and converting it to uppercase.
# This exists to keep the business identifier in a consistent canonical form.
# Its function is to verify the normalization rule used during creation.
def test_stock_normalizes_symbol():
    stock = Stock.create(
        symbol="  comi  ",
        name="Commercial International Bank",
    )

    assert stock.symbol == "COMI"


# Tests that an empty name is rejected.
# This exists because Stock requires a meaningful display/business name.
# Its function is to prevent an empty name from entering the entity.
def test_stock_cannot_have_empty_name():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="COMI",
            name="",
        )


# Tests that a whitespace-only name is rejected.
# This exists because whitespace alone is not a meaningful stock name.
# Its function is to verify the name validation rule after trimming.
def test_stock_cannot_have_whitespace_only_name():
    with pytest.raises(ValueError):
        Stock.create(
            symbol="COMI",
            name="   ",
        )


# Tests that Stock normalizes its name by removing surrounding whitespace.
# This exists to keep stored business data consistent without changing the meaningful name text.
# Its function is to verify name normalization during creation.
def test_stock_normalizes_name():
    stock = Stock.create(
        symbol="COMI",
        name="  Commercial International Bank  ",
    )

    assert stock.name == "Commercial International Bank"


# Tests that two newly created Stocks with different identities are not equal.
# This exists because Stock equality is based on entity identity, not merely matching business fields.
# Its function is to protect entity semantics when two records happen to describe the same stock data.
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


# Tests that Stocks with different symbols are not equal.
# This exists as a concrete example that independently created entities remain distinct even when their business data differs.
# Its function is to protect the entity equality behavior.
def test_stocks_with_different_symbols_are_not_equal():
    stock1 = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    stock2 = Stock.create(
        symbol="SWDY",
        name="Elsewedy Electric",
    )

    assert stock1 != stock2


# Tests that every newly created Stock receives a UUID identity.
# This exists because identity is fundamental to the Stock entity model.
# Its function is to verify the type and presence of the generated identifier.
def test_stock_has_id():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert isinstance(stock.id, UUID)


# Tests that an existing Stock can be reconstructed using its persisted identity.
# This exists to support the domain distinction between creating a new entity and restoring an existing one.
# Its function is to verify that reconstitution preserves the original entity ID.
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


# Tests that two Stock objects representing the same entity identity are equal.
# This exists because entity equality is defined by identity rather than by all field values.
# Its function is to protect equality across a create/reconstitute lifecycle.
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


# Tests that the create factory generates a new UUID identity.
# This exists to explicitly protect the creation path responsible for new Stock entities.
# Its function is to verify that create does not require an externally supplied ID.
def test_stock_create_generates_id():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    assert isinstance(stock.id, UUID)


# Tests that create and reconstitute are the two intended Stock creation paths.
# This exists to document and protect the lifecycle boundary between creating and restoring an entity.
# Its function is to verify that reconstitution preserves the identity generated by create.
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