"""Unit tests for the pure presentation helpers (ui/presenter.py).

These encode the display contract from spec §5.3 and the Claude Design file
(AuDash.dc.html): number formatting, verdict/vote color mapping, the sentiment
gate, the GSR balance geometry, cash<->mass derivation, and the view-models the
Streamlit layer renders. All functions are pure (no DB, no Streamlit).
"""

from datetime import datetime, timezone

import pytest

from ui import presenter
from ui.theme import THEME


# --- number formatting -------------------------------------------------------

def test_fmt_groups_thousands_and_fixes_decimals():
    assert presenter.fmt(1234.5) == "1,234.50"
    assert presenter.fmt(520.0) == "520.00"
    assert presenter.fmt(73.4, 1) == "73.4"


def test_signed_prefixes_plus_for_non_negative():
    assert presenter.signed(1.2, 1) == "+1.2"
    assert presenter.signed(0.0, 2) == "+0.00"
    assert presenter.signed(-3.4, 1) == "-3.4"


def test_signed_int_prefixes_plus_for_non_negative():
    assert presenter.signed_int(2) == "+2"
    assert presenter.signed_int(0) == "+0"
    assert presenter.signed_int(-1) == "-1"


# --- verdict / vote colors ---------------------------------------------------

def test_verdict_color_maps_recommendation_to_palette():
    assert presenter.verdict_color("BUY", THEME) == THEME["buy"]
    assert presenter.verdict_color("SELL", THEME) == THEME["sell"]
    assert presenter.verdict_color("HOLD", THEME) == THEME["hold"]


def test_vote_text_renders_signed_single_digit():
    assert presenter.vote_text(1) == "+1"
    assert presenter.vote_text(0) == "0"
    assert presenter.vote_text(-1) == "-1"


def test_vote_color_follows_sign():
    assert presenter.vote_color(1, THEME) == THEME["buy"]
    assert presenter.vote_color(-1, THEME) == THEME["sell"]
    assert presenter.vote_color(0, THEME) == THEME["muted"]


# --- sentiment gate ----------------------------------------------------------

def test_sentiment_gate_stale_takes_priority():
    sig = {"sentiment_stale": True, "quant_bias": "SELL", "final_recommendation": "HOLD"}
    assert presenter.sentiment_gate(sig) == "stale"


def test_sentiment_gate_vetoed_when_final_drops_to_hold():
    sig = {"sentiment_stale": False, "quant_bias": "SELL", "final_recommendation": "HOLD"}
    assert presenter.sentiment_gate(sig) == "vetoed"


def test_sentiment_gate_passed_when_final_matches_quant():
    sig = {"sentiment_stale": False, "quant_bias": "BUY", "final_recommendation": "BUY"}
    assert presenter.sentiment_gate(sig) == "passed"


def test_sentiment_gate_neutral_when_no_quant_trade():
    sig = {"sentiment_stale": False, "quant_bias": "HOLD", "final_recommendation": "HOLD"}
    assert presenter.sentiment_gate(sig) == "neutral"


def test_gate_label_and_color():
    assert presenter.gate_label("neutral") == "No quant trade"
    assert presenter.gate_color("passed", THEME) == THEME["buy"]
    assert presenter.gate_color("vetoed", THEME) == THEME["sell"]
    assert presenter.gate_color("stale", THEME) == THEME["sell"]
    assert presenter.gate_color("neutral", THEME) == THEME["hold"]


# --- GSR balance geometry ----------------------------------------------------

def test_gsr_position_gold_rich_above_band_tilts_and_clamps():
    pos = presenter.gsr_position(88.8, 78.0, 86.5)
    assert pos["side"] == "gold"
    assert "Gold-rich" in pos["label"]
    # frac > 1 -> clamped to 1 -> +11 degrees
    assert pos["degrees"] == pytest.approx(11.0)


def test_gsr_position_silver_rich_below_band_tilts_negative():
    pos = presenter.gsr_position(75.2, 78.0, 86.5)
    assert pos["side"] == "silver"
    assert "Silver-rich" in pos["label"]
    assert pos["degrees"] == pytest.approx(-11.0)


def test_gsr_position_within_band_is_balanced_and_level():
    pos = presenter.gsr_position(82.25, 78.0, 86.5)
    assert pos["side"] == "neutral"
    assert "Within band" in pos["label"]
    assert pos["degrees"] == pytest.approx(0.0)


# --- sentiment age -----------------------------------------------------------

def test_sentiment_age_days_none_when_no_snapshot():
    assert presenter.sentiment_age_days(None, datetime.now(timezone.utc)) is None


def test_sentiment_age_days_measures_utc_delta_in_fractional_days():
    snap = {"fetched_at": "2026-06-21T00:00:00+00:00"}
    now = datetime(2026, 6, 23, 0, 0, 0, tzinfo=timezone.utc)
    assert presenter.sentiment_age_days(snap, now) == pytest.approx(2.0)


# --- cash <-> mass derivation ------------------------------------------------

def test_resolve_trade_amounts_cash_mode_derives_mass():
    out = presenter.resolve_trade_amounts("cash", "5000", 520.0)
    assert out["fiat_total_myr"] == pytest.approx(5000.0)
    assert out["mass_grams"] == pytest.approx(9.615384, abs=1e-5)


def test_resolve_trade_amounts_mass_mode_derives_cash():
    out = presenter.resolve_trade_amounts("mass", "10", 520.0)
    assert out["mass_grams"] == pytest.approx(10.0)
    assert out["fiat_total_myr"] == pytest.approx(5200.0)


def test_resolve_trade_amounts_blank_input_is_zero():
    out = presenter.resolve_trade_amounts("cash", "", 520.0)
    assert out == {"mass_grams": 0.0, "fiat_total_myr": 0.0}


def test_resolve_trade_amounts_zero_rate_does_not_divide_by_zero():
    out = presenter.resolve_trade_amounts("cash", "5000", 0.0)
    assert out["mass_grams"] == 0.0


# --- view-models -------------------------------------------------------------

def _market():
    return {
        "gold_buy": 520.0, "gold_sell": 500.0,
        "silver_buy": 6.0, "silver_sell": 5.54,
        "buy_spread": 12.0, "sell_spread": 8.0,
        "holdings": 125.0, "cost_basis": 478.5,
        "pnl": 2687.5, "rsi": 73.4, "percent_b": 1.04, "sentiment": 1.2,
    }


def test_build_metric_cells_has_twelve_cells_in_order():
    cells = presenter.build_metric_cells(_market(), THEME)
    assert len(cells) == 12
    assert cells[0]["label"] == "Gold buy"
    assert cells[0]["color"] == THEME["gold"]


def test_build_metric_cells_colors_pnl_and_sentiment_by_sign():
    pos = presenter.build_metric_cells(_market(), THEME)
    pnl = next(c for c in pos if c["label"] == "Unrealized PnL")
    sent = next(c for c in pos if c["label"] == "Sentiment")
    assert pnl["color"] == THEME["buy"]
    assert sent["color"] == THEME["buy"]

    m = _market()
    m["pnl"] = -100.0
    m["sentiment"] = -2.0
    neg = presenter.build_metric_cells(m, THEME)
    assert next(c for c in neg if c["label"] == "Unrealized PnL")["color"] == THEME["sell"]
    assert next(c for c in neg if c["label"] == "Sentiment")["color"] == THEME["sell"]


def _signal_result():
    return {
        "rsi_vote": -1, "vol_vote": -1, "gsr_vote": -1, "net_votes": -3,
        "quant_bias": "SELL", "sentiment_score": 1.2, "sentiment_stale": False,
        "final_recommendation": "HOLD",
    }


def test_build_signal_rows_maps_votes_to_three_rows():
    inputs = {"rsi": 73.4, "percent_b": 1.04, "gsr": 88.8}
    rows = presenter.build_signal_rows(_signal_result(), inputs, THEME)
    assert [r["label"] for r in rows] == ["RSI (14)", "Volatility band (%B)", "Gold / Silver Ratio"]
    assert rows[0]["vote_text"] == "-1"
    assert rows[0]["vote_color"] == THEME["sell"]


def test_verdict_view_blanks_metal_word_on_hold_and_signs_net():
    view = presenter.verdict_view(_signal_result(), threshold=2, theme=THEME)
    assert view["word"] == "HOLD"
    assert view["metal_word"] == ""
    assert view["net_signed"] == "-3"
    assert view["threshold"] == 2
    assert view["stale"] is False


def test_verdict_view_sets_metal_word_when_trading():
    sig = _signal_result()
    sig["final_recommendation"] = "SELL"
    view = presenter.verdict_view(sig, threshold=2, theme=THEME)
    assert view["metal_word"] == "GOLD"
    assert view["word"] == "SELL"


# --- settings grouping -------------------------------------------------------

def test_verdict_reason_stale_protects_capital():
    sig = {"sentiment_stale": True, "quant_bias": "SELL", "final_recommendation": "HOLD"}
    reason = presenter.verdict_reason(sig).lower()
    assert "stale" in reason and "capital" in reason


def test_verdict_reason_vetoed_mentions_block():
    sig = {"sentiment_stale": False, "quant_bias": "SELL", "final_recommendation": "HOLD"}
    assert "block" in presenter.verdict_reason(sig).lower()


def test_verdict_reason_passed_is_clean_trade():
    sig = {"sentiment_stale": False, "quant_bias": "BUY", "final_recommendation": "BUY"}
    assert "clean buy" in presenter.verdict_reason(sig).lower()


def test_verdict_reason_neutral_is_mixed():
    sig = {"sentiment_stale": False, "quant_bias": "HOLD", "final_recommendation": "HOLD"}
    assert "mixed" in presenter.verdict_reason(sig).lower()


def test_gate_detail_stale_without_snapshot():
    sig = {"sentiment_stale": True, "quant_bias": "HOLD",
           "final_recommendation": "HOLD", "sentiment_score": None, "net_votes": 0}
    detail = presenter.gate_detail(sig, age=None, max_age=2.0, threshold=2)
    assert "no sentiment" in detail.lower()


def test_gate_detail_stale_reports_age_and_limit():
    sig = {"sentiment_stale": True, "quant_bias": "BUY",
           "final_recommendation": "HOLD", "sentiment_score": 0.5, "net_votes": 2}
    detail = presenter.gate_detail(sig, age=4.1, max_age=2.0, threshold=2)
    assert "4.1" in detail and "beyond" in detail.lower()


def test_gate_detail_passed_mentions_clears():
    sig = {"sentiment_stale": False, "quant_bias": "BUY",
           "final_recommendation": "BUY", "sentiment_score": 0.8, "net_votes": 2}
    detail = presenter.gate_detail(sig, age=0.6, max_age=2.0, threshold=2)
    assert "clear" in detail.lower()


def test_settings_groups_cover_keys_and_mask_api_keys():
    settings = {
        "rsi_period": "14", "rsi_oversold": "30", "rsi_overbought": "70",
        "vol_band_deviations": "2", "gsr_band_deviations": "2",
        "quant_vote_threshold": "2", "sentiment_max_age_days": "2",
        "default_buy_spread": "12.0", "default_sell_spread": "8.0",
        "spread_recency_alpha": "30", "spread_staleness_tau": "30",
        "BASE_CURRENCY": "MYR", "TIMEZONE": "Asia/Kuala_Lumpur",
        "GEMINI_API_KEY": "secret", "COMMODITY_API_KEY": "secret2",
    }
    groups = presenter.settings_groups(settings)
    titles = [g["title"] for g in groups]
    assert "Indicators" in titles
    all_fields = [f for g in groups for f in g["fields"]]
    by_key = {f["key"]: f for f in all_fields}
    assert by_key["rsi_period"]["value"] == "14"
    assert by_key["GEMINI_API_KEY"]["type"] == "password"
