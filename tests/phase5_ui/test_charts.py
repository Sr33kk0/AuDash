"""Structure tests for the themed Plotly figures (ui/charts.py).

We assert the figure carries the right traces / guide lines / axes — not pixels
(per the design brief's testability note). Rendering fidelity is visual.
"""

import pandas as pd
import plotly.graph_objects as go

from ui import charts
from ui.theme import THEME


def _series():
    dates = [f"2026-06-{d:02d}" for d in range(1, 11)]
    price = [500.0 + i for i in range(10)]
    bands = pd.DataFrame({
        "middle": [None] * 4 + [503.0, 504.0, 505.0, 506.0, 507.0, 508.0],
        "upper": [None] * 4 + [510.0, 511.0, 512.0, 513.0, 514.0, 515.0],
        "lower": [None] * 4 + [496.0, 497.0, 498.0, 499.0, 500.0, 501.0],
    })
    return dates, price, bands


def test_build_price_figure_has_spot_band_and_trade_traces():
    dates, price, bands = _series()
    markers = [
        {"date": "2026-06-05", "side": "BUY", "price": 504.0},
        {"date": "2026-06-08", "side": "SELL", "price": 507.0},
    ]
    fig = charts.build_price_figure(dates, price, bands, markers, THEME)
    assert isinstance(fig, go.Figure)
    names = {t.name for t in fig.data}
    assert {"Spot", "Buy", "Sell"} <= names


def test_build_price_figure_spot_uses_accent_color():
    dates, price, bands = _series()
    fig = charts.build_price_figure(dates, price, bands, [], THEME)
    spot = next(t for t in fig.data if t.name == "Spot")
    assert spot.line.color == THEME["accent"]


def test_build_rsi_figure_has_rsi_trace_and_two_guide_lines():
    dates, _, _ = _series()
    rsi = [None] * 3 + [40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0]
    fig = charts.build_rsi_figure(dates, rsi, 30, 70, THEME)
    names = {t.name for t in fig.data}
    assert "RSI" in names
    assert len(fig.layout.shapes) == 2  # oversold + overbought guides


def test_build_rsi_figure_fixes_y_axis_to_0_100():
    dates, _, _ = _series()
    rsi = [None] * 3 + [40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0]
    fig = charts.build_rsi_figure(dates, rsi, 30, 70, THEME)
    assert tuple(fig.layout.yaxis.range) == (0, 100)


def test_gsr_balance_svg_is_svg_with_metal_labels():
    svg = charts.build_gsr_balance_svg(11.0, THEME)
    assert svg.lstrip().startswith("<svg")
    assert "AU" in svg and "AG" in svg
    assert THEME["gold"] in svg and THEME["silver"] in svg
