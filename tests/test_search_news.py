"""v2.5: grouped global search, the news engine (sections, de-duplication, breaking window, filters, saved articles,
explanations, daily summary), glossary coverage and request ids. Runs offline on the temporary test database."""
import os
from datetime import timedelta

import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

import api.routes_news as RN  # noqa: E402
import api.routes_search as RS  # noqa: E402
from api.main import app  # noqa: E402
from equitypilot import db  # noqa: E402
from equitypilot.data import marketdata as M  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(M, "index_overview", lambda ttl=15: [
        {"symbol": "^NSEI", "name": "NIFTY 50", "last": 25144.3, "change": -155.05, "change_pct": -0.00613, "as_of": "2026-11-13", "kind": "broad"}])
    monkeypatch.setattr(RN, "_refresh_in_background", lambda: None)
    RN._LOAD_CACHE.clear()
    RS._CACHE.clear()
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------ search
def test_search_groups_companies_with_preview(client):
    d = client.get("/api/search?q=SAMPLE-ALPHA").json()
    assert d["order"][0] == "companies" and d["companies"][0]["symbol"] == "SAMPLE-ALPHA"
    c = d["companies"][0]
    assert c["exchange"] == "Sample" and "price" in c and "market_cap" in c
    assert client.get("/api/search?q=SAMPLE-ALPHA").headers.get("x-request-id")


@pytest.mark.parametrize("q,group,expect", [
    ("Nifty 50", "indices", "^NSEI"), ("nifty", "indices", "^NSEI"),
    ("Indian banking sector", "industries", "banking"), ("IT industry", "industries", "it"),
    ("Debt to equity ratio", "concepts", None), ("DCF valuation", "concepts", None),
    ("Companies with high ROE", "tools", None),
])
def test_search_understands_topics(client, q, group, expect):
    d = client.get("/api/search", params={"q": q}).json()
    assert d["order"] and d["order"][0] == group, (q, d["order"])
    first = d[group][0]
    if expect:
        assert expect in (first.get("symbol"), first.get("id"), first.get("to"))
    if q == "DCF valuation":                                       # explanation first, then the matching research tool
        assert any(t["to"] == "/valuation" for t in d["tools"])


def test_search_empty_and_no_match(client):
    assert client.get("/api/search?q=").json()["order"] == []
    d = client.get("/api/search?q=zzqqxxnotacompany").json()
    assert d["companies"] == [] and d["indices"] == [] and d["industries"] == []


# ------------------------------------------------------------------ news engine
def _row(feed, title, hours_ago, **kw):
    now = db.utcnow()
    return {"feed": feed, "category": kw.get("category"), "title": title, "summary": kw.get("summary"), "url": kw.get("url", f"https://x.test/{abs(hash((feed, title)))}"),
            "published": now - timedelta(hours=hours_ago), "source": kw.get("source", "test"), "symbol": kw.get("symbol"), "fetched_at": now}


@pytest.fixture()
def news_rows():
    rows = [
        _row("media_et_markets", "Sensex falls 300 points as banks drag", 1, category="Indian market", source="The Economic Times (RSS)"),
        _row("media_mint_markets", "Sensex falls 300 points as banks drag", 2, category="Indian market", source="Mint (RSS)"),   # same story
        _row("media_et_commodities", "Gold slips on strong dollar", 30, category="Commodities & currency", source="The Economic Times (RSS)"),
        _row("rbi_press", "RBI keeps repo rate unchanged in monetary policy review", 5, category="Economy & RBI", source="Reserve Bank of India - press releases (RSS)"),
        _row("nse_announcements", "Sample Alpha Limited", 0.5, category="Quarterly results", symbol="SAMPLE-ALPHA",
             summary="Sample Alpha Limited has informed the Exchange about Financial Results for the quarter", source="NSE India - corporate announcements (RSS)"),
        _row("media_et_ipo", "Acme Ltd IPO likely to open next week, sources said", 4, category="IPO & corporate actions", source="The Economic Times (RSS)"),
        _row("yahoo_market", "Random blog says buy now", 1, category="Indian market", source="Some Unknown Blog via Yahoo Finance"),
    ]
    db.upsert(db.news_items, rows, ["feed", "url", "title"])
    yield rows
    with db.get_engine().begin() as conn:
        conn.execute(db.news_items.delete().where(db.news_items.c.url.like("https://x.test/%")))


def _titles(d):
    return [i["title"] for i in d["items"]]


def test_news_sections_and_dedupe(client, news_rows):
    m = client.get("/api/news/feed?section=market&days=7").json()
    assert _titles(m).count("Sensex falls 300 points as banks drag") == 1               # one story, not two
    item = next(i for i in m["items"] if i["title"].startswith("Sensex"))
    # the earliest publisher is kept as the original; the later copy is listed under "also reported by"
    assert item["publisher"] == "Mint" and item["also"] == ["The Economic Times"] and item["kind"] == "Media report"
    assert "Random blog says buy now" not in _titles(m) and m["hidden_unrated"] >= 1      # unrated hidden by default
    assert "Gold slips on strong dollar" in _titles(client.get("/api/news/feed?section=commodities&days=7").json())
    eco = client.get("/api/news/feed?section=economy&days=7").json()["items"]
    rbi = next(i for i in eco if i["title"].startswith("RBI keeps"))
    assert rbi["tier"] == "primary" and rbi["important"] is True and rbi["kind"] == "Official disclosure"
    res = client.get("/api/news/feed?section=results&days=7").json()["items"]
    filing = next(i for i in res if i["symbol"] == "SAMPLE-ALPHA")
    assert filing["summary"].startswith("Financial Results") and filing["published"] and filing["fetched_at"]   # publication and fetch times kept apart


def test_breaking_only_last_three_hours(client, news_rows):
    b = _titles(client.get("/api/news/feed?section=breaking&days=7").json())
    assert "Sensex falls 300 points as banks drag" in b
    assert "Gold slips on strong dollar" not in b and "RBI keeps repo rate unchanged in monetary policy review" not in b


def test_news_filters_and_tentative_flag(client, news_rows):
    d = client.get("/api/news/feed?section=ipo&days=7&q=acme").json()
    assert _titles(d) == ["Acme Ltd IPO likely to open next week, sources said"] and d["items"][0]["tentative"] is True
    s = client.get("/api/news/feed?section=market&days=7&source=Mint").json()
    assert all("Mint" in (i["publisher"] or i["source"]) for i in s["items"])
    assert client.get("/api/news/feed?section=nope").status_code == 404


def test_saved_articles_round_trip(client):
    body = {"url": "https://x.test/saved", "title": "Saved story", "source": "The Economic Times", "published": "2026-11-13T05:00:00"}
    assert client.post("/api/news/saved", json=body).json()["ok"]
    assert any(i["url"] == body["url"] for i in client.get("/api/news/saved").json()["items"])
    assert client.post("/api/news/saved", json={**body, "url": "javascript:alert(1)"}).status_code in (400, 422)
    client.delete("/api/news/saved", params={"url": body["url"]})
    assert not any(i["url"] == body["url"] for i in client.get("/api/news/saved").json()["items"])


def test_explain_separates_fact_from_guidance(client):
    e = client.post("/api/news/explain", json={"title": "Sample Alpha Limited", "category": "Quarterly results", "tier": "primary",
                                               "symbol": "SAMPLE-ALPHA", "source": "NSE India"}).json()
    assert e["status"].startswith("Confirmed") and "not a prediction" in e["note"] and e["factors"]
    m = client.post("/api/news/explain", json={"title": "Firm X may raise funds, sources said", "tier": "established", "source": "Mint"}).json()
    assert m["status"].startswith("Developing")


def test_daily_summary_is_fact_based(client, monkeypatch):
    import api.routes_market as RM
    monkeypatch.setattr(RM, "movers", lambda n=6: {"gainers": [], "losers": [], "active": [], "breadth": None, "universe": 0})
    monkeypatch.setattr(RM, "sectors", lambda: {"industries": []})
    s = client.get("/api/news/summary").json()
    assert s["headline"].startswith("NIFTY 50 fell 0.61%") and s["indices"][0]["label"] == "NIFTY 50" and s["sources"]


def test_dedupe_keeps_distinct_filings():
    base = {"summary": None, "url": None, "source": "NSE", "publisher": None, "tier": "primary", "published": "2026-11-13T05:00:00", "also": []}
    a = {**base, "title": "Tata Steel Limited", "summary": "Board meeting intimation"}
    b = {**base, "title": "Tata Steel Limited", "summary": "Credit rating update"}
    assert len(RN.dedupe([a, b])) == 2                                                     # same company, different filings


# ------------------------------------------------------------------ glossary covers every searchable concept
def test_glossary_includes_metric_guide(client):
    terms = {t["term"].lower() for t in client.get("/api/learn").json()["glossary"]}
    for c in RS._CONCEPTS:
        assert c["name"].lower() in terms or any(c["name"].lower() == a for a in terms), c["name"]
