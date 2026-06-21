from datetime import timezone

from utils.timeutil import now_utc


def test_now_utc_is_timezone_aware_utc():
    dt = now_utc()
    assert dt.tzinfo is not None
    assert dt.utcoffset() == timezone.utc.utcoffset(None)
