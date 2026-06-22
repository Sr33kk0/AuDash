import pytest

from worker import api_client
from worker.api_client import BullionFetchError, execute_ingestion_pipeline
from database.connection import fetch_historical_matrix


def _fake_rates(gold, silver):
    def _fn(api_key, **kwargs):
        return {"gold_rate_per_oz": gold, "silver_rate_per_oz": silver}
    return _fn


def test_pipeline_writes_spot_row(db_conn, monkeypatch):
    monkeypatch.setattr(api_client, "fetch_raw_bullion_rates",
                        _fake_rates(12000.0, 150.0))
    result = execute_ingestion_pipeline(db_conn, "KEY", date="2026-06-22")
    assert result == {"gold_rate_per_oz": 12000.0, "silver_rate_per_oz": 150.0}
    df = fetch_historical_matrix(db_conn)
    assert list(df["date"]) == ["2026-06-22"]
    assert df.iloc[0]["gold_rate_per_oz"] == 12000.0
    assert df.iloc[0]["silver_rate_per_oz"] == 150.0


def test_pipeline_defaults_date_to_utc_today(db_conn, monkeypatch):
    from utils.timeutil import now_utc
    monkeypatch.setattr(api_client, "fetch_raw_bullion_rates",
                        _fake_rates(1.0, 1.0))
    execute_ingestion_pipeline(db_conn, "KEY")
    df = fetch_historical_matrix(db_conn)
    assert list(df["date"]) == [now_utc().date().isoformat()]


def test_pipeline_rejects_non_positive_rates(db_conn, monkeypatch):
    monkeypatch.setattr(api_client, "fetch_raw_bullion_rates",
                        _fake_rates(-5.0, 150.0))
    with pytest.raises(BullionFetchError):
        execute_ingestion_pipeline(db_conn, "KEY")
