from analytics.risk import apply_position_policy


def _directional(final="HOLD", quant_bias="HOLD", stale=False,
                 net_votes=0, reasons=None):
    """A minimal directional signal dict (isolates risk.py from the brain)."""
    return {
        "rsi_vote": 0, "vol_vote": 0, "gsr_vote": 0,
        "net_votes": net_votes, "quant_bias": quant_bias,
        "sentiment_score": 0.0, "sentiment_stale": stale,
        "final_recommendation": final,
        "reasons": list(reasons) if reasons else [],
    }


def _policy(directional, *, holding_grams=0.0, cost_basis=0.0,
            current_sell_rate=0.0, stop_loss_pct=5.0, take_profit_pct=10.0,
            max_position_grams=100.0):
    return apply_position_policy(
        directional, holding_grams=holding_grams, cost_basis=cost_basis,
        current_sell_rate=current_sell_rate, stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct, max_position_grams=max_position_grams)


# --- stop-loss: the unconditional hard floor --------------------------------

def test_stop_loss_fires_through_stale_sentiment():
    d = _directional(final="HOLD", quant_bias="BUY", stale=True)
    r = _policy(d, holding_grams=10.0, cost_basis=500.0, current_sell_rate=460.0)  # -8%
    assert r["final_recommendation"] == "SELL"
    assert r["position_action"] == "EMERGENCY_LIQUIDATION"


def test_stop_loss_fires_through_active_quant_buy():
    d = _directional(final="BUY", quant_bias="BUY", net_votes=3)
    r = _policy(d, holding_grams=10.0, cost_basis=500.0, current_sell_rate=470.0)  # -6%
    assert r["final_recommendation"] == "SELL"
    assert r["position_action"] == "EMERGENCY_LIQUIDATION"
    assert r["directional_recommendation"] == "BUY"


# --- take-profit: the deferential ceiling -----------------------------------

def test_take_profit_defers_to_confirmed_buy():
    d = _directional(final="BUY", quant_bias="BUY", net_votes=3)
    r = _policy(d, holding_grams=10.0, cost_basis=500.0, current_sell_rate=560.0)  # +12%
    assert r["final_recommendation"] == "BUY"      # winner runs
    assert r["position_action"] is None


def test_take_profit_banks_when_not_confirmed_buy():
    d = _directional(final="HOLD", quant_bias="HOLD")
    r = _policy(d, holding_grams=10.0, cost_basis=500.0, current_sell_rate=560.0)  # +12%
    assert r["final_recommendation"] == "SELL"
    assert r["position_action"] == "TAKE_PROFIT"


def test_stale_feed_winner_is_banked():
    d = _directional(final="HOLD", quant_bias="BUY", stale=True)  # stale -> forced HOLD
    r = _policy(d, holding_grams=10.0, cost_basis=500.0, current_sell_rate=560.0)  # +12%
    assert r["final_recommendation"] == "SELL"
    assert r["position_action"] == "TAKE_PROFIT"


# --- capacity veto ----------------------------------------------------------

def test_buy_capped_at_max_position():
    d = _directional(final="BUY", quant_bias="BUY", net_votes=3)
    r = _policy(d, holding_grams=100.0, cost_basis=500.0, current_sell_rate=505.0,
                max_position_grams=100.0)  # +1% -> no SL/TP
    assert r["final_recommendation"] == "HOLD"
    assert r["position_action"] == "AT_CAP"


def test_buy_allowed_below_cap():
    d = _directional(final="BUY", quant_bias="BUY", net_votes=3)
    r = _policy(d, holding_grams=40.0, cost_basis=500.0, current_sell_rate=505.0,
                max_position_grams=100.0)
    assert r["final_recommendation"] == "BUY"
    assert r["position_action"] is None


# --- impossible sell --------------------------------------------------------

def test_sell_with_no_holdings_suppressed():
    d = _directional(final="SELL", quant_bias="SELL", net_votes=-3)
    r = _policy(d, holding_grams=0.0, cost_basis=0.0, current_sell_rate=500.0)
    assert r["final_recommendation"] == "HOLD"
    assert r["position_action"] == "NOTHING_TO_LIQUIDATE"


# --- flat identity ----------------------------------------------------------

def test_flat_position_passes_through_unchanged():
    d = _directional(final="BUY", quant_bias="BUY", net_votes=3)
    r = _policy(d, holding_grams=0.0, cost_basis=0.0, current_sell_rate=500.0)
    assert r["final_recommendation"] == "BUY"
    assert r["position_action"] is None
    assert r["directional_recommendation"] == "BUY"
    assert r["pnl_pct"] is None


# --- cost_basis <= 0 guard (no phantom liquidation) -------------------------

def test_cost_basis_zero_no_trigger():
    d = _directional(final="HOLD")
    r = _policy(d, holding_grams=10.0, cost_basis=0.0, current_sell_rate=500.0)
    assert r["pnl_pct"] is None
    assert r["position_action"] is None


def test_negative_cost_basis_no_phantom_liquidation():
    d = _directional(final="HOLD")
    r = _policy(d, holding_grams=10.0, cost_basis=-100.0, current_sell_rate=500.0)
    assert r["pnl_pct"] is None
    assert r["position_action"] is None


# --- audit isolation (Trap A) -----------------------------------------------

def test_input_reasons_not_mutated():
    d = _directional(final="HOLD", reasons=["original reason"])
    original = d["reasons"]
    r = _policy(d, holding_grams=10.0, cost_basis=500.0, current_sell_rate=460.0)  # SL
    assert original == ["original reason"]      # input list content untouched
    assert d["reasons"] is original             # same object, unchanged
    assert r["reasons"] is not original         # output is a NEW list
    assert len(r["reasons"]) == 2               # original + 1 risk line


# --- precedence -------------------------------------------------------------

def test_stop_loss_beats_cap():
    d = _directional(final="BUY", quant_bias="BUY", net_votes=3)
    r = _policy(d, holding_grams=100.0, cost_basis=500.0, current_sell_rate=460.0,
                max_position_grams=100.0)  # -8% AND at cap
    assert r["position_action"] == "EMERGENCY_LIQUIDATION"
