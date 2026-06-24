"""Headless AppTest coverage for the form side-effects.

Drives the real widgets and asserts the DB write actually happened (the trade
ledger row, the persisted setting) and that "Refresh sentiment now" degrades
safely with no API key.
"""

from datetime import timedelta

from streamlit.testing.v1 import AppTest

from database.connection import (
    fetch_transactions, get_db_connection, get_setting, write_spot_prices,
)
from utils.timeutil import now_utc

APP = "ui/app.py"


def _seed(db_file) -> None:
    with get_db_connection(str(db_file)) as conn:
        base = now_utc().date()
        for i in range(30):
            d = (base - timedelta(days=29 - i)).isoformat()
            write_spot_prices(conn, d, 16000.0 - i * 60.0, 190.0 - i * 0.2)


def _run(tmp_path, monkeypatch) -> AppTest:
    _seed(tmp_path / "audash.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return AppTest.from_file(APP, default_timeout=60).run()


def _widget(widgets, key):
    return next(w for w in widgets if w.key == key)


def test_submitting_trade_form_writes_a_ledger_row(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    at.radio[0].set_value("New Trade").run()
    _widget(at.text_input, "trade_primary").set_value("5000").run()
    _widget(at.button, "trade_submit").click().run()

    assert not at.exception
    with get_db_connection(str(tmp_path / "audash.db")) as conn:
        df = fetch_transactions(conn)
    assert len(df) == 1
    assert df.iloc[0]["action_type"] == "BUY"
    assert df.iloc[0]["metal"] == "GOLD"


def test_saving_settings_persists_change(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    at.radio[0].set_value("Settings").run()
    _widget(at.text_input, "set_rsi_oversold").set_value("35").run()
    _widget(at.button, "save_settings").click().run()

    assert not at.exception
    with get_db_connection(str(tmp_path / "audash.db")) as conn:
        assert get_setting(conn, "rsi_oversold") == "35"


def test_refresh_sentiment_without_key_warns(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    at.radio[0].set_value("Settings").run()
    _widget(at.button, "refresh_sentiment").click().run()

    assert not at.exception
    assert any("Gemini API key" in w.value for w in at.warning)
