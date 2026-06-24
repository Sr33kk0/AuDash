"""Direction A "Assayer's Terminal" palette + identity CSS.

Pure configuration (no Streamlit/Plotly import) so presenter helpers can take
the palette as a plain dict and stay unit-testable. Hex tokens are ported
verbatim from the approved Claude Design file (AuDash.dc.html, theme "A").
"""

# Bi-metallic instrument-panel palette. Keys are snake_case mirrors of the
# design's camelCase theme object so the mapping is auditable 1:1.
THEME: dict[str, object] = {
    "is_dark": True,
    "bg": "#0E0D0B",
    "chrome": "rgba(14,13,11,0.86)",
    "panel": "#1A1815",
    "line": "#2E2A24",
    "text": "#EDE7D9",
    "sub": "#B8AF9F",
    "muted": "#8C857A",
    "accent": "#C8A24C",
    "accent_bright": "#E8C877",
    "gold": "#C8A24C",
    "gold_edge": "#C8A24C",
    "silver": "#AEB6BD",
    "silver_edge": "#AEB6BD",
    "buy": "#6FAE7E",
    "sell": "#C56A5C",
    "hold": "#AEB6BD",
    "gold_tint": "rgba(200,162,76,0.06)",
    "silver_tint": "rgba(174,182,189,0.06)",
    "neutral_tint": "#1A1815",
    "on_accent": "#0E0D0B",
    "f_display": "'Cormorant Garamond', Georgia, serif",
    "f_data": "'IBM Plex Mono', monospace",
    "f_ui": "'IBM Plex Sans', system-ui, sans-serif",
    "f_body": "'IBM Plex Sans', system-ui, sans-serif",
}

# Google Fonts + the identity layer injected once via st.markdown(unsafe...).
# Re-skins Streamlit's default chrome into the dark warm-charcoal instrument
# panel and supplies the verdict/metric/badge primitives the views compose.
IDENTITY_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,500&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {{ --focus: {THEME['accent']}; }}

.stApp {{ background: {THEME['bg']}; color: {THEME['text']}; font-family: {THEME['f_ui']}; }}
.block-container {{ max-width: 1240px; padding-top: 1.4rem; }}

.audash-num {{ font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}

:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}

/* Panels --------------------------------------------------------------- */
.audash-panel {{
    background: {THEME['panel']};
    border: 1px solid {THEME['line']};
    border-radius: 6px;
    padding: 24px;
}}
.audash-eyebrow {{
    font-family: {THEME['f_data']};
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: {THEME['muted']};
}}

/* Verdict hero --------------------------------------------------------- */
.audash-verdict-word {{
    font-family: {THEME['f_display']};
    font-weight: 700;
    font-size: 96px;
    line-height: 0.9;
    letter-spacing: 0.01em;
}}
.audash-verdict-metal {{
    font-family: {THEME['f_display']};
    font-size: 30px;
    font-weight: 500;
    color: {THEME['sub']};
}}
.audash-verdict-reason {{
    font-family: {THEME['f_body']};
    font-size: 16px;
    line-height: 1.55;
    color: {THEME['sub']};
    max-width: 46ch;
    text-wrap: pretty;
}}
.audash-stale {{
    font-family: {THEME['f_data']};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.16em;
    color: {THEME['sell']};
    border: 1px solid {THEME['sell']};
    padding: 2px 7px;
    border-radius: 2px;
}}

/* Metric grid ---------------------------------------------------------- */
.audash-cell {{
    border: 1px solid {THEME['line']};
    border-radius: 5px;
    padding: 15px 16px;
}}
.audash-cell-label {{
    font-family: {THEME['f_ui']};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: {THEME['muted']};
    margin-bottom: 9px;
}}
.audash-cell-value {{
    font-family: {THEME['f_data']};
    font-weight: 600;
    font-size: 25px;
    line-height: 1;
}}
.audash-cell-unit {{ font-family: {THEME['f_data']}; font-size: 11px; color: {THEME['muted']}; }}

/* Ledger / breakdown --------------------------------------------------- */
.audash-vote {{
    font-family: {THEME['f_data']};
    font-weight: 600;
    font-size: 14px;
    border-radius: 3px;
    padding: 3px 10px;
}}

/* Streamlit chrome tidy ------------------------------------------------ */
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp [data-testid="stToolbar"] {{ display: none; }}
</style>
"""
