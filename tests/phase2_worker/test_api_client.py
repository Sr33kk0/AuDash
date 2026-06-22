import pytest

from worker import api_client
from worker.api_client import (
    GRAMS_PER_TROY_OZ,
    BullionFetchError,
    convert_oz_to_grams,
    fetch_raw_bullion_rates,
)


def test_grams_per_troy_oz_constant():
    assert GRAMS_PER_TROY_OZ == 31.1034768


def test_convert_oz_to_grams():
    # 31.1034768 MYR/oz -> 1.0 MYR/gram
    assert convert_oz_to_grams(31.1034768) == pytest.approx(1.0)
    assert convert_oz_to_grams(12000.0) == pytest.approx(12000.0 / 31.1034768)


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        if self._payload is _BAD_JSON:
            raise ValueError("No JSON object could be decoded")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise api_client.requests.HTTPError(f"status {self.status_code}")


_BAD_JSON = object()


def _patch_get(monkeypatch, payload, status=200):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(payload, status)
    monkeypatch.setattr(api_client.requests, "get", fake_get)


def test_inverts_base_to_symbol_rate_into_myr_per_oz(monkeypatch):
    _patch_get(monkeypatch, {"success": True, "base": "MYR",
                             "rates": {"XAU": 0.0001, "XAG": 0.01}})
    rates = fetch_raw_bullion_rates("KEY")
    assert rates["gold_rate_per_oz"] == pytest.approx(10000.0)
    assert rates["silver_rate_per_oz"] == pytest.approx(100.0)


def test_unsuccessful_payload_raises(monkeypatch):
    _patch_get(monkeypatch, {"success": False, "error": {"info": "bad key"}})
    with pytest.raises(BullionFetchError):
        fetch_raw_bullion_rates("KEY")


def test_missing_symbol_raises(monkeypatch):
    _patch_get(monkeypatch, {"success": True, "rates": {"XAU": 0.0001}})
    with pytest.raises(BullionFetchError):
        fetch_raw_bullion_rates("KEY")


def test_zero_rate_raises(monkeypatch):
    _patch_get(monkeypatch, {"success": True, "rates": {"XAU": 0.0, "XAG": 0.01}})
    with pytest.raises(BullionFetchError):
        fetch_raw_bullion_rates("KEY")


def test_http_error_raises_bullion_fetch_error(monkeypatch):
    _patch_get(monkeypatch, {}, status=500)
    with pytest.raises(BullionFetchError):
        fetch_raw_bullion_rates("KEY")


def test_non_json_body_raises_bullion_fetch_error(monkeypatch):
    _patch_get(monkeypatch, _BAD_JSON)
    with pytest.raises(BullionFetchError):
        fetch_raw_bullion_rates("KEY")


def test_negative_rate_raises(monkeypatch):
    _patch_get(monkeypatch, {"success": True, "rates": {"XAU": -0.0001, "XAG": 0.01}})
    with pytest.raises(BullionFetchError):
        fetch_raw_bullion_rates("KEY")


def test_transport_error_raises_bullion_fetch_error(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise api_client.requests.ConnectionError("network down")
    monkeypatch.setattr(api_client.requests, "get", fake_get)
    with pytest.raises(BullionFetchError):
        fetch_raw_bullion_rates("KEY")
