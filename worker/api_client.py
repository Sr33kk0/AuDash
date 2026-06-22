"""metalpriceapi.com REST client and the price-ingestion pipeline.

Fetches MYR-denominated bullion rates, inverts the base->symbol quote into
MYR-per-troy-ounce, validates the payload, and persists via the Phase 1 DAO.
Network failures and malformed payloads raise BullionFetchError so the daemon
loop can swallow them without dying.
"""

import requests

from database.connection import write_spot_prices
from utils.timeutil import now_utc

GRAMS_PER_TROY_OZ = 31.1034768
_API_URL = "https://api.metalpriceapi.com/v1/latest"


class BullionFetchError(Exception):
    """Raised when bullion rates cannot be fetched, parsed, or validated."""


def convert_oz_to_grams(oz_rate: float) -> float:
    """Convert a per-troy-ounce rate to a per-gram rate."""
    return oz_rate / GRAMS_PER_TROY_OZ
