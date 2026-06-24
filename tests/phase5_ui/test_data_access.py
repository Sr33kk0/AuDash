"""Integration tests for the DB -> dashboard view-model assembly.

Uses the real temp-file SQLite fixture (db_conn). Covers the new
fetch_transactions DAO and ui.data_access.load_dashboard_model, with emphasis
on the Rule 3 wiring: sentiment age -> generate_trade_signal -> forced HOLD.
"""

from datetime import timedelta

import pandas as pd

from database.connection import (
    log_transaction, write_sentiment_snapshot, write_spot_prices,
)
from ui import data_access
from utils.timeutil import now_utc


def _seed_spot(conn, days: int = 30, start_gold: float = 16000.0,
               start_silver: float = 190.0) -> list[str]:
    """Seed a descending gold series (drives RSI oversold) over `days` days."""
    dates = []
    base = now_utc().date()
    for i in range(days):
        d = (base - timedelta(days=days - 1 - i)).isoformat()
        dates.append(d)
        gold = start_gold - i * 60.0           # steady decline
        silver = start_silver - i * 0.2
        write_spot_prices(conn, d, gold, silver)
    return dates


def test_fetch_transactions_returns_dataframe_with_ledger_columns(db_conn):
    log_transaction(db_conn, "BUY", "GOLD", 500.0, 10.0, 5000.0)
    log_transaction(db_conn, "SELL", "GOLD", 510.0, 4.0, 2040.0)
    df = data_access.fetch_transactions(db_conn)
    assert len(df) == 2
    assert {"action_type", "timestamp", "execution_rate_myr",
            "mass_grams", "metal"} <= set(df.columns)


def test_fetch_transactions_filters_by_metal(db_conn):
    log_transaction(db_conn, "BUY", "GOLD", 500.0, 10.0, 5000.0)
    log_transaction(db_conn, "BUY", "SILVER", 6.0, 100.0, 600.0)
    gold = data_access.fetch_transactions(db_conn, metal="GOLD")
    assert len(gold) == 1
    assert gold.iloc[0]["metal"] == "GOLD"


def test_load_dashboard_model_populates_market_and_signal(db_conn):
    _seed_spot(db_conn)
    log_transaction(db_conn, "BUY", "GOLD", 500.0, 20.0, 10000.0)
    write_sentiment_snapshot(db_conn, now_utc().date().isoformat(),
                             1.5, "Risk-on", "Fresh positive read", ["h1"])

    model = data_access.load_dashboard_model(db_conn, now=now_utc())

    assert {"settings", "market", "signal_inputs", "signal_result",
            "gsr_band", "chart", "sentiment_age", "threshold"} <= set(model)
    assert isinstance(model["market"]["gold_buy"], float)
    assert model["market"]["gold_buy"] > 0
    assert model["signal_result"]["final_recommendation"] in {"BUY", "SELL", "HOLD"}
    assert len(model["chart"]["dates"]) == 30
    # fresh sentiment -> not stale
    assert model["signal_result"]["sentiment_stale"] is False


def test_load_dashboard_model_forces_hold_when_sentiment_stale(db_conn):
    _seed_spot(db_conn)
    write_sentiment_snapshot(db_conn, now_utc().date().isoformat(),
                             1.5, "Risk-on", "Old read", ["h1"])

    # Look at the model 5 days later: the snapshot is now beyond max age.
    model = data_access.load_dashboard_model(
        db_conn, now=now_utc() + timedelta(days=5))

    assert model["signal_result"]["sentiment_stale"] is True
    assert model["signal_result"]["final_recommendation"] == "HOLD"


def test_load_dashboard_model_empty_db_is_safe_hold(db_conn):
    model = data_access.load_dashboard_model(db_conn, now=now_utc())
    assert model["signal_result"]["final_recommendation"] == "HOLD"
    assert model["signal_result"]["sentiment_stale"] is True
    assert model["chart"]["dates"] == []
