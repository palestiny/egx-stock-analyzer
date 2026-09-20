from dataclasses import FrozenInstanceError

import pytest

from app.domain.market_data.volume import Volume


# Tests that a normal positive integer volume is accepted and stored unchanged.
# This protects the basic valid case for the Volume Value Object.
# Its function is to verify correct handling of a typical positive market volume.
def test_volume_accepts_positive_value():
    volume = Volume(1_000_000)

    assert volume.value == 1_000_000


# Tests that zero volume is allowed.
# This exists because zero is a valid boundary value for the current Volume domain rule.
# Its function is to protect that lower valid boundary from becoming positive-only.
def test_volume_accepts_zero():
    volume = Volume(0)

    assert volume.value == 0


# Tests that negative volume is rejected.
# This exists because volume cannot be negative in the domain model.
# Its function is to verify that invalid negative input raises ValueError.
def test_volume_rejects_negative_value():
    with pytest.raises(ValueError):
        Volume(-1)


# Tests that fractional volume is rejected.
# This exists because the current domain decision defines Volume as an integer Value Object.
# Its function is to prevent decimal quantities from entering the domain model.
def test_volume_rejects_fractional_value():
    with pytest.raises(TypeError):
        Volume(100.5)


# Tests that Volume is immutable after creation.
# This exists because Volume is a Value Object whose value must not change after construction.
# Its function is to protect the frozen Value Object contract.
def test_volume_is_immutable():
    volume = Volume(1_000)

    with pytest.raises(FrozenInstanceError):
        volume.value = 2_000


# Tests that boolean values are rejected even though bool is technically an integer subtype in Python.
# This exists because True/False are not meaningful market volumes.
# Its function is to ensure the domain accepts actual integer quantities rather than Python's bool subtype.
def test_volume_rejects_boolean():
    with pytest.raises(TypeError):
        Volume(True)