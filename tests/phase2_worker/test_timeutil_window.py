from datetime import datetime, timezone

import pytest

from utils.timeutil import next_local_time_utc, to_local


def test_to_local_converts_utc_to_zone():
    # 09:00 UTC == 17:00 Asia/Kuala_Lumpur (UTC+8, no DST)
    dt = datetime(2026, 6, 22, 9, 0, tzinfo=timezone.utc)
    local = to_local(dt, "Asia/Kuala_Lumpur")
    assert local.hour == 17
    assert local.utcoffset().total_seconds() == 8 * 3600


def test_to_local_rejects_naive_datetime():
    with pytest.raises(ValueError):
        to_local(datetime(2026, 6, 22, 9, 0), "Asia/Kuala_Lumpur")


def test_next_local_time_utc_future_same_day():
    now = datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)  # 16:00 local
    target = next_local_time_utc(17, 0, "Asia/Kuala_Lumpur", now=now)
    assert target == datetime(2026, 6, 22, 9, 0, tzinfo=timezone.utc)


def test_next_local_time_utc_rolls_to_next_day_when_past():
    now = datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc)  # 18:00 local
    target = next_local_time_utc(17, 0, "Asia/Kuala_Lumpur", now=now)
    assert target == datetime(2026, 6, 23, 9, 0, tzinfo=timezone.utc)


def test_next_local_time_utc_exactly_at_window_rolls_forward():
    now = datetime(2026, 6, 22, 9, 0, tzinfo=timezone.utc)  # exactly 17:00 local
    target = next_local_time_utc(17, 0, "Asia/Kuala_Lumpur", now=now)
    assert target == datetime(2026, 6, 23, 9, 0, tzinfo=timezone.utc)


def test_next_local_time_utc_returns_utc_aware():
    target = next_local_time_utc(17, 0, "Asia/Kuala_Lumpur")
    assert target.tzinfo is not None
    assert target.utcoffset() == timezone.utc.utcoffset(None)
