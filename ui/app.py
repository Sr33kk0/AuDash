"""AuDash — Streamlit entry point (Phase 5).

Top chrome + nav, then the dashboard (verdict hero, consensus, instrument
readout, the "why" ledger, the GSR assay balance, and the analytical charts),
or the trade / settings surfaces. Read side comes from ui.data_access; every
value/colour decision is a pure presenter helper; the look is the approved
Direction A "Assayer's Terminal" design.
"""

import html
import sqlite3

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
    <div class="audash-duo">
      <div class="audash-panel">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
          <span class="audash-eyebrow">{eyebrow}</span>{stale}
        </div>
        <div style="display:flex;align-items:flex-end;gap:18px;">
          <div class="audash-verdict-word" role="heading" aria-level="1" style="color:{view['color']};">{view['word']}</div>{metal}
        </div>
        <p class="audash-verdict-reason" style="margin:18px 0 0;">{reason}</p>
      </div>
      <div class="audash-panel" style="display:flex;flex-direction:column;">
        <div class="audash-eyebrow" role="heading" aria-level="2" style="margin-bottom:18px;">Consensus</div>
        <div style="display:flex;align-items:baseline;gap:8px;">
          <span class="audash-num" style="font-family:{t['f_data']};font-weight:600;font-size:46px;color:{t['text']};">{view['net_signed']}</span>
          <span style="font-family:{t['f_data']};font-size:14px;color:{t['muted']};">net votes</span>
        </div>
        <div style="font-family:{t['f_data']};font-size:13px;color:{t['sub']};margin-top:2px;">threshold ±{view['threshold']} → quant <span style="color:{view['quant_color']};">{view['quant_bias']}</span></div>
        <div style="height:1px;background:{t['line']};margin:18px 0;"></div>
        <div class="audash-eyebrow" role="heading" aria-level="3" style="margin-bottom:8px;">Sentiment gate</div>
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:8px;">
          <span aria-hidden="true" style="width:9px;height:9px;border-radius:50%;background:{view['gate_color']};"></span>
          <span style="font-family:{t['f_ui']};font-size:14px;font-weight:500;color:{t['text']};">{view['gate_label']}</span>
        </div>
        <p style="margin:0;font-family:{t['f_data']};font-size:12.5px;line-height:1.5;color:{t['sub']};">{detail}</p>
      </div>
    </div>"""


def _metric_grid_html(cells: list[dict]) -> str:
    items = ""
    for i, c in enumerate(cells):
        items += (
            f'<div class="audash-cell" style="--i:{i};background:{c["tint"]};'
            f'border-top:2px solid {c["edge"]};">'
            f'<dt class="audash-cell-label">{c["label"]}</dt>'
            f'<dd class="audash-cell-dd">'
            f'<span class="audash-num audash-cell-value" style="color:{c["color"]};">{c["value"]}</span>'
            f'<span class="audash-cell-unit">{c["unit"]}</span></dd></div>'
        )
    return (
        '<div style="margin-bottom:20px;">'
        '<div class="audash-eyebrow" role="heading" aria-level="2" style="margin-bottom:10px;">'
        'Instrument Readout · MYR · Asia/Kuala_Lumpur</div>'
        '<dl class="audash-readout">'
        f'{items}</dl></div>'
    )


def _breakdown_gsr_html(rows: list[dict], view: dict, gsr_band: dict,
                        pos: dict, svg: str) -> str:
    t = THEME
    row_html = ""
    for s in rows:
        row_html += (
            f'<div role="row" style="display:grid;grid-template-columns:1fr auto auto;'
            f'align-items:center;gap:14px;padding:11px 0;border-bottom:1px solid {t["line"]};">'
            f'<div role="rowheader"><div style="font-family:{t["f_ui"]};font-size:14px;font-weight:500;color:{t["text"]};">{s["label"]}</div>'
            f'<div style="font-family:{t["f_data"]};font-size:12px;color:{t["muted"]};">{s["detail"]}</div></div>'
            f'<span role="cell" aria-label="reading {s["value"]}" class="audash-num" style="font-family:{t["f_data"]};font-size:13px;color:{t["sub"]};">{s["value"]}</span>'
            f'<span role="cell" aria-label="vote {s["vote_text"]}" class="audash-num audash-vote" style="min-width:38px;text-align:center;'
            f'color:{s["vote_color"]};border:1px solid {s["vote_color"]};">{s["vote_text"]}</span></div>'
        )
    label_color = presenter.gsr_label_color(pos["side"], t)
    return f"""
    <div class="audash-duo">
      <div class="audash-panel">
        <div class="audash-eyebrow" role="heading" aria-level="2" style="margin-bottom:16px;">Why · ledger of reasons</div>
        <div role="table" aria-label="Signal ledger — each row gives a signal, its reading, and its vote">
        {row_html}
        <div role="row" style="display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:14px;padding:13px 0 4px;border-bottom:1px solid {t['line']};">
          <div role="rowheader" style="font-family:{t['f_ui']};font-size:14px;font-weight:600;color:{t['text']};">Net quant bias</div>
          <span role="cell" class="audash-num" style="font-family:{t['f_data']};font-size:13px;color:{t['muted']};">{view['net_signed']} vs ±{view['threshold']}</span>
          <span role="cell" class="audash-num" style="min-width:38px;text-align:center;font-family:{t['f_data']};font-weight:600;color:{view['quant_color']};">{view['quant_bias']}</span>
        </div>
        <div role="row" style="display:flex;align-items:center;justify-content:space-between;gap:14px;padding-top:13px;">
          <div role="rowheader" style="font-family:{t['f_ui']};font-size:14px;font-weight:600;color:{t['text']};">Sentiment gate → final</div>
          <span role="cell" style="font-family:{t['f_display']};font-weight:700;font-size:22px;color:{view['color']};">{view['word']}</span>
        </div>
        </div>
      </div>
      <div class="audash-panel" style="display:flex;flex-direction:column;">
        <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:6px;">
          <span class="audash-eyebrow" role="heading" aria-level="2">Gold / Silver Ratio</span>
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
    st.markdown('<div class="audash-eyebrow" role="heading" aria-level="2" style="margin:6px 0 8px;">'
                'Gold spot · Bollinger channel · trade marks</div>',
                unsafe_allow_html=True)
    if chart["dates"]:
        price_fig = charts.build_price_figure(
            chart["dates"], chart["price"], chart["bands"], chart["markers"], THEME)
        st.plotly_chart(price_fig, use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('<div class="audash-eyebrow" role="heading" aria-level="3" style="margin:6px 0 8px;">'
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
        f'<div role="banner" style="display:flex;align-items:baseline;gap:10px;">'
        f'<span style="font-family:{THEME["f_display"]};font-weight:700;font-size:24px;'
        f'letter-spacing:0.04em;color:{THEME["text"]};">AuDash</span>'
        f'<span aria-hidden="true" class="audash-num" style="font-family:{THEME["f_data"]};font-size:11px;'
        f'letter-spacing:0.18em;color:{THEME["accent"]};border:1px solid {THEME["line"]};'
        f'padding:2px 6px;border-radius:2px;">999.9</span></div>',
        unsafe_allow_html=True,
    )
    return st.radio("Navigation", ["Dashboard", "New Trade", "Settings"],
                    horizontal=True, key="nav", label_visibility="collapsed")


# --- Capital-protection fallback (read side unavailable) ---------------------

def _is_db_locked(exc: BaseException) -> bool:
    """True for SQLite write-contention — the worker holding the database
    mid-write — as opposed to a genuine fault. Drives the reassuring copy."""
    return isinstance(exc, sqlite3.OperationalError) and (
        "locked" in str(exc).lower() or "busy" in str(exc).lower())


def _unavailable_panel_html(locked: bool, detail: str) -> str:
    """The 'no reading' panel, in the capital-protection voice.

    Mirrors the verdict hero (eyebrow · serif word · reason) but renders a
    forced, visible HOLD in neutral silver — the instrument declining to judge
    on data it can't trust (Rule 3 / Design Principle 4). Never an alarm, never
    a raw traceback. Read survives without colour: the word, the NO READING
    chip, and the pause glyph each carry the state.
    """
    t = THEME
    hold = t["hold"]
    if locked:
        eyebrow = "Capital protection · instrument holding"
        reason = (
            "The background worker is committing a fresh reading, so the "
            "database is briefly locked. AuDash is holding rather than show a "
            "half-written number — your capital is never judged on partial "
            "data. The reading clears on its own once the write completes.")
        note = "Database locked · worker mid-write"
    else:
        eyebrow = "Capital protection · no reading"
        reason = (
            "AuDash can't reach its data store, so it is declining to show a "
            "verdict rather than guess — no trade should be made on an absent "
            "reading. Confirm the worker and its data volume are running, then "
            "retake the reading below.")
        note = "Data store unreachable"
    note_html = html.escape(f"{note} · {detail}" if detail else note)
    pause = (
        '<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true" '
        'style="flex:none;">'
        f'<rect x="6" y="5" width="3.4" height="12" rx="1" fill="{hold}"></rect>'
        f'<rect x="12.6" y="5" width="3.4" height="12" rx="1" fill="{hold}"></rect>'
        '</svg>')
    return (
        f'<div class="audash-panel audash-hold-panel" role="status" aria-live="polite" '
        f'style="margin-bottom:20px;border-color:{hold}40;">'
        f'<span class="audash-eyebrow">{eyebrow}</span>'
        f'<div style="display:flex;align-items:center;gap:14px;margin-top:10px;">'
        f'{pause}'
        f'<span style="font-family:{t["f_display"]};font-weight:700;'
        f'font-size:64px;line-height:0.9;letter-spacing:0.01em;color:{hold};">'
        f'HOLD</span>'
        f'<span class="audash-num" style="font-family:{t["f_data"]};'
        f'font-size:10px;font-weight:600;letter-spacing:0.16em;color:{hold};'
        f'border:1px solid {hold};padding:3px 8px;border-radius:2px;">'
        f'NO READING</span></div>'
        f'<p class="audash-verdict-reason" style="margin:16px 0 0;">{reason}</p>'
        f'<div class="audash-num" style="font-family:{t["f_data"]};'
        f'font-size:11.5px;color:{t["muted"]};margin-top:14px;'
        f'letter-spacing:0.02em;">{note_html}</div></div>'
    )


def render_unavailable(exc: Exception) -> None:
    """Stand in for any screen when the read side can't be assembled: the
    on-brand HOLD panel plus a calm retry (a rerun re-attempts the read)."""
    locked = _is_db_locked(exc)
    detail = "" if locked else type(exc).__name__
    st.markdown(_unavailable_panel_html(locked, detail), unsafe_allow_html=True)
    st.button("↻ Retake the reading", key="retry_read", type="primary")


def main() -> None:
    section = render_chrome()
    try:
        with get_db_connection() as conn:
            seed_default_settings(conn)
            model = data_access.load_dashboard_model(conn)
    except Exception as exc:  # noqa: BLE001 — any read-side fault degrades to a calm HOLD, never a traceback
        render_unavailable(exc)
        return

    if section == "Dashboard":
        render_dashboard(model)
    elif section == "New Trade":
        forms.render_ledger_input_form(model)
    else:
        forms.render_settings_panel(model)


main()
