"""Risk-desk overlay: layer position-aware policy over the directional signal.

Asymmetric Agency (spec docs/superpowers/specs/2026-06-26-position-aware-signals-design.md):
analytics.signals owns ENTRIES and is never modified here. This module's single
pure function (Rule 2 — no I/O, no Streamlit, no global state) lets the position
act as a risk desk on top. It reserves a REDUCE_ONLY right to INITIATE a SELL for
stop-loss / take-profit, and may VETO an impossible or over-capacity call toward
HOLD. It never invents or adds a BUY.

Keeping signals.py purely directional means a backtest can always separate
"did my entry math fire?" from "did my risk policy interrupt it?".
"""


def apply_position_policy(
    signal_result: dict,
    *,
    holding_grams: float,
    cost_basis: float,
    current_sell_rate: float,
    stop_loss_pct: float,
    take_profit_pct: float,
    max_position_grams: float,
) -> dict:
    """Overlay the position risk desk on a directional signal; return a new dict.

    `signal_result` (output of generate_trade_signal) is NOT mutated. The
    directional verdict is preserved under 'directional_recommendation';
    'final_recommendation' is overwritten with the position-adjusted call. Adds
    'position_action' (None | EMERGENCY_LIQUIDATION | TAKE_PROFIT | AT_CAP |
    NOTHING_TO_LIQUIDATE) and 'pnl_pct' (signed %, or None when flat / cost<=0).
    """
    directional_final = signal_result["final_recommendation"]

    # 0. Computation gate (NOT an early return): pnl_pct is computable only with a
    #    real long position AND a positive cost basis. cost_basis <= 0 (e.g. a bad
    #    manual ledger entry) must never reach the divide, or an inverted % off a
    #    negative base could fire a phantom liquidation.
    pnl_pct = None
    if holding_grams > 0 and cost_basis > 0:
        pnl_pct = (current_sell_rate - cost_basis) / cost_basis * 100.0
    has_pnl = pnl_pct is not None

    # Ladder — first match wins.
    if has_pnl and pnl_pct <= -stop_loss_pct:
        final, action = "SELL", "EMERGENCY_LIQUIDATION"          # 1. hard floor
        reason = (f"PnL {pnl_pct:+.1f}% <= -{stop_loss_pct:g}% -> "
                  "emergency liquidation (capital protection)")
    elif has_pnl and pnl_pct >= take_profit_pct and directional_final != "BUY":
        final, action = "SELL", "TAKE_PROFIT"                    # 3. deferential ceiling
        reason = (f"PnL {pnl_pct:+.1f}% >= +{take_profit_pct:g}% with no "
                  "confirmed BUY -> take profit")
    elif directional_final == "BUY" and holding_grams >= max_position_grams:
        final, action = "HOLD", "AT_CAP"                         # 4. capacity veto
        reason = (f"Holdings {holding_grams:g} g >= cap {max_position_grams:g} g "
                  "-> BUY declined (at position cap)")
    elif directional_final == "SELL" and holding_grams <= 0:
        final, action, reason = "HOLD", "NOTHING_TO_LIQUIDATE", "No holdings to liquidate -> SELL suppressed to HOLD"           # 5. impossible-sell veto
    else:
        final, action, reason = directional_final, None, None    # 6. passthrough

    result = dict(signal_result)  # shallow copy of the mapping
    # NEW list — never .append() onto the shared (mutable) reasons list, or we
    # would silently mutate the brain's original dict and destroy the audit trail.
    result["reasons"] = signal_result.get("reasons", []) + ([reason] if reason else [])
    result["directional_recommendation"] = directional_final
    result["final_recommendation"] = final
    result["position_action"] = action
    result["pnl_pct"] = pnl_pct
    return result
