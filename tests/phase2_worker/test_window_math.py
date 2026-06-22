from datetime import datetime, timezone

from worker.main import sleep_until_next_window


def test_seconds_until_window_same_day():
    # 08:00 UTC == 16:00 local; window 17:00 local == 09:00 UTC -> 1 hour
    now = datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)
    secs = sleep_until_next_window(now=now, tz_name="Asia/Kuala_Lumpur")
    assert secs == 3600.0


def test_rolls_to_next_day_when_past_window():
    # 10:00 UTC == 18:00 local, past 17:00 -> next window 09:00 UTC next day
    now = datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc)
    secs = sleep_until_next_window(now=now, tz_name="Asia/Kuala_Lumpur")
    assert secs == 23 * 3600.0


def test_exactly_at_window_waits_full_day():
    now = datetime(2026, 6, 22, 9, 0, tzinfo=timezone.utc)  # exactly 17:00 local
    secs = sleep_until_next_window(now=now, tz_name="Asia/Kuala_Lumpur")
    assert secs == 24 * 3600.0


def test_seconds_is_never_negative():
    now = datetime(2026, 6, 22, 8, 30, tzinfo=timezone.utc)
    secs = sleep_until_next_window(now=now, tz_name="Asia/Kuala_Lumpur")
    assert secs > 0
