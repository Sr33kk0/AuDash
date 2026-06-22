"""Pure platform-spread engine: asymmetric, recency-weighted, staleness-decaying.

All spread values are absolute MYR-per-gram amounts. No I/O, no global state
(Rule 2). The spread reflects broker pricing behavior, so it uses the entire
trade history (recency-decayed) and never resets on liquidation.
"""

import math

import numpy as np
import pandas as pd

# Physical constant; mirrors worker.api_client.GRAMS_PER_TROY_OZ. Duplicated
# here to keep analytics free of any worker import (purity / no I/O coupling).
GRAMS_PER_TROY_OZ = 31.1034768


def per_gram(per_oz):
    """Convert a per-troy-ounce amount (scalar or Series) to per gram."""
    return per_oz / GRAMS_PER_TROY_OZ


def realized_spread(exec_rate: float, spot: float, side: str) -> float:
    """Per-trade realized spread vs spot (per gram). BUY markup / SELL haircut."""
    if side == "BUY":
        return exec_rate - spot
    if side == "SELL":
        return spot - exec_rate
    raise ValueError(f"side must be 'BUY' or 'SELL', got {side!r}")


def recency_weighted_mean(values, ages_days, alpha_days: float) -> float:
    """Exponentially recency-weighted mean: weight_i = exp(-age_i / alpha)."""
    v = np.asarray(values, dtype=float)
    a = np.asarray(ages_days, dtype=float)
    if v.size == 0:
        raise ValueError("recency_weighted_mean requires at least one value")
    weights = np.exp(-a / alpha_days)
    return float(np.sum(weights * v) / np.sum(weights))


def staleness_weight(latest_age_days: float, tau_days: float) -> float:
    """Decay weight for how stale the latest trade is: exp(-age / tau)."""
    return math.exp(-latest_age_days / tau_days)


def effective_spread(derived: float | None, fallback: float,
                     staleness_w: float) -> float:
    """Blend derived spread toward the configured fallback as trades go stale."""
    if derived is None:
        return fallback
    return staleness_w * derived + (1.0 - staleness_w) * fallback


def platform_rates(spot_today_per_gram: float, eff_buy_spread: float,
                   eff_sell_spread: float) -> dict:
    """Current platform buy/sell rates from spot plus asymmetric spreads."""
    return {
        "buy": spot_today_per_gram + eff_buy_spread,
        "sell": spot_today_per_gram - eff_sell_spread,
    }


def spot_on_or_before(spot_per_gram: pd.Series, date: str) -> float | None:
    """Spot at `date`, else the nearest prior date; None if none exists.

    Expects an ascending ISO 'YYYY-MM-DD' string index (lexicographic == chronological).
    """
    prior = spot_per_gram[spot_per_gram.index <= date]
    if prior.empty:
        return None
    return float(prior.iloc[-1])
