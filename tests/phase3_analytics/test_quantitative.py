import pandas as pd
import pytest

from analytics.quantitative import compute_gold_silver_ratio


def test_gsr_elementwise_ratio():
    gold = pd.Series([2000.0, 2200.0])
    silver = pd.Series([25.0, 20.0])
    gsr = compute_gold_silver_ratio(gold, silver)
    assert gsr.iloc[0] == pytest.approx(80.0)
    assert gsr.iloc[1] == pytest.approx(110.0)


def test_gsr_preserves_length_and_index():
    gold = pd.Series([2000.0, 2100.0, 2200.0], index=[10, 11, 12])
    silver = pd.Series([25.0, 25.0, 25.0], index=[10, 11, 12])
    gsr = compute_gold_silver_ratio(gold, silver)
    assert len(gsr) == 3
    assert list(gsr.index) == [10, 11, 12]
    assert gsr.iloc[-1] == pytest.approx(88.0)
