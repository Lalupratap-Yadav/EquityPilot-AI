"""v2.7 performance work: every speed-up here must give exactly the same answers as before.

Covers: statement/ratio caches and their invalidation, the news de-duplication index (against the original
all-pairs rule), batched quote reads, quotes that are final after the session, non-blocking page quotes, the yfinance
single-symbol layout bug, the worker process, non-blocking news refreshes, search scope and the loopback launcher."""
from __future__ import annotations

import random
import socket
import threading
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from equitypilot import db, workers
from equitypilot.analytics import ratios as R
from equitypilot.analytics import screener
from equitypilot.data import marketdata as M
from equitypilot.data import repository as repo

IST = timezone(timedelta(hours=5, minutes=30))
SYM = "SAMPLE-ALPHA"


# ------------------------------------------------------------------ statement and ratio caches
def test_financials_cache_returns_equal_independent_copies():
    a = repo.get_financials(SYM)
    b = repo.get_financials(SYM)
    assert a.signature is not None and a.signature == b.signature
    pd.testing.assert_frame_equal(a.wide, b.wide)
    a.wide.iloc[0, 0] = -123456.0                       # a caller modifying its copy never changes the cache
    c = repo.get_financials(SYM)
    assert c.wide.iloc[0, 0] != -123456.0


def test_financials_cache_sees_changed_statements():
    fd = repo.get_financials(SYM)
    period = fd.periods[-1]
    row = db.read_df(db.select(db.financials).where(db.financials.c.symbol == SYM)
                     .where(db.financials.c.period_type == "annual").where(db.financials.c.line_item == "revenue")
                     .where(db.financials.c.basis == fd.basis)).copy()
    row["period_end"] = pd.to_datetime(row["period_end"])
    rec = row[row["period_end"] == period].iloc[0].to_dict()
    rec.pop("id", None)
    rec["period_end"] = pd.Timestamp(rec["period_end"]).date()
    rec["fetched_at"] = pd.Timestamp(rec["fetched_at"]).to_pydatetime()      # unchanged: only the value differs
    old = rec["value"]
    try:
        rec["value"] = old * 2
        repo.save_financial_rows([rec])
        fresh = repo.get_financials(SYM)
        assert fresh.signature != fd.signature
        assert fresh.latest("revenue") == pytest.approx(old * 2)
        assert R.compute_ratios(fresh).loc["net_margin"].iloc[-1] == pytest.approx(
            R.compute_ratios(fd).loc["net_margin"].iloc[-1] / 2)
        assert screener.company_metrics(SYM)["revenue"] == pytest.approx(old * 2)
    finally:
        rec["value"] = old
        repo.save_financial_rows([rec])
    assert repo.get_financials(SYM).latest("revenue") == pytest.approx(old)


def test_ratio_cache_matches_uncached_and_returns_copies():
    fd = repo.get_financials(SYM)
    cached = R.compute_ratios(fd)
    pd.testing.assert_frame_equal(cached, R._compute_ratios(fd))
    cached.iloc[0, 0] = 999.0
    assert R.compute_ratios(fd).iloc[0, 0] != 999.0


def test_company_metrics_identical_with_bulk_inputs():
    syms = repo.list_companies()["symbol"].tolist()
    comps, quotes = repo.get_companies(syms), repo.get_quotes(syms)
    for s in syms:
        a = screener.company_metrics(s)
        b = screener.company_metrics(s, company=comps.get(s), quote=quotes.get(s))
        assert pd.Series(a).equals(pd.Series(b)), s


# ------------------------------------------------------------------ news de-duplication
def _brute_dedupe(items):
    """The original O(n^2) rule, kept here as the reference."""
    import re

    from api.routes_news import _TIER_RANK, _age_h, _words

    def key(it):
        base = re.sub(r"[^a-z0-9]+", " ", it["title"].lower()).strip()[:100]
        return base + "|" + re.sub(r"[^a-z0-9]+", " ", (it["summary"] or "").lower())[:80] if it["tier"] == "primary" else base
    order = sorted(items, key=lambda x: (_TIER_RANK.get(x["tier"], 9), x["published"] or "9999"))
    kept, media = {}, []
    for it in order:
        k = key(it)
        if k in kept:
            kept[k]["also"].append(it["publisher"] or it["source"])
            continue
        if it["tier"] != "primary":
            w = _words(it["title"])
            dup = None
            for ws, other in media:
                if w and ws and len(w & ws) / len(w | ws) >= 0.75 and abs(_age_h(other) - _age_h(it)) <= 48:
                    dup = other
                    break
            if dup is not None:
                src = it["publisher"] or it["source"]
                if src not in dup["also"] and src != (dup["publisher"] or dup["source"]):
                    dup["also"].append(src)
                continue
            media.append((w, it))
        kept[k] = it
    for it in kept.values():
        it["also"] = sorted({a for a in it["also"] if a and a != (it["publisher"] or it["source"])})
    return list(kept.values())


def test_dedupe_index_identical_to_all_pairs_rule():
    from api import routes_news as RN
    rng = random.Random(7)
    vocab = [f"word{i}" for i in range(40)] + ["sensex", "nifty", "rally", "falls", "rbi", "policy", "bank", "stocks"]
    now = db.utcnow()
    for trial in range(30):
        items = []
        for i in range(rng.randint(5, 120)):
            base = rng.sample(vocab, rng.randint(1, 9))
            if items and rng.random() < 0.4:                   # near-copies of an earlier headline
                prev = rng.choice(items)["title"].split()
                base = prev[:] + ([rng.choice(vocab)] if rng.random() < 0.5 else [])
                if len(base) > 3 and rng.random() < 0.5:
                    base.pop(rng.randrange(len(base)))
            tier = rng.choice(["primary", "established", "established", "unrated", "user"])
            items.append({"title": " ".join(base), "summary": rng.choice([None, "subject " + rng.choice(vocab)]),
                          "tier": tier, "publisher": rng.choice(["ET", "Mint", "BS", None]), "source": rng.choice(["NSE", "Yahoo"]),
                          "published": (now - timedelta(hours=rng.uniform(0, 120))).isoformat() if rng.random() > 0.05 else None,
                          "also": []})
        copy = [{**i, "also": []} for i in items]
        got = [(i["title"], i["tier"], i["published"], tuple(i["also"])) for i in RN.dedupe(items)]
        want = [(i["title"], i["tier"], i["published"], tuple(i["also"])) for i in _brute_dedupe(copy)]
        assert got == want, f"trial {trial}"


def test_clean_summary_strips_exchange_preamble():
    from api.routes_news import _clean_summary
    t = "Tata Consultancy Services Limited"
    assert _clean_summary(t, f"{t} has informed the Exchange about Board Meeting|SUBJECT: results") == "Board Meeting - Subject: results"
    assert _clean_summary(t, f"{t.upper()} HAS INFORMED THE EXCHANGE REGARDING  dividend") == "dividend"
    assert _clean_summary("A (B) [C]", "A (B) [C] has informed the Exchange about x") == "x"     # regex characters in titles
    assert _clean_summary(t, t) is None


def test_entity_fold_fast_path_unchanged():
    from equitypilot.data import entities as E
    for s in ["Nestlé India", "Dr. Reddy’s", "plain ascii text", "Café ‘quoted’", ""]:
        slow = "".join(c for c in __import__("unicodedata").normalize("NFKD", s.replace("’", "'").replace("‘", "'").replace("�", "e"))
                       if not __import__("unicodedata").combining(c))
        assert E._fold(s) == slow


# ------------------------------------------------------------------ quotes
def test_from_db_many_matches_single_reads():
    syms = repo.list_companies()["symbol"].tolist() + ["NOPE.NS"]
    many = M._from_db_many(syms)
    assert set(many) == set(syms)
    for s in syms:
        assert many[s] == M._from_db(s)
    assert many["NOPE.NS"]["status"] == "unavailable"


def test_after_session_quotes_are_final_while_closed():
    qc = M.QuoteCache(ttl=60)
    fri_1700 = datetime(2026, 11, 20, 17, 0, tzinfo=IST).timestamp()           # after Friday's close
    fri_1531 = datetime(2026, 11, 20, 15, 31, tzinfo=IST).timestamp()          # closing price may still settle
    qc._data = {"A": (fri_1700, {}), "B": (fri_1531, {})}
    assert qc._stale_list(["A", "B", "C"], now=fri_1700 + 600) == ["B", "C"]   # A fetched after the session: final
    assert qc._stale_list(["A"], now=fri_1700 + 1700) == []                    # still within FINAL_TTL (30 min)
    assert qc._stale_list(["A"], now=fri_1700 + 1900) == ["A"]                 # FINAL_TTL elapsed: refreshed again
    sat = datetime(2026, 11, 21, 12, 0, tzinfo=IST).timestamp()                # weekend fetches are final as well
    qc._data = {"A": (sat, {})}
    assert qc._stale_list(["A"], now=sat + 900) == []
    mon_1000 = datetime(2026, 11, 23, 10, 0, tzinfo=IST).timestamp()           # in session: normal TTL again
    qc._data = {"A": (mon_1000 - 61, {})}
    assert qc._stale_list(["A"], now=mon_1000) == ["A"]


def test_last_session_date():
    assert str(M._last_session_date(datetime(2026, 11, 22, 10, 0, tzinfo=IST))) == "2026-11-20"    # Sunday -> Friday
    assert str(M._last_session_date(datetime(2026, 11, 23, 8, 0, tzinfo=IST))) == "2026-11-20"     # Monday pre-market
    assert str(M._last_session_date(datetime(2026, 11, 23, 15, 45, tzinfo=IST))) == "2026-11-23"   # Monday after close


def _bars(start: str, closes: list[float], freq: str, tz=IST) -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(closes), freq=freq, tz=tz)
    return pd.DataFrame({"Open": closes, "High": closes, "Low": closes, "Close": closes, "Adj Close": closes,
                         "Volume": [1000.0] * len(closes)}, index=idx)


class FakeYF:
    """yf.download stand-in that builds the yfinance 1.x layout (ticker level kept even for one symbol)."""

    def __init__(self, daily: dict, intraday: dict):
        self.daily, self.intraday, self.calls = daily, intraday, []

    def download(self, syms, period, interval, **kw):
        self.calls.append((interval, list(syms)))
        src = self.daily if interval == "1d" else self.intraday
        frames = {s: src[s] for s in syms if s in src}
        return pd.concat(frames, axis=1, sort=True) if frames else pd.DataFrame()


def _provider_with(fake, monkeypatch):
    monkeypatch.setattr(M.config, "OFFLINE", False)
    p = M.YahooDelayedProvider()
    monkeypatch.setattr(p, "_yf", lambda: fake)
    return p


def test_single_symbol_quote_with_yfinance_1x_layout(monkeypatch):
    """Regression: a one-symbol download keeps the ticker column level; the old code returned no quote at all."""
    fake = FakeYF({"TCS.NS": _bars("2026-11-16", [10, 11, 12, 13, 14], "D")},
                  {"TCS.NS": _bars("2026-11-20 09:15", [14.0, 14.5], "min")})
    p = _provider_with(fake, monkeypatch)
    q = p.quotes(["TCS.NS"], status_open=True, now=datetime(2026, 11, 20, 9, 20, tzinfo=IST))
    assert q["TCS.NS"].price == 14.5 and q["TCS.NS"].prev_close == 13


def test_closed_market_skips_intraday_only_when_daily_is_final(monkeypatch):
    daily = {"A.NS": _bars("2026-11-16", [1, 2, 3, 4, 5], "D"),             # includes Friday 20 Nov
             "B.NS": _bars("2026-11-15", [1, 2, 3, 4, 5], "D")}             # last row Thursday: not final yet
    intra = {"A.NS": _bars("2026-11-20 15:27", [5.0, 5.0], "min"), "B.NS": _bars("2026-11-20 15:27", [6.0, 6.5], "min")}
    fake = FakeYF(daily, intra)
    p = _provider_with(fake, monkeypatch)
    sat = datetime(2026, 11, 21, 11, 0, tzinfo=IST)
    q = p.quotes(["A.NS", "B.NS"], status_open=False, now=sat)
    assert fake.calls == [("1d", ["A.NS", "B.NS"]), ("1m", ["B.NS"])]       # only B needed intraday data
    assert q["A.NS"].price == 5 and q["A.NS"].prev_close == 4
    assert q["A.NS"].time == "2026-11-20T10:00:00"                           # 15:30 IST, the official close time
    assert q["B.NS"].price == 6.5 and q["B.NS"].prev_close == 5 and q["A.NS"].status == "close"
    fake.calls.clear()
    p.quotes(["A.NS", "B.NS"], status_open=True, now=datetime(2026, 11, 20, 11, 0, tzinfo=IST))   # in session
    assert fake.calls == [("1d", ["A.NS", "B.NS"]), ("1m", ["A.NS", "B.NS"])]


def test_get_nowait_answers_from_cache_and_refreshes_in_background(monkeypatch):
    qc = M.QuoteCache(ttl=60)
    started, release = threading.Event(), threading.Event()

    def slow_quotes(syms):
        started.set()
        release.wait(5)
        return {s: M.Quote(s, 101.0, 100.0, 1.0, 0.01, None, "2026-11-20T10:00:00", "delayed", "fake") for s in syms}
    monkeypatch.setattr(M, "_provider_quotes", slow_quotes)
    monkeypatch.setattr(M.config, "OFFLINE", False)
    qc._data = {SYM: (time.time(), {"symbol": SYM, "price": 1.0})}
    t = time.perf_counter()
    out = qc.get_nowait([SYM, "TCS.NS"])
    assert time.perf_counter() - t < 0.5                      # did not wait for the provider
    assert out[SYM]["price"] == 1.0 and "TCS.NS" in out
    assert started.wait(2)                                     # the stale/missing symbol is being fetched
    release.set()
    for _ in range(50):
        if qc.peek("TCS.NS")[1]:
            break
        time.sleep(0.05)
    assert qc.peek("TCS.NS")[1]["price"] == 101.0
    assert not any(s.startswith("SAMPLE-") for s in qc._data if s != SYM)


# ------------------------------------------------------------------ worker process
def test_worker_disabled_by_default_and_falls_back():
    assert not workers.available()
    with pytest.raises(workers.WorkerUnavailable):
        workers.run(screener._worker_universe_frame)


def test_worker_process_gives_the_same_universe_frame(monkeypatch):
    monkeypatch.setenv("EQUITYPILOT_WORKER_PROCESS", "1")
    workers.enable()
    try:
        remote = workers.run(screener._worker_universe_frame, timeout=300)
    finally:
        workers._STATE["enabled"] = False
        workers.shutdown()
    local = screener.universe_frame()
    pd.testing.assert_frame_equal(remote.reset_index(drop=True), local.reset_index(drop=True))


# ------------------------------------------------------------------ requests never wait for publishers
def test_home_news_does_not_wait_for_feed_downloads(monkeypatch):
    from fastapi.testclient import TestClient

    from api.main import app
    from equitypilot.data import feeds as N
    calls = []
    monkeypatch.setattr(N, "refresh_all", lambda *a, **k: (calls.append(1), time.sleep(3)))
    c = TestClient(app)
    t = time.perf_counter()
    r = c.get("/api/news?section=economy&limit=3")
    assert r.status_code == 200 and time.perf_counter() - t < 2.5


def test_search_news_excludes_exchange_filing_titles():
    from api import routes_search as RS
    assert not any(f.startswith("nse_") for f in RS._SEARCH_NEWS_FEEDS)
    assert "yahoo_market" in RS._SEARCH_NEWS_FEEDS and "rbi_press" in RS._SEARCH_NEWS_FEEDS


# ------------------------------------------------------------------ launcher
def test_loopback_launcher_binds_ipv4_and_ipv6_loopback_only():
    from api.__main__ import loopback_sockets
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    socks = loopback_sockets(port)
    try:
        hosts = {s.getsockname()[0] for s in socks}
        assert "127.0.0.1" in hosts
        assert hosts <= {"127.0.0.1", "::1"}                    # never 0.0.0.0 / ::
    finally:
        for s in socks:
            s.close()


def test_company_news_feed_does_not_wait_for_the_provider(monkeypatch):
    from fastapi.testclient import TestClient

    from api import routes_news as RN
    from api.main import app
    started = threading.Event()
    monkeypatch.setattr(RN.config, "OFFLINE", False)
    monkeypatch.setattr(RN.repo, "refresh_news", lambda s: (started.set(), time.sleep(3), (True, "ok"))[-1])
    db.set_setting("company_news:SAMPLE-ALPHA", None)
    db.set_setting("company_news:TCS.NS", "2000-01-01T00:00:00")        # stale: a refresh is due
    c = TestClient(app)
    t = time.perf_counter()
    r = c.get("/api/news/feed?section=company&symbol=TCS.NS")
    assert r.status_code == 200 and time.perf_counter() - t < 2.5          # answered from stored items
    assert started.wait(2)                                                 # refresh running in the background
    assert RN.refresh_company_news_soon("TCS.NS") is False                 # one refresh per company at a time


def test_charts_serve_cached_bars_and_refresh_in_background(monkeypatch):
    from api import routes_market as RM
    calls = []
    fresh = pd.DataFrame({"time": pd.to_datetime(["2026-11-20 09:15"]), "open": [2.0], "high": [2.0], "low": [2.0], "close": [2.0], "volume": [1.0]})
    old = fresh.assign(close=[1.0])

    class Prov:
        name = "fake"

        def bars(self, symbol, rng):
            calls.append((symbol, rng))
            time.sleep(0.5)
            return fresh
    monkeypatch.setattr(RM.M, "provider", lambda: Prov())
    monkeypatch.setattr(RM.config, "OFFLINE", False)
    monkeypatch.setitem(RM._BARS_CACHE, ("X.NS", "1D"), (time.time() - 3600, old))       # expired copy
    t = time.perf_counter()
    got = RM._bars_cached("X.NS", "1D")
    assert time.perf_counter() - t < 0.3 and got["close"].iloc[0] == 1.0                 # served at once
    for _ in range(40):
        if RM._BARS_CACHE[("X.NS", "1D")][1]["close"].iloc[0] == 2.0:
            break
        time.sleep(0.05)
    assert calls == [("X.NS", "1D")] and RM._BARS_CACHE[("X.NS", "1D")][1]["close"].iloc[0] == 2.0
    RM._BARS_CACHE.pop(("X.NS", "1D"), None)


def test_feed_refresh_checks_are_throttled(monkeypatch):
    from equitypilot.data import feeds as N
    started = []
    with N._BG_REFRESH:                       # let a refresh started by an earlier test finish first
        pass
    monkeypatch.setattr(N, "refresh_all", lambda *a, **k: started.append(1))
    monkeypatch.setitem(N._BG_LAST, "t", 0.0)
    for _ in range(5):
        N.refresh_all_in_background()
    time.sleep(0.3)
    assert started == [1]                         # one pass, not one per page view


def test_search_news_index_finds_headlines_and_skips_filings():
    from api import routes_search as RS
    now = db.utcnow()
    db.upsert(db.news_items, [
        {"feed": "media_et_markets", "category": "Indian market", "title": "Zylophone metals rally on export orders",
         "summary": None, "url": "https://example.com/zylo1", "published": now, "source": "The Economic Times", "symbol": None,
         "fetched_at": now},
        {"feed": "nse_announcements", "category": "General update", "title": "Zylophone Metals Limited",
         "summary": "filing", "url": "https://example.com/zylo2", "published": now, "source": "NSE India", "symbol": None,
         "fetched_at": now}], ["feed", "url", "title"])
    RS._NEWS_INDEX["t"] = 0.0
    RS._CACHE.clear()
    hits = RS._news("zylophone metals")
    assert [h["url"] for h in hits] == ["https://example.com/zylo1"]          # publisher headline found; filing title skipped
    t = time.perf_counter()
    RS._news("zylophone metals")
    assert time.perf_counter() - t < 0.05                                       # in-memory match
