"""AuDash — Streamlit entry point (Phase 5).

Top chrome + nav, then the dashboard (verdict hero, consensus, instrument
readout, the "why" ledger, the GSR assay balance, and the analytical charts),
or the trade / settings surfaces. Read side comes from ui.data_access; every
value/colour decision is a pure presenter helper; the look is the approved
Direction A "Assayer's Terminal" design.
"""

import streamlit as st

from database.connection import get_db_connection, seed_default_settings
from ui import charts, data_access, forms, presenter
from ui.theme import IDENTITY_CSS, THEME
from utils.timeutil import to_local

st.set_page_config(page_title="AuDash", page_icon="🜚", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(IDENTITY_CSS, unsafe_allow_html=True)


# --- HTML builders (read-only display surfaces) ------------------------------

def _eyebrow(model: dict) -> str:
    tz = model["settings"]["TIMEZONE"]
    local = to_local(model["now"], tz)
    age = model["sentiment_age"]
    max_age = float(model["settings"]["sentiment_max_age_days"])
    if age is None:
        freshness = "no snapshot"
    elif age <= max_age:
        freshness = "live"
    else:
        freshness = f"snapshot {age:.1f} d old"
    return f"{local:%d %b %Y · %H:%M} · {freshness}"


def _verdict_consensus_html(view: dict, reason: str, detail: str, eyebrow: str) -> str:
    t = THEME
    stale = '<span class="audash-stale">STALE</span>' if view["stale"] else ""
    metal = (f'<span class="audash-verdict-metal">{view["metal_word"]}</span>'
             if view["metal_word"] else "")
    return f"""
    <div style="display:grid;grid-template-columns:1.55fr 1fr;gap:20px;margin-bottom:20px;">
      <div class="audash-panel">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
          <span class="audash-eyebrow">{eyebrow}</span>{stale}
        </div>
        <div style="display:flex;align-items:flex-end;gap:18px;">
          <div class="audash-verdict-word" style="color:{view['color']};">{view['word']}</div>{metal}
        </div>
        <p class="audash-verdict-reason" style="margin:18px 0 0;">{reason}</p>
      </div>
      <div class="audash-panel" style="display:flex;flex-direction:column;">
        <div class="audash-eyebrow" style="margin-bottom:18px;">Consensus</div>
        <div style="display:flex;align-items:baseline;gap:8px;">
          <span class="audash-num" style="font-family:{t['f_data']};font-weight:600;font-size:46px;color:{t['text']};">{view['net_signed']}</span>
          <span style="font-family:{t['f_data']};font-size:14px;color:{t['muted']};">net votes</span>
        </div>
        <div style="font-family:{t['f_data']};font-size:13px;color:{t['sub']};margin-top:2px;">threshold ±{view['threshold']} → quant <span style="color:{view['quant_color']};">{view['quant_bias']}</span></div>
        <div style="height:1px;background:{t['line']};margin:18px 0;"></div>
        <div class="audash-eyebrow" style="margin-bottom:8px;">Sentiment gate</div>
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:8px;">
          <span style="width:9px;height:9px;border-radius:50%;background:{view['gate_color']};"></span>
          <span style="font-family:{t['f_ui']};font-size:14px;font-weight:500;color:{t['text']};">{view['gate_label']}</span>
        </div>
        <p style="margin:0;font-family:{t['f_data']};font-size:12.5px;line-height:1.5;color:{t['sub']};">{detail}</p>
      </div>
    </div>"""


def _metric_grid_html(cells: list[dict]) -> str:
    items = ""
    for c in cells:
        items += (
            f'<div class="audash-cell" style="background:{c["tint"]};'
            f'border-top:2px solid {c["edge"]};">'
            f'<div class="audash-cell-label">{c["label"]}</div>'
            f'<div style="display:flex;align-items:baseline;gap:5px;">'
            f'<span class="audash-num audash-cell-value" style="color:{c["color"]};">{c["value"]}</span>'
            f'<span class="audash-cell-unit">{c["unit"]}</span></div></div>'
        )
    return (
        '<div style="margin-bottom:20px;">'
        '<div class="audash-eyebrow" style="margin-bottom:10px;">'
        'Instrument Readout · MYR · Asia/Kuala_Lumpur</div>'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">'
        f'{items}</div></div>'
    )


def _breakdown_gsr_html(rows: list[dict], view: dict, gsr_band: dict,
                        pos: dict, svg: str) -> str:
    t = THEME
    row_html = ""
    for s in rows:
        row_html += (
            f'<div style="display:grid;grid-template-columns:1fr auto auto;'
            f'align-items:center;gap:14px;padding:11px 0;border-bottom:1px solid {t["line"]};">'
            f'<div><div style="font-family:{t["f_ui"]};font-size:14px;font-weight:500;color:{t["text"]};">{s["label"]}</div>'
            f'<div style="font-family:{t["f_data"]};font-size:12px;color:{t["muted"]};">{s["detail"]}</div></div>'
            f'<span class="audash-num" style="font-family:{t["f_data"]};font-size:13px;color:{t["sub"]};">{s["value"]}</span>'
            f'<span class="audash-num audash-vote" style="min-width:38px;text-align:center;'
            f'color:{s["vote_color"]};border:1px solid {s["vote_color"]};">{s["vote_text"]}</span></div>'
        )
    label_color = presenter.gsr_label_color(pos["side"], t)
    return f"""
    <div style="display:grid;grid-template-columns:1.45fr 1fr;gap:20px;margin-bottom:20px;">
      <div class="audash-panel">
        <div class="audash-eyebrow" style="margin-bottom:16px;">Why · ledger of reasons</div>
        {row_html}
        <div style="display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:14px;padding:13px 0 4px;border-bottom:1px solid {t['line']};">
          <div style="font-family:{t['f_ui']};font-size:14px;font-weight:600;color:{t['text']};">Net quant bias</div>
          <span class="audash-num" style="font-family:{t['f_data']};font-size:13px;color:{t['muted']};">{view['net_signed']} vs ±{view['threshold']}</span>
          <span class="audash-num" style="min-width:38px;text-align:center;font-family:{t['f_data']};font-weight:600;color:{view['quant_color']};">{view['quant_bias']}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:14px;padding-top:13px;">
          <div style="font-family:{t['f_ui']};font-size:14px;font-weight:600;color:{t['text']};">Sentiment gate → final</div>
          <span style="font-family:{t['f_display']};font-weight:700;font-size:22px;color:{view['color']};">{view['word']}</span>
        </div>
      </div>
      <div class="audash-panel" style="display:flex;flex-direction:column;">
        <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:6px;">
          <span class="audash-eyebrow">Gold / Silver Ratio</span>
          <span class="audash-num" style="font-family:{t['f_data']};font-weight:600;font-size:20px;color:{t['text']};">{presenter.fmt(gsr_band['value'], 1)}</span>
        </div>
        <div style="font-family:{t['f_ui']};font-size:12px;color:{label_color};margin-bottom:8px;">{pos['label']}</div>
        <div style="flex:1;display:flex;align-items:center;justify-content:center;min-height:170px;">{svg}</div>
        <div style="display:flex;justify-content:space-between;font-family:{t['f_data']};font-size:11px;color:{t['muted']};">
          <span>lower {presenter.fmt(gsr_band['lower'], 1)}</span><span>band</span><span>upper {presenter.fmt(gsr_band['upper'], 1)}</span>
        </div>
      </div>
    </div>"""


# --- screens -----------------------------------------------------------------

def render_dashboard(model: dict) -> None:
    sig = model["signal_result"]
    view = presenter.verdict_view(sig, model["threshold"], THEME)
    reason = presenter.verdict_reason(sig)
    detail = presenter.gate_detail(sig, model["sentiment_age"],
                                   float(model["settings"]["sentiment_max_age_days"]),
                                   model["threshold"])
    st.markdown(_verdict_consensus_html(view, reason, detail, _eyebrow(model)),
                unsafe_allow_html=True)

    cells = presenter.build_metric_cells(model["market"], THEME)
    st.markdown(_metric_grid_html(cells), unsafe_allow_html=True)

    rows = presenter.build_signal_rows(sig, model["signal_inputs"], THEME)
    band = model["gsr_band"]
    pos = presenter.gsr_position(band["value"], band["lower"], band["upper"])
    svg = charts.build_gsr_balance_svg(pos["degrees"], THEME)
    st.markdown(_breakdown_gsr_html(rows, view, band, pos, svg),
                unsafe_allow_html=True)

    chart = model["chart"]
    st.markdown('<div class="audash-eyebrow" style="margin:6px 0 8px;">'
                'Gold spot · Bollinger channel · trade marks</div>',
                unsafe_allow_html=True)
    if chart["dates"]:
        price_fig = charts.build_price_figure(
            chart["dates"], chart["price"], chart["bands"], chart["markers"], THEME)
        st.plotly_chart(price_fig, use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('<div class="audash-eyebrow" style="margin:6px 0 8px;">'
                    'RSI · 14</div>', unsafe_allow_html=True)
        rsi_fig = charts.build_rsi_figure(
            chart["dates"], chart["rsi"],
            float(model["settings"]["rsi_oversold"]),
            float(model["settings"]["rsi_overbought"]), THEME)
        st.plotly_chart(rsi_fig, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.markdown(f'<p style="font-family:{THEME["f_body"]};color:{THEME["muted"]};">'
                    'No price history yet — the worker will populate spot prices '
                    'on its next cycle.</p>', unsafe_allow_html=True)


def render_chrome() -> str:
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:10px;">'
        f'<span style="font-family:{THEME["f_display"]};font-weight:700;font-size:24px;'
        f'letter-spacing:0.04em;color:{THEME["text"]};">AuDash</span>'
        f'<span class="audash-num" style="font-family:{THEME["f_data"]};font-size:11px;'
        f'letter-spacing:0.18em;color:{THEME["accent"]};border:1px solid {THEME["line"]};'
        f'padding:2px 6px;border-radius:2px;">999.9</span></div>',
        unsafe_allow_html=True,
    )
    return st.radio("Navigation", ["Dashboard", "New Trade", "Settings"],
                    horizontal=True, key="nav", label_visibility="collapsed")


def main() -> None:
    section = render_chrome()
    with get_db_connection() as conn:
        seed_default_settings(conn)
        model = data_access.load_dashboard_model(conn)

    if section == "Dashboard":
        render_dashboard(model)
    elif section == "New Trade":
        forms.render_ledger_input_form(model)
    else:
        forms.render_settings_panel(model)


main()
