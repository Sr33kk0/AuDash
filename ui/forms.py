"""Streamlit input surfaces: the trade ledger form and the settings panel.

These use real Streamlit widgets (so they're interactive and AppTest-driveable)
over the dark theme. All display formatting + the cash<->mass math comes from
the pure presenter; writes go through the Phase 1 DAO. The AI deps for
"Refresh sentiment now" are imported lazily so the dashboard never needs them.
"""

import os

import streamlit as st

from database.connection import get_db_connection, log_transaction, set_setting
from ui import presenter
from ui.theme import THEME


def _heading(eyebrow: str, title: str, blurb: str) -> None:
    st.markdown(
        f'<div class="audash-eyebrow">{eyebrow}</div>'
        f'<div style="font-family:{THEME["f_display"]};font-weight:600;'
        f'font-size:34px;color:{THEME["text"]};margin:2px 0 4px;">{title}</div>'
        f'<p style="font-family:{THEME["f_body"]};font-size:15px;'
        f'color:{THEME["sub"]};margin:0 0 22px;">{blurb}</p>',
        unsafe_allow_html=True,
    )


def _rate_for(market: dict, metal: str, action: str) -> float:
    """Current platform rate for the chosen metal + side (MYR/gram)."""
    return float(market[f"{metal.lower()}_{action.lower()}"])


def _trade_timestamp(trade_date) -> str:
    """UTC ISO for a date-granular trade. Noon UTC keeps date[:10] == the
    picked date, so the spread engine's spot-on-trade-date join can't drift
    across the UTC offset (Rule 1; guards the Phase 3 date-slice caveat)."""
    return f"{trade_date.isoformat()}T12:00:00+00:00"


def render_ledger_input_form(model: dict) -> None:
    """Pick metal/action/date + a cash<->mass toggle; write one ledger row."""
    market = model["market"]
    _heading("New Trade", "Log a transaction",
             "Recorded to the trade ledger. The derived value uses the live "
             "platform rate.")

    metal = st.radio("Metal", ["GOLD", "SILVER"], horizontal=True, key="trade_metal")
    action = st.radio("Action", ["BUY", "SELL"], horizontal=True, key="trade_action")
    trade_date = st.date_input("Date", key="trade_date")

    rate = _rate_for(market, metal, action)
    st.markdown(
        f'<div class="audash-eyebrow" style="margin-top:6px;">'
        f'Platform {action.lower()} rate</div>'
        f'<div class="audash-num" style="font-family:{THEME["f_data"]};'
        f'font-size:18px;color:{THEME["text"]};margin-bottom:10px;">'
        f'{presenter.fmt(rate)} <span class="audash-cell-unit">MYR/g</span></div>',
        unsafe_allow_html=True,
    )

    mode = st.radio("Enter by", ["cash", "mass"], horizontal=True, key="trade_mode",
                    format_func=lambda m: "Cash · MYR" if m == "cash" else "Mass · grams")
    primary = st.text_input(
        "Cash · MYR" if mode == "cash" else "Mass · grams",
        value="0", key="trade_primary")

    amounts = presenter.resolve_trade_amounts(mode, primary, rate)
    if mode == "cash":
        derived = f"{presenter.fmt(amounts['mass_grams'], 4)} g"
    else:
        derived = f"RM {presenter.fmt(amounts['fiat_total_myr'])}"
    st.markdown(
        f'<div class="audash-eyebrow">Derived <span style="color:{THEME["accent"]};">'
        f'live</span></div><div class="audash-num" style="font-family:'
        f'{THEME["f_data"]};font-size:18px;font-weight:600;color:{THEME["accent"]};'
        f'margin-bottom:18px;">{derived}</div>',
        unsafe_allow_html=True,
    )

    if st.button(f"Log {action} · {metal}", key="trade_submit", type="primary"):
        with get_db_connection() as conn:
            log_transaction(conn, action, metal, rate,
                            amounts["mass_grams"], amounts["fiat_total_myr"],
                            timestamp=_trade_timestamp(trade_date))
        st.success(f"Logged {action} · {metal} · {derived} → ledger")


def render_settings_panel(model: dict) -> None:
    """Edit every system_settings key; save, or re-run sentiment on demand."""
    settings = model["settings"]
    _heading("Settings", "System settings",
             "Runtime configuration stored in system_settings.")

    edited: dict[str, str] = {}
    for group in presenter.settings_groups(settings):
        st.markdown(
            f'<div class="audash-eyebrow" style="color:{THEME["accent"]};'
            f'margin:14px 0 6px;">{group["title"]}</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, field in enumerate(group["fields"]):
            with cols[i % 2]:
                kwargs = {"type": "password"} if field["type"] == "password" else {}
                edited[field["key"]] = st.text_input(
                    field["label"], value=str(field["value"]),
                    key=f"set_{field['key']}", **kwargs)

    save, refresh = st.columns([1, 1])
    with save:
        if st.button("Save settings", key="save_settings", type="primary"):
            with get_db_connection() as conn:
                for key, value in edited.items():
                    set_setting(conn, key, value)
            st.success("Settings saved to system_settings")
    with refresh:
        if st.button("↻ Refresh sentiment now", key="refresh_sentiment"):
            _refresh_sentiment(model, edited)


def _refresh_sentiment(model: dict, edited: dict) -> None:
    """Re-run the AI sentiment pipeline and write a fresh snapshot."""
    api_key = edited.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        st.warning("No Gemini API key configured — add one above, save, then retry.")
        return
    # Lazy import: keeps feedparser / google-generativeai off the dashboard path.
    from worker.sentiment_pipeline import execute_sentiment_pipeline

    market = model["market"]
    metrics = {"rsi": market["rsi"], "gsr": model["gsr_band"]["value"]}
    with st.spinner("Re-running sentiment pipeline…"):
        with get_db_connection() as conn:
            result = execute_sentiment_pipeline(
                conn, api_key=api_key,
                model_name=edited.get("GEMINI_MODEL", "gemini-2.0-flash"),
                market_metrics=metrics)
    if result.get("failed"):
        st.error("Sentiment refresh failed — prior snapshot kept (capital protection).")
    else:
        st.success("Sentiment pipeline re-run · fresh snapshot written.")
