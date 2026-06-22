import math

import pandas as pd
import pytest

from analytics.spread import (
    GRAMS_PER_TROY_OZ,
    effective_spread,
    per_gram,
    platform_rates,
    realized_spread,
    recency_weighted_mean,
    spot_on_or_before,
    staleness_weight,
)


def test_per_gram_constant_and_conversion():
    assert GRAMS_PER_TROY_OZ == 31.1034768
    assert per_gram(31.1034768) == pytest.approx(1.0)


def test_realized_spread_buy_is_markup():
    assert realized_spread(105.0, 100.0, "BUY") == pytest.approx(5.0)


def test_realized_spread_sell_is_haircut():
    assert realized_spread(95.0, 100.0, "SELL") == pytest.approx(5.0)


def test_realized_spread_rejects_bad_side():
    with pytest.raises(ValueError):
        realized_spread(100.0, 100.0, "HOLD")


def test_recency_weighted_mean_equal_ages_is_plain_mean():
    assert recency_weighted_mean([10.0, 20.0], [0.0, 0.0], 30.0) == pytest.approx(15.0)


def test_recency_weighted_mean_favors_recent():
    # old sample (age 1000, alpha 1) is weighted ~0 -> result ~ recent value
    result = recency_weighted_mean([10.0, 20.0], [0.0, 1000.0], 1.0)
    assert result == pytest.approx(10.0, abs=1e-6)


def test_recency_weighted_mean_empty_raises():
    with pytest.raises(ValueError):
        recency_weighted_mean([], [], 30.0)


def test_staleness_weight_zero_age_is_one():
    assert staleness_weight(0.0, 30.0) == pytest.approx(1.0)


def test_staleness_weight_one_tau_is_exp_minus_one():
    assert staleness_weight(30.0, 30.0) == pytest.approx(math.exp(-1.0))


def test_effective_spread_no_trades_is_fallback():
    assert effective_spread(None, 2.0, 0.0) == pytest.approx(2.0)


def test_effective_spread_blends_by_staleness():
    # w=0.5: 0.5*10 + 0.5*2 = 6
    assert effective_spread(10.0, 2.0, 0.5) == pytest.approx(6.0)


def test_platform_rates_apply_asymmetric_spreads():
    rates = platform_rates(100.0, 3.0, 2.0)
    assert rates["buy"] == pytest.approx(103.0)
    assert rates["sell"] == pytest.approx(98.0)


def test_spot_on_or_before_uses_nearest_prior():
    spot = pd.Series({"2026-01-01": 10.0, "2026-01-03": 12.0})
    assert spot_on_or_before(spot, "2026-01-02") == pytest.approx(10.0)
    assert spot_on_or_before(spot, "2026-01-03") == pytest.approx(12.0)
    assert spot_on_or_before(spot, "2025-12-31") is None
