"""Chart data tests: correct IST dates for daily bars, range slicing, the reference (baseline) price,
the period change and volatility annualisation. Offline: the provider is replaced by a fake."""
import os

import numpy as np
import pandas as pd
import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

import api.routes_market as RM  # noqa: E402
from api.main import app  # noqa: E402
from equitypilot.data import marketdata as M  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


class _FakeTicker:
    def __init__(self, frame):
        self.frame = frame

    def history(self, **_):
        return self.frame


class _FakeYF:
    def __init__(self, frame):
        self.frame = frame

    def Ticker(self, _symbol):  # noqa: N802 - mirrors the yfinance API
        return _FakeTicker(self.frame)


def _daily_frame(n=10):
    # yfinance daily bars are stamped 00:00 Asia/Kolkata, i.e. 18:30 UTC of the previous day
    idx = pd.date_range("2026-11-02", periods=n, freq="B", tz="Asia/Kolkata", name="Date")
    close = np.linspace(100, 110, n)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000}, index=idx)


def test_daily_bars_keep_the_exchange_date(monkeypatch):
    """Regression: daily bars were converted to UTC and shown one day early (12 Nov plotted as 11 Nov)."""
    prov = M.YahooDelayedProvider()
    monkeypatch.setattr(prov, "_yf", lambda: _FakeYF(_daily_frame()))
    bars = prov.bars("TEST.NS", "1Y")
    assert str(bars["time"].iloc[0].date()) == "2026-11-02"
    assert (bars["time"].dt.hour == 0).all()


def test_intraday_bars_are_utc(monkeypatch):
    idx = pd.date_range("2026-11-12 09:15", periods=4, freq="5min", tz="Asia/Kolkata", name="Datetime")
    frame = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": [1.0, 2, 3, 4], "Volume": 5}, index=idx)
    prov = M.YahooDelayedProvider()
    monkeypatch.setattr(prov, "_yf", lambda: _FakeYF(frame))
    bars = prov.bars("TEST.NS", "1D")
    assert bars["time"].iloc[0] == pd.Timestamp("2026-11-12 03:45")    # 09:15 IST


@pytest.mark.parametrize("rng,expected", [("1W", 5), ("1M", 22), ("3M", 66), ("6M", 126), ("1Y", 252)])
def test_sample_chart_respects_range(client, rng, expected):
    d = client.get(f"/api/chart/SAMPLE-ALPHA?range={rng}").json()
    assert len(d["bars"]) == expected and d["intraday"] is False
    assert all(len(b["time"]) == 10 for b in d["bars"])              # plain YYYY-MM-DD dates


def test_chart_baseline_and_change(client):
    d = client.get("/api/chart/SAMPLE-BETA?range=1Y").json()
    first, last = d["bars"][0]["close"], d["bars"][-1]["close"]
    assert d["baseline"] == {"value": pytest.approx(first), "label": "Start of period"}
    assert d["change"]["abs"] == pytest.approx(last - first)
    assert d["change"]["pct"] == pytest.approx(last / first - 1)
    assert d["has_volume"] is True
    assert d["stats"]["volatility"] is not None and 0 < d["stats"]["volatility"] < 2


def test_old_range_alias_still_works(client):
    assert client.get("/api/chart/SAMPLE-ALPHA?range=5D").status_code == 200
    assert client.get("/api/chart/SAMPLE-ALPHA?range=2Y").status_code == 422


def test_one_day_uses_previous_close(client, monkeypatch):
    """1D change is measured from the previous session's close, as exchanges quote it."""
    idx = pd.date_range("2026-11-12 03:45", periods=40, freq="5min")
    intraday = pd.DataFrame({"time": idx, "open": 101.0, "high": 102.0, "low": 100.0, "close": np.linspace(101, 103, 40), "volume": 10.0})
    daily = pd.DataFrame({"time": pd.to_datetime(["2026-11-10", "2026-11-11", "2026-11-12"]), "open": 1.0, "high": 1.0,
                          "low": 1.0, "close": [98.0, 100.0, 103.0], "volume": 1.0})
    monkeypatch.setattr(RM, "_bars_cached", lambda sym, rng: intraday if rng == "1D" else daily)
    monkeypatch.setattr(RM.M.QUOTES, "get", lambda syms, stale_ok=False: {})
    d = client.get("/api/chart/%5ETEST?range=1D").json()
    assert d["intraday"] is True and d["session_date"] == "2026-11-12"
    assert d["baseline"] == {"value": 100.0, "label": "Previous close"}
    assert d["change"]["pct"] == pytest.approx(103 / 100 - 1)


def test_weekly_volatility_is_annualised_with_52(client, monkeypatch):
    rng = np.random.default_rng(0)
    t = pd.date_range("2020-01-06", periods=200, freq="W-MON")
    close = 100 * np.cumprod(1 + rng.normal(0, 0.03, 200))
    weekly = pd.DataFrame({"time": t, "open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    monkeypatch.setattr(RM, "_bars_cached", lambda sym, r: weekly)
    d = client.get("/api/chart/%5EWEEK?range=MAX").json()
    expected = pd.Series(close).pct_change().dropna().std() * 52 ** 0.5
    assert d["stats"]["volatility"] == pytest.approx(expected)
