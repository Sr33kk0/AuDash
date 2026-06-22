"""metalpriceapi.com REST client and the price-ingestion pipeline.

Fetches MYR-denominated bullion rates, inverts the base->symbol quote into
MYR-per-troy-ounce, validates the payload, and persists via the Phase 1 DAO.
Network failures and malformed payloads raise BullionFetchError so the daemon
loop can swallow them without dying.
"""

import sqlite3

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


def _invert_rate(rate: float | None, symbol: str) -> float:
    """Invert a base->symbol quote into a symbol price; reject missing/non-positive."""
    if rate is None or rate <= 0:
        raise BullionFetchError(f"Missing or non-positive rate for {symbol}")
    return 1.0 / rate


def fetch_raw_bullion_rates(api_key: str, *, base: str = "MYR",
                            symbols: tuple[str, ...] = ("XAU", "XAG"),
                            timeout: float = 10.0) -> dict[str, float]:
    """Fetch bullion rates and return MYR-per-troy-ounce for gold and silver.

    Raises BullionFetchError on transport, decode, or validation failure.
    """
    params = {"api_key": api_key, "base": base, "symbols": ",".join(symbols)}
    try:
        resp = requests.get(_API_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise BullionFetchError(f"HTTP request failed: {exc}") from exc
    except ValueError as exc:  # json decode error
        raise BullionFetchError(f"Invalid JSON payload: {exc}") from exc

    if not data.get("success", False):
        raise BullionFetchError(f"API returned unsuccessful payload: {data}")

    rates = data.get("rates") or {}
    return {
        "gold_rate_per_oz": _invert_rate(rates.get("XAU"), "XAU"),
        "silver_rate_per_oz": _invert_rate(rates.get("XAG"), "XAG"),
    }


def execute_ingestion_pipeline(conn: sqlite3.Connection, api_key: str, *,
                               date: str | None = None) -> dict[str, float]:
    """Fetch, validate, and persist today's spot prices; return the rates."""
    rates = fetch_raw_bullion_rates(api_key)
    gold = rates["gold_rate_per_oz"]
    silver = rates["silver_rate_per_oz"]
    if gold <= 0 or silver <= 0:
        raise BullionFetchError(
            f"Non-positive rates: gold={gold}, silver={silver}")
    day = date or now_utc().date().isoformat()
    write_spot_prices(conn, day, gold, silver)
    return rates
