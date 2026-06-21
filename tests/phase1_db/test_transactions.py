import sqlite3

import pytest

from database.connection import log_transaction


def test_log_transaction_returns_uuid_and_persists(db_conn):
    tx_id = log_transaction(db_conn, "BUY", "GOLD", 380.5, 10.0, 3805.0)
    assert isinstance(tx_id, str) and len(tx_id) == 36
    row = db_conn.execute(
        "SELECT * FROM transactions WHERE id=?;", (tx_id,)
    ).fetchone()
    assert row["action_type"] == "BUY"
    assert row["metal"] == "GOLD"
    assert row["execution_rate_myr"] == 380.5
    assert row["mass_grams"] == 10.0
    assert row["fiat_total_myr"] == 3805.0
    assert row["timestamp"] is not None


def test_invalid_action_type_rejected(db_conn):
    with pytest.raises(sqlite3.IntegrityError):
        log_transaction(db_conn, "HOLD", "GOLD", 380.5, 10.0, 3805.0)


def test_invalid_metal_rejected(db_conn):
    with pytest.raises(sqlite3.IntegrityError):
        log_transaction(db_conn, "BUY", "PLATINUM", 380.5, 10.0, 3805.0)
