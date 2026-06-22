"""Centralized timezone-aware datetime helpers.

Internal storage is always UTC. Local time is applied only at the edges
(worker scheduling, UI display).
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def now_utc() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_local(dt: datetime, tz_name: str) -> datetime:
    """Convert a timezone-aware datetime to the given IANA zone.

    Raises ValueError if `dt` is naive (Rule 1: no naive datetimes).
    """
    if dt.tzinfo is None:
        raise ValueError("to_local requires a timezone-aware datetime")
    return dt.astimezone(ZoneInfo(tz_name))


def next_local_time_utc(hour: int, minute: int, tz_name: str,
                        now: datetime | None = None) -> datetime:
    """Return the next future HH:MM local instant as a UTC datetime.

    If HH:MM local has already passed today (or is exactly `now`), the
    result rolls forward to the next day.
    """
    now = now or now_utc()
    zone = ZoneInfo(tz_name)
    local_now = now.astimezone(zone)
    target = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= local_now:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc)
