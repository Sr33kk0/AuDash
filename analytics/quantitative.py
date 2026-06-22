"""Pure, stateless quantitative indicators over price series.

No I/O, no Streamlit, no global state (Rule 2): every function takes pandas
Series / primitives and returns values, so each is unit-testable in isolation.
Spot inputs are per troy ounce; the Gold/Silver Ratio is unit-invariant.
"""

import pandas as pd


def compute_gold_silver_ratio(gold: pd.Series, silver: pd.Series) -> pd.Series:
    """Return the elementwise Gold/Silver Ratio (gold_per_oz / silver_per_oz)."""
    return gold / silver
