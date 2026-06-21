"""Centralized timezone-aware datetime helpers.

Internal storage is always UTC. Local time is applied only at the edges
(worker scheduling, UI display) in later phases.
"""

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
