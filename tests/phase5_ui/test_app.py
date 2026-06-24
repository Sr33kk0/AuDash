"""Headless AppTest coverage for the dashboard screen + navigation.

Asserts the app renders the verdict, the instrument readout, and the breakdown
without raising — structure, not pixels (design brief §4). A temp DATA_DIR DB
is seeded so load_dashboard_model has real data.
"""

from datetime import timedelta

from streamlit.testing.v1 import AppTest

from database.connection import (
    get_db_connection, write_sentiment_snapshot, write_spot_prices,
)
from utils.timeutil import now_utc

APP = "ui/app.py"


def _seed(db_file) -> None:
    with get_db_connection(str(db_file)) as conn:
        base = now_utc().date()
        for i in range(30):
            d = (base - timedelta(days=29 - i)).isoformat()
            write_spot_prices(conn, d, 16000.0 - i * 60.0, 190.0 - i * 0.2)
        write_sentiment_snapshot(conn, base.isoformat(), 1.5, "Risk-on",
                                 "Fresh positive read", ["headline"])


def _run(tmp_path, monkeypatch) -> AppTest:
    _seed(tmp_path / "audash.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return AppTest.from_file(APP, default_timeout=60).run()


def test_dashboard_renders_without_exception(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    assert not at.exception


def test_dashboard_shows_verdict_and_metric_labels(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    blob = " ".join(m.value for m in at.markdown)
    assert any(word in blob for word in ("BUY", "SELL", "HOLD"))
    assert "Gold buy" in blob
    assert "Why · ledger of reasons" in blob


def _seed_stale(db_file) -> None:
    """Seed prices + a sentiment snapshot whose fetched_at is older than the
    default sentiment_max_age_days (2). Forces the gate to STALE -> HOLD, which
    yields an empty metal word (presenter.verdict_view)."""
    _seed(db_file)
    with get_db_connection(str(db_file)) as conn:
        stale_ts = (now_utc() - timedelta(days=5)).isoformat()
        conn.execute("UPDATE sentiment_snapshots SET fetched_at = ?;", (stale_ts,))


def test_stale_verdict_html_stays_one_block(tmp_path, monkeypatch):
    """A no-metal HOLD must not collapse the verdict's `{metal}` line into a
    blank line: Streamlit dedents the body, and a blank line mid-HTML closes
    the CommonMark HTML block, dumping the rest (incl. the verdict reason) as
    raw escaped text. Guard: the verdict body carries no interior blank line."""
    _seed_stale(tmp_path / "audash.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception

    # Discriminate on the reason text: the CSS <style> block also mentions
    # `audash-verdict-reason` (and carries blank lines between rule groups).
    verdict = next(m.value for m in at.markdown if "Sentiment is stale" in m.value)
    assert 'class="audash-verdict-reason"' in verdict
    interior = verdict.splitlines()[1:-1]  # edges are stripped by clean_text
    assert all(line.strip() for line in interior), \
        "blank line inside verdict HTML closes the block -> raw text leaks"


def test_nav_to_new_trade_reveals_form(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    at.radio[0].set_value("New Trade").run()
    assert not at.exception
    assert "Metal" in [r.label for r in at.radio]


def test_nav_to_settings_reveals_inputs(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    at.radio[0].set_value("Settings").run()
    assert not at.exception
    keys = [w.key for w in at.text_input]
    assert "set_rsi_period" in keys
