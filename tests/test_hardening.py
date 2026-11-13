"""Robustness: offline mode never touches the network, unknown API paths are JSON 404s, the news table stays bounded,
and hostile inputs never cause server errors."""
import os
from datetime import timedelta

import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from equitypilot import db  # noqa: E402
from equitypilot.data import feeds as N  # noqa: E402
from equitypilot.data import marketdata as M  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_offline_provider_never_calls_the_network(monkeypatch):
    prov = M.YahooDelayedProvider()
    monkeypatch.setattr(prov, "_yf", lambda: (_ for _ in ()).throw(AssertionError("network used in offline mode")))
    assert M.config.OFFLINE
    assert prov.bars("TCS.NS", "1D").empty and prov.actions("TCS.NS") == [] and prov.quotes(["TCS.NS"]) == {}


def test_offline_chart_falls_back_to_stored_history(client):
    d = client.get("/api/chart/SAMPLE-ALPHA?range=1Y").json()
    assert d["bars"] and d["status"] == "sample"
    r = client.get("/api/chart/TCS.NS?range=1D")                       # untracked + offline: empty, not an error
    assert r.status_code == 200 and r.json()["bars"] == []


def test_unknown_api_path_is_json_404(client):
    r = client.get("/api/this/does/not/exist")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("path", [
    "/api/companies/..%2F..%2Fetc%2Fpasswd", "/api/companies/%00", "/api/chart/%27%20OR%201%3D1?range=1Y",
    "/api/search?q=%27%3B%20DROP%20TABLE%20companies%3B--", "/api/news/feed?section=top&q=%3Cscript%3E",
    "/api/news/related?title=x", "/api/compare?symbols=,,,", "/api/quotes?symbols=" + "A," * 100,
])
def test_hostile_inputs_never_500(client, path):
    assert client.get(path).status_code < 500


def test_prune_news_keeps_tracked_and_recent():
    now = db.utcnow()
    rows = [
        {"feed": "nse_announcements", "title": "Old untracked", "url": "https://x.test/p1", "published": now - timedelta(days=40), "symbol": None},
        {"feed": "nse_announcements", "title": "Old tracked", "url": "https://x.test/p2", "published": now - timedelta(days=40), "symbol": "SAMPLE-ALPHA"},
        {"feed": "nse_announcements", "title": "Recent untracked", "url": "https://x.test/p3", "published": now - timedelta(days=2), "symbol": None},
        {"feed": "media_et_markets", "title": "Very old media", "url": "https://x.test/p4", "published": now - timedelta(days=400), "symbol": None},
    ]
    db.upsert(db.news_items, [{**r, "category": None, "summary": None, "source": "t", "fetched_at": now} for r in rows], ["feed", "url", "title"])
    N.prune_news(force=True)
    left = set(db.read_df(db.select(db.news_items.c.title).where(db.news_items.c.url.like("https://x.test/p%")))["title"])
    assert left == {"Old tracked", "Recent untracked"}
    with db.get_engine().begin() as conn:
        conn.execute(db.news_items.delete().where(db.news_items.c.url.like("https://x.test/p%")))


def test_quote_cache_single_flight(monkeypatch):
    """Many concurrent requests for the same stale symbols must cause one provider call, not one each."""
    import threading
    import time as _t
    calls = []

    class Slow(M.MarketDataProvider):
        def quotes(self, symbols):
            calls.append(list(symbols))
            _t.sleep(0.3)
            return {s: M.Quote(s, 1.0, 1.0, 0.0, 0.0, None, "2026-11-13T09:58:00", "close", "test") for s in symbols}
    monkeypatch.setattr(M, "_PROVIDER", Slow())
    monkeypatch.setattr(M, "_persist", lambda q: None)
    cache = M.QuoteCache(ttl=60)
    threads = [threading.Thread(target=cache.get, args=(["AAA.NS", "BBB.NS"],)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1


def test_stale_index_tiles_are_served_without_waiting(monkeypatch):
    import time as _t
    monkeypatch.setattr(M.config, "OFFLINE", False)
    old = [{"symbol": "^NSEI", "name": "NIFTY 50", "last": 1.0}]
    monkeypatch.setattr(M, "_IDX_CACHE", {"t": 0.0, "data": old})     # stale
    monkeypatch.setattr(M, "_compute_index_overview", lambda: _t.sleep(2) or [])
    t0 = _t.time()
    assert M.index_overview() == old and _t.time() - t0 < 0.5


def test_unrelated_symbols_do_not_wait_behind_a_slow_fetch(monkeypatch):
    """Regression: a big background download (about 140 symbols) made a chart for one index wait about 57 s."""
    import threading
    import time as _t

    class SlowForBig(M.MarketDataProvider):
        def quotes(self, symbols):
            _t.sleep(2.0 if len(symbols) > 1 else 0.05)
            return {s: M.Quote(s, 1.0, 1.0, 0.0, 0.0, None, "2026-11-13T09:58:00", "close", "test") for s in symbols}
    monkeypatch.setattr(M, "_PROVIDER", SlowForBig())
    monkeypatch.setattr(M, "_persist", lambda q: None)
    cache = M.QuoteCache(ttl=60)
    big = threading.Thread(target=cache.refresh, args=([f"S{i}.NS" for i in range(140)],))
    big.start()
    _t.sleep(0.2)
    t0 = _t.time()
    assert cache.get(["^NSEI"])["^NSEI"]["price"] == 1.0 and _t.time() - t0 < 1.0
    big.join()
