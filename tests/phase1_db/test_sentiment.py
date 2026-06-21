from database.connection import fetch_latest_sentiment, write_sentiment_snapshot


def test_write_then_fetch_latest_roundtrips_headlines(db_conn):
    write_sentiment_snapshot(
        db_conn, "2026-06-21", 2.5, "Fed policy",
        "Hawkish tone weighs on gold.", ["Fed holds rates", "CPI cooler"],
    )
    snap = fetch_latest_sentiment(db_conn)
    assert snap["date"] == "2026-06-21"
    assert snap["sentiment_score"] == 2.5
    assert snap["dominant_risk_factor"] == "Fed policy"
    assert snap["source_headlines"] == ["Fed holds rates", "CPI cooler"]


def test_fetch_latest_returns_most_recent_date(db_conn):
    write_sentiment_snapshot(db_conn, "2026-06-19", 1.0, "a", "s", [])
    write_sentiment_snapshot(db_conn, "2026-06-21", -3.0, "b", "t", [])
    write_sentiment_snapshot(db_conn, "2026-06-20", 0.0, "c", "u", [])
    snap = fetch_latest_sentiment(db_conn)
    assert snap["date"] == "2026-06-21"
    assert snap["sentiment_score"] == -3.0


def test_fetch_latest_empty_returns_none(db_conn):
    assert fetch_latest_sentiment(db_conn) is None
