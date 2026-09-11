from dataclasses import FrozenInstanceError

import pytest

from app.domain.market_data.volume import Volume


def test_volume_accepts_positive_value():
    volume = Volume(1_000_000)

    assert volume.value == 1_000_000


def test_volume_accepts_zero():
    volume = Volume(0)

    assert volume.value == 0


def test_volume_rejects_negative_value():
    with pytest.raises(ValueError):
        Volume(-1)


def test_volume_rejects_fractional_value():
    with pytest.raises(TypeError):
        Volume(100.5)


def test_volume_is_immutable():
    volume = Volume(1_000)

    with pytest.raises(FrozenInstanceError):
        volume.value = 2_000

def test_volume_rejects_boolean():
    with pytest.raises(TypeError):
        Volume(True)