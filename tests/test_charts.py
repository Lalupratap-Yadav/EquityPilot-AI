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
    monkeypatch.setattr(M.config, "OFFLINE", False)          # the fake provider stands in for the network
    prov = M.YahooDelayedProvider()
    monkeypatch.setattr(prov, "_yf", lambda: _FakeYF(_daily_frame()))
    bars = prov.bars("TEST.NS", "1Y")
    assert str(bars["time"].iloc[0].date()) == "2026-11-02"
    assert (bars["time"].dt.hour == 0).all()


def test_intraday_bars_are_utc(monkeypatch):
    idx = pd.date_range("2026-11-12 09:15", periods=4, freq="5min", tz="Asia/Kolkata", name="Datetime")
    frame = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": [1.0, 2, 3, 4], "Volume": 5}, index=idx)
    monkeypatch.setattr(M.config, "OFFLINE", False)
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


# ------------------------------------------------------------------ one source of truth for the latest price
def test_merge_quote_appends_today_when_daily_row_is_missing():
    """Regression: after midnight Yahoo's daily row for the last session is NaN, so tiles/charts showed the day before."""
    bars = pd.DataFrame({"time": pd.to_datetime(["2026-11-10", "2026-11-11"]), "open": 1.0, "high": 101.0, "low": 99.0,
                         "close": [100.0, 101.0], "volume": 5.0})
    q = {"price": 102.5, "prev_close": 101.0, "time": "2026-11-12T09:59:00"}      # 15:29 IST on 12 Nov
    out = RM._merge_quote(bars, q, intraday=False)
    assert len(out) == 3 and out["time"].iloc[-1] == pd.Timestamp("2026-11-12") and out["close"].iloc[-1] == 102.5
    same_day = RM._merge_quote(out, {**q, "price": 103.0}, intraday=False)
    assert len(same_day) == 3 and same_day["close"].iloc[-1] == 103.0 and same_day["high"].iloc[-1] == 103.0
    assert len(RM._merge_quote(bars, {**q, "time": "2026-11-09T09:59:00"}, intraday=False)) == 2   # older quote ignored


def test_merge_quote_updates_weekly_bar_in_same_week():
    bars = pd.DataFrame({"time": pd.to_datetime(["2026-10-26", "2026-11-02", "2026-11-09"]), "open": 1.0, "high": 1.0,
                         "low": 1.0, "close": [1.0, 2.0, 3.0], "volume": 1.0})
    out = RM._merge_quote(bars, {"price": 4.0, "time": "2026-11-12T09:59:00"}, intraday=False)
    assert len(out) == 3 and out["close"].iloc[-1] == 4.0


def test_merge_quote_intraday_same_session_only():
    t = pd.date_range("2026-11-12 03:45", periods=3, freq="5min")
    bars = pd.DataFrame({"time": t, "open": 1.0, "high": 2.0, "low": 0.5, "close": [1.0, 1.5, 1.8], "volume": 1.0})
    out = RM._merge_quote(bars, {"price": 1.9, "time": "2026-11-12T03:57:00"}, intraday=True)
    assert out["close"].iloc[-1] == 1.9 and len(out) == 3
    assert RM._merge_quote(bars, {"price": 9.0, "time": "2026-11-13T04:00:00"}, intraday=True)["close"].iloc[-1] == 1.8


def test_index_tiles_use_the_shared_quote(monkeypatch):
    """Tiles take last/prev from the same quote cache as the charts; daily history only draws the sparkline."""
    monkeypatch.setattr(M.config, "OFFLINE", False)
    monkeypatch.setattr(M, "_IDX_CACHE", {"t": 0.0, "data": []})
    monkeypatch.setattr(M, "_load_index_snapshot", lambda: [])          # no saved tiles: compute from the quote
    hist = {"^BSESN": {"dates": ["2026-11-09", "2026-11-11"], "closes": [81106.65, 81879.40]}}
    monkeypatch.setattr(M, "_index_history", lambda ttl=900: hist)
    monkeypatch.setattr(M.QUOTES, "get", lambda syms, stale_ok=False: {
        "^BSESN": {"price": 81911.01, "prev_close": 81879.40, "time": "2026-11-12T09:59:00", "status": "close"}})
    tiles = {t["symbol"]: t for t in M.index_overview()}
    s = tiles["^BSESN"]
    assert s["last"] == 81911.01 and s["as_of"] == "2026-11-12"
    assert s["change_pct"] == pytest.approx(81911.01 / 81879.40 - 1)
    assert s["spark"][-1] == 81911.01 and len(s["spark"]) == 3


def test_bad_tick_filter_removes_spike_and_keeps_real_moves():
    # 75 five-minute bars of normal noise (as on a real 1D chart) with one closing-session glitch at bar 70
    rng = np.random.default_rng(1)
    close = list(100 * np.cumprod(1 + rng.normal(0, 0.0004, 75)))
    good = close[70]
    close[70] = close[69] * 0.991                                                 # jumps 0.9% away ...
    close[71] = close[69] * 1.0005                                                # ... and straight back
    t = pd.date_range("2026-11-12 03:45", periods=75, freq="5min")
    bars = pd.DataFrame({"time": t, "open": close, "high": [c * 1.0003 for c in close], "low": [c * 0.9997 for c in close],
                         "close": close, "volume": 0.0})
    bars.loc[70, "low"] = close[69] * 0.98                                        # bogus wick on the spike bar
    bars.loc[71, "open"] = close[70]                                              # next bar opens at the glitch
    out, n = M.clean_intraday(bars)
    assert len(out) == 74 and close[70] not in out["close"].tolist() and n >= 1 and good != close[70]
    assert out["low"].min() > close[69] * 0.995
    assert out["close"].iloc[-1] == close[-1]                                     # latest value never altered
    # a genuine sustained move (no reversal) is kept untouched
    trend = list(close[:60]) + [close[59] * (1 + 0.01 * k) for k in range(1, 16)]
    out2, n2 = M.clean_intraday(bars.assign(close=trend, open=trend, high=[c * 1.0003 for c in trend], low=[c * 0.9997 for c in trend]))
    assert len(out2) == 75 and n2 == 0
