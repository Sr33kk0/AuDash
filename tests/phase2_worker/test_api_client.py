import pytest

from worker.api_client import GRAMS_PER_TROY_OZ, convert_oz_to_grams


def test_grams_per_troy_oz_constant():
    assert GRAMS_PER_TROY_OZ == 31.1034768


def test_convert_oz_to_grams():
    # 31.1034768 MYR/oz -> 1.0 MYR/gram
    assert convert_oz_to_grams(31.1034768) == pytest.approx(1.0)
    assert convert_oz_to_grams(12000.0) == pytest.approx(12000.0 / 31.1034768)
