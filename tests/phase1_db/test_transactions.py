import sqlite3

import pytest

from database.connection import fetch_transactions, get_db_connection, log_transaction


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


def test_log_transaction_persists_reverses_id(db_conn):
    orig = log_transaction(db_conn, "BUY", "GOLD", 400.0, 2.0, 800.0)
    rev = log_transaction(db_conn, "SELL", "GOLD", 400.0, 2.0, 800.0,
                          reverses_id=orig)
    rev_row = db_conn.execute(
        "SELECT reverses_id FROM transactions WHERE id=?;", (rev,)).fetchone()
    orig_row = db_conn.execute(
        "SELECT reverses_id FROM transactions WHERE id=?;", (orig,)).fetchone()
    assert rev_row["reverses_id"] == orig
    assert orig_row["reverses_id"] is None


def test_fetch_transactions_includes_reverses_id(db_conn):
    orig = log_transaction(db_conn, "BUY", "GOLD", 400.0, 2.0, 800.0)
    log_transaction(db_conn, "SELL", "GOLD", 400.0, 2.0, 800.0, reverses_id=orig)
    df = fetch_transactions(db_conn)
    assert "reverses_id" in df.columns
    assert set(df["reverses_id"].dropna()) == {orig}


def test_migration_adds_reverses_id_to_legacy_db(tmp_path):
    db = tmp_path / "legacy.db"
    raw = sqlite3.connect(str(db))
    raw.execute(
        "CREATE TABLE transactions (id TEXT PRIMARY KEY, timestamp TIMESTAMP, "
        "action_type TEXT, metal TEXT, execution_rate_myr REAL, "
        "mass_grams REAL, fiat_total_myr REAL);")
    raw.commit()
    raw.close()
    with get_db_connection(str(db)) as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(transactions);")]
    assert "reverses_id" in cols
