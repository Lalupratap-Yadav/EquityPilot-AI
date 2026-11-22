"""v2.6: company identification in news, Earnings & Results, Corporate Actions, Financial Health, Data Quality,
Virtual Invest corporate-action accounting, search ranking across the securities master, and privacy."""
from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import routes_news as RN
from api import routes_search as RS
from api.main import app
from equitypilot import db
from equitypilot.analytics import paper as P
from equitypilot.analytics import ratios as R
from equitypilot.data import entities as E
from equitypilot.data import events as EV
from equitypilot.data import repository as repo
from equitypilot.data import securities as S

REAL = {"TCS.NS": "Tata Consultancy Services Limited", "INFY.NS": "Infosys Limited", "WIPRO.NS": "Wipro Limited",
        "TECHM.NS": "Tech Mahindra Limited", "M&M.NS": "Mahindra & Mahindra Limited", "HDFCBANK.NS": "HDFC Bank Limited",
        "HDFCLIFE.NS": "HDFC Life Insurance Company Limited", "RELIANCE.NS": "Reliance Industries Limited",
        "RPOWER.NS": "Reliance Power Limited", "BAJFINANCE.NS": "Bajaj Finance Limited", "ITC.NS": "ITC Limited",
        "NESTLEIND.NS": "Nestle India Limited", "MARUTI.NS": "Maruti Suzuki India Limited", "LT.NS": "Larsen & Toubro Limited",
        "SBIN.NS": "State Bank of India", "TITAN.NS": "Titan Company Limited", "FEDERALBNK.NS": "The Federal Bank Limited",
        "LICI.NS": "Life Insurance Corporation of India", "HINDALCO.NS": "Hindalco Industries Limited"}


def _reset_caches():
    E.reset_cache()
    S._TRACKED["rows"] = None
    RN._LOAD_CACHE.clear()
    RS._CACHE.clear()
    EV._ROWS_CACHE.clear()


@pytest.fixture()
def real_companies():
    db.upsert(db.companies, [{"symbol": s, "name": n, "is_sample": False} for s, n in REAL.items()], ["symbol"])
    _reset_caches()
    yield
    with db.get_engine().begin() as conn:
        conn.execute(db.companies.delete().where(db.companies.c.symbol.in_(list(REAL))))
        conn.execute(db.disclosures.delete().where(db.disclosures.c.symbol.in_(list(REAL))))
        conn.execute(db.news_items.delete().where(db.news_items.c.source == "v26-test"))
    _reset_caches()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(RN, "_refresh_in_background", lambda: None)
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------ company identification
MATCHER_CASES = [
    ("Satya Nadella went from H-1B worker to Microsoft CEO. The Trump administration just shut that path", []),
    ("Trump administration freezes green cards for Microsoft, IT firms", []),
    ("TCS shares rise as AI revenue offsets sluggish growth", ["TCS.NS"]),
    ("Tech Mahindra Q2 profit jumps; Mahindra & Mahindra SUV sales climb", ["TECHM.NS", "M&M.NS"]),
    ("Mahindra group plans new EV plant", []),                                  # group word alone
    ("HDFC Life premium growth slows while HDFC Bank deposits rise", ["HDFCLIFE.NS", "HDFCBANK.NS"]),
    ("HDFC AMC inflows jump", []),                                              # a different listed entity
    ("Reliance Power, Reliance Infra shares hit upper circuit", ["RPOWER.NS"]),  # not Reliance Industries
    ("Bajaj Housing Finance IPO: Bajaj Finance to sell stake", ["BAJFINANCE.NS"]),
    ("ITC Hotels demerger record date fixed", []),
    ("DGFT changes export policy for battery scrap under ITC (HS) code 85491400", []),
    ("Nestle SA cuts outlook; Suzuki Motor plans EV launch", []),               # foreign parents
    ("Nestlé India Q2 results: profit up 5%", ["NESTLEIND.NS"]),
    ("Infosys's buyback opens; Wipro trades flat", ["INFY.NS", "WIPRO.NS"]),
    ("SBI Card shares slip; SBI raises FD rates", ["SBIN.NS"]),
    ("Jio Platforms IPO filing expected", ["RELIANCE.NS"]),                      # public-record subsidiary
    ("Tata group stocks rally", []),
    ("Investors switch to itc-like defensives", []),                            # lower case / inside a word
    ("L&T Finance Q2 net up 20%; L&T bags mega order", ["LT.NS"]),
    ("Federal Reserve holds rates", []),
    ("Titan submersible inquiry continues", []),
    ("LIC Housing Finance raises lending rates", []),
    ("Novelis files for IPO in the US", ["HINDALCO.NS"]),
    ("Kamarajar Port picks SBI Capital, IDBI Capital and ICICI Securities for IPO", []),   # advisers, not the companies
]


@pytest.mark.parametrize("text,expect", MATCHER_CASES)
def test_company_matcher_precision(text, expect):
    m = E.Matcher(REAL)
    assert [x.symbol for x in m.find(text)] == expect, text


def test_matcher_records_how_it_matched():
    m = E.Matcher(REAL)
    assert m.find("Jio Platforms IPO filing expected")[0].reason == "subsidiary"
    assert m.find("Jio Platforms IPO; RIL shares gain")[0].reason == "alias"          # a direct mention outranks it
    assert m.mentions("TCS.NS", "IT stocks fall", "Tata Consultancy Services led the decline") is not None
    assert m.mentions("TCS.NS", "IT stocks fall", "Infosys led the decline") is None


def test_company_news_excludes_headlines_that_do_not_name_the_company(client, real_companies):
    now = db.utcnow()
    db.upsert(db.disclosures, [
        {"symbol": "TCS.NS", "date": now - timedelta(hours=2), "title": "Trump administration freezes green cards for Microsoft, IT firms",
         "category": "News", "publisher": "Reuters", "url": "https://x.test/ms", "source": "Yahoo", "data_type": "third_party", "fetched_at": now},
        {"symbol": "TCS.NS", "date": now - timedelta(hours=3), "title": "TCS wins $1 billion deal from European bank",
         "category": "News", "publisher": "Reuters", "url": "https://x.test/tcs", "source": "Yahoo", "data_type": "third_party", "fetched_at": now}],
        ["symbol", "title", "url"])
    db.upsert(db.news_items, [{"feed": "media_et_stocks", "category": "Indian market", "title": "Infosys, Wipro shares rise after US deal wins",
                               "summary": None, "url": "https://x.test/infy", "published": now - timedelta(hours=1), "source": "v26-test",
                               "symbol": None, "fetched_at": now}], ["feed", "url", "title"])
    db.set_setting("company_news:TCS.NS", now.isoformat())                 # no provider call in the test
    db.set_setting("company_news:INFY.NS", now.isoformat())
    _reset_caches()
    tcs = client.get("/api/news/feed?section=company&symbol=TCS.NS&days=7").json()["items"]
    titles = [i["title"] for i in tcs]
    assert "TCS wins $1 billion deal from European bank" in titles
    assert not any("Microsoft" in t for t in titles)                       # the reported mis-tagging
    market = client.get("/api/news/feed?section=market&days=7&include_unrated=true").json()["items"]
    ms = [i for i in market if "Microsoft" in i["title"]]
    assert ms and ms[0]["symbol"] is None and ms[0]["symbols"] == []        # kept, but as general market news
    infy = client.get("/api/news/feed?section=company&symbol=INFY.NS&days=7").json()["items"]
    hit = [i for i in infy if i["title"].startswith("Infosys, Wipro")]
    assert hit and set(hit[0]["symbols"]) == {"INFY.NS", "WIPRO.NS"} and hit[0]["match"] == "Named in the headline"
    # the company's AI context / report helpers see only verified headlines too
    assert list(repo.get_disclosures("TCS.NS")["title"]) == ["TCS wins $1 billion deal from European bank"]


def test_provider_headlines_are_split_into_company_and_general(monkeypatch, real_companies):
    from equitypilot.data import yahoo
    now = db.utcnow()
    monkeypatch.setattr(yahoo, "fetch_news", lambda s: [
        {"symbol": s, "date": now, "title": "Infosys sees no material impact from U.S. PERM suspension", "category": "News", "publisher": "Investing.com",
         "url": "https://x.test/a", "summary": None, "source": "Yahoo", "data_type": "third_party", "fetched_at": now},
        {"symbol": s, "date": now, "title": "IT stocks slip on US visa worries", "category": "News", "publisher": "Mint", "url": "https://x.test/b",
         "summary": "Tata Consultancy Services and peers fell 2%.", "source": "Yahoo", "data_type": "third_party", "fetched_at": now}])
    ok, msg = repo.refresh_news("TCS.NS")
    assert ok and "1 headlines name the company" in msg
    d = repo.get_disclosures("TCS.NS")
    assert list(d["title"]) == ["IT stocks slip on US visa worries"] and d["data_type"].iloc[0] == "third_party_matched"
    gen = db.read_df(db.select(db.news_items).where(db.news_items.c.url == "https://x.test/a"))
    assert len(gen) == 1 and gen["symbol"].iloc[0] is None and gen["feed"].iloc[0] == "yahoo_market"
    with db.get_engine().begin() as conn:
        conn.execute(db.news_items.delete().where(db.news_items.c.url == "https://x.test/a"))


# ------------------------------------------------------------------ earnings & results, corporate actions
def _d(days: int) -> str:
    return (EV.today_ist() + timedelta(days=days)).strftime("%d-%b-%Y")


@pytest.fixture()
def events(real_companies):
    now = db.utcnow()
    T = "Tata Consultancy Services Limited"

    def row(feed, title, summary, url, cat=None, sym="TCS.NS", hours=1):
        return {"feed": feed, "category": cat, "title": title, "summary": summary, "url": url, "published": now - timedelta(hours=hours),
                "source": "v26-test", "symbol": sym, "fetched_at": now}
    db.upsert(db.news_items, [
        row("nse_board_meetings", T, f"To consider and approve the financial results for the quarter ended December 31, 2026 |Meeting Date: {_d(20)}", "https://x.test/bm1.pdf"),
        row("nse_announcements", T, f"{T} has informed the Exchange about Board Meeting to be held on {_d(20)} to inter-alia consider and approve the Unaudited "
            "Financial results of the Company for the Quarterly ended December 2026 . |SUBJECT: Board Meeting Intimation", "https://x.test/bm2.pdf", "Board meeting"),
        row("nse_board_meetings", "Infosys Limited", f"To consider buyback of equity shares |Meeting Date: {_d(5)}", "https://x.test/bm3.pdf", sym="INFY.NS"),
        row("nse_announcements", "Wipro Limited", "Wipro Limited has informed the Exchange regarding Outcome of Board Meeting held on 14-Nov-2026, the financial "
            "results for the period ended September 30, 2026. |SUBJECT: Outcome of Board Meeting", "https://x.test/r1.pdf", "Quarterly results", "WIPRO.NS"),
        row("nse_announcements", "Wipro Limited", "Wipro Limited has informed the Exchange about Delay in declaration of results |SUBJECT: Reasons for Delayed/Non-submission "
            "of Financial Results", "https://x.test/r2.pdf", "Quarterly results", "WIPRO.NS"),
        row("nse_corporate_actions", f"{T} - Ex-Date: {_d(3)}", f"SERIES:EQ |PURPOSE:INTERIM DIVIDEND - RS 11 PER SHARE |FACE VALUE:1 |RECORD DATE:{_d(3)} "
            "|BOOK CLOSURE START DATE:- |BOOK CLOSURE END DATE:-", "https://x.test/ca1"),
        row("nse_corporate_actions", f"Infosys Limited - Ex-Date: {_d(4)}", f"SERIES:EQ |PURPOSE:FACE VALUE SPLIT (SUB-DIVISION) - FROM RS 10/- PER SHARE TO RS 2/- PER SHARE "
            f"|FACE VALUE:10 |RECORD DATE:{_d(4)} |BOOK CLOSURE START DATE:- |BOOK CLOSURE END DATE:-", "https://x.test/ca2", sym="INFY.NS"),
        row("nse_corporate_actions", f"Wipro Limited - Ex-Date: {_d(6)}", f"SERIES:EQ |PURPOSE:BONUS 1:1 |FACE VALUE:2 |RECORD DATE:{_d(6)} |BOOK CLOSURE START DATE:- |BOOK CLOSURE END DATE:-",
            "https://x.test/ca3", sym="WIPRO.NS"),
        row("nse_corporate_actions", f"Some Finance Limited - Ex-Date: {_d(2)}", f"SERIES:N1 |PURPOSE:INTEREST PAYMENT |FACE VALUE:1000 |RECORD DATE:{_d(2)} "
            "|BOOK CLOSURE START DATE:- |BOOK CLOSURE END DATE:-", "https://x.test/ca4", sym=None),
        row("nse_corporate_actions", f"{T} - Ex-Date: {_d(-30)}", f"SERIES:EQ |PURPOSE:FINAL DIVIDEND - RS 30 PER SHARE |FACE VALUE:1 |RECORD DATE:{_d(-30)} "
            "|BOOK CLOSURE START DATE:- |BOOK CLOSURE END DATE:-", "https://x.test/ca5"),
    ], ["feed", "url", "title"])
    EV._ROWS_CACHE.clear()
    yield


def test_results_calendar_uses_only_stated_dates_and_merges_filings(client, events):
    d = client.get("/api/events/results?view=upcoming").json()
    tcs = [e for e in d["items"] if e["symbol"] == "TCS.NS"]
    assert len(tcs) == 1                                                       # feed + announcement = one meeting
    e = tcs[0]
    assert e["meeting_date"] == (EV.today_ist() + timedelta(days=20)).isoformat() and e["state"] == "upcoming"
    assert len(e["sources"]) == 2 and e["results"] and e["status"] == "confirmed"
    assert e["period"] and "December" in e["period"]
    assert not any(x["symbol"] == "INFY.NS" for x in d["items"])                # a buyback meeting is not a result date
    assert any("never estimates" in n for n in d["notes"])
    recent = client.get("/api/events/results?view=recent&q=wipro").json()["items"]
    assert {r["kind"] for r in recent} == {"results", "delay"}
    assert all(r["url"].startswith("https://x.test/") for r in recent)
    assert client.get("/api/events/results?start=2026-13-01").status_code == 400
    assert client.get("/api/events/results?view=nonsense").status_code == 422
    assert client.get("/api/events/results?industry=not-an-industry").status_code == 400


def test_corporate_actions_classification_and_dates(client, events):
    d = client.get("/api/events/actions?when=upcoming").json()
    by = {a["company"]: a for a in d["items"]}
    div = by["Tata Consultancy Services Limited"]
    assert div["type"] == "dividend" and div["amount"] == 11.0 and div["record_date"] and div["payment_date"] is None and div["tier"] == "OFFICIAL"
    split = by["Infosys Limited"]
    assert split["type"] == "split" and split["amount"] is None and "each share becomes 5" in split["ratio"]
    assert by["Wipro Limited"]["type"] == "bonus" and by["Wipro Limited"]["ratio"] == "1:1"
    assert "Some Finance Limited" not in by                                    # debt interest is not an equity action
    assert all(a["ex_date"] >= d["today"] for a in d["items"])
    only_div = client.get("/api/events/actions?when=upcoming&type=dividend").json()["items"]
    assert only_div and all(a["type"] == "dividend" for a in only_div)
    past = client.get("/api/events/actions?when=past&q=tata").json()["items"]
    assert past and past[0]["amount"] == 30.0 and past[0]["ex_date"] < d["today"]
    assert set(d["types"]) >= {"dividend", "split", "bonus", "rights", "buyback", "merger"} and all(v["explain"] for v in d["types"].values())
    assert client.get("/api/events/actions?type=nonsense").status_code == 400
    ev = client.get("/api/events/company/TCS.NS").json()
    assert ev["board_meetings"] and any(a["amount"] == 11.0 for a in ev["actions"])
    assert client.get("/api/events/company/NOPE.NS").status_code == 404


# ------------------------------------------------------------------ financial health, EPS checks, coverage, quality
def test_health_shows_metrics_formulas_and_never_scores_missing_data(client):
    h = client.get("/api/companies/SAMPLE-ALPHA/health").json()
    keys = [a["key"] for a in h["areas"]]
    assert keys == ["growth", "profitability", "debt", "liquidity", "cash_flow", "efficiency", "valuation"]
    for a in h["areas"]:
        assert a["status"] in ("strong", "adequate", "weak", "insufficient", "context")
        for m in a["metrics"]:
            assert m["formula"] or m["key"] in ("pe", "pb")
            if m["missing"]:
                assert m["value"] is None and not m["rated"]                  # missing is never zero, never rated
    assert next(a for a in h["areas"] if a["key"] == "valuation")["status"] in ("context", "insufficient")
    assert any("no overall company score" in m.lower() for m in h["method"])
    bank = client.get("/api/companies/SAMPLE-EPSILON/health").json()
    assert bank["is_financial"]
    st = {a["key"]: a["status"] for a in bank["areas"]}
    assert st["debt"] == "not_applicable" and st["cash_flow"] == "not_applicable" and "asset_quality" in st and "capital" in st


def test_health_area_without_data_is_insufficient():
    from equitypilot.analytics import health as H
    a = H._area("debt", "Debt", "q", [H._metric("debt_to_equity", None, "FY2026", False)])
    assert a["status"] == "insufficient" and a["points"] is None
    b = H._area("debt", "Debt", "q", [H._metric("debt_to_equity", 0.2, "FY2026", False), H._metric("interest_coverage", 1.0, "FY2026", False)])
    assert b["status"] == "adequate" and b["points"] == 1.0                 # strong (2) + weak (0) -> 1.0


def test_eps_checks_flag_swapped_basic_and_diluted():
    wide = pd.DataFrame({pd.Timestamp("2025-03-31"): {"eps_basic": 44.5, "eps_diluted": 88.7, "net_income": 100.0, "shares_diluted": 1.13},
                         pd.Timestamp("2026-03-31"): {"eps_basic": 90.0, "eps_diluted": 89.0, "net_income": 100.0, "shares_diluted": 1.12}})
    fd = repo.FinancialData(wide=wide, period_type="annual", basis="")
    checks = R.eps_checks(fd)
    assert any(c["level"] == "warning" and "Mar 2025" in c["check"] for c in checks)
    assert not any(c["level"] == "warning" and "Mar 2026" in c["check"] for c in checks)


def test_coverage_and_data_quality(client):
    c = client.get("/api/companies/SAMPLE-ALPHA/coverage").json()
    assert c["applicable"] >= 6 and all(i["tier"] == "SAMPLE" for i in c["items"] if i["applicable"])
    assert all(i["state"] in ("fresh", "ageing", "stale", "missing", "not_applicable") for i in c["items"])
    q = client.get("/api/data/quality").json()
    assert set(q["labels"]) == {"OFFICIAL", "SECONDARY", "THIRD-PARTY", "DELAYED", "HISTORICAL", "CALCULATED", "ASSUMPTION", "SAMPLE", "USER-ENTERED"}
    keys = {f["key"] for f in q["feeds"]}
    assert {"nse_board_meetings", "nse_corporate_actions", "nse_announcements", "rbi_press", "sebi"} <= keys
    assert all(f["tier"] in ("OFFICIAL", "SECONDARY", "THIRD-PARTY") for f in q["feeds"])
    assert q["market_data"]["tier"] in ("DELAYED", "OFFICIAL") and q["offline"] is True


# ------------------------------------------------------------------ virtual invest: corporate actions without double counting
def test_split_factor_after():
    sp = pd.DataFrame([{"date": date(2026, 1, 10), "value": 2.0}, {"date": date(2026, 6, 1), "value": 5.0}])
    assert P.split_factor_after(sp, date(2025, 12, 1)) == 10.0
    assert P.split_factor_after(sp, date(2026, 1, 10)) == 5.0                 # a split on the same day is not "after"
    assert P.split_factor_after(sp, date(2026, 7, 1)) == 1.0
    assert P.split_factor_after(pd.DataFrame(), date(2026, 7, 1)) == 1.0


def test_performance_has_no_jump_on_a_split():
    with TestClient(app) as c:
        uid = c.get("/api/me").json()["user"]["id"]
        price = c.get("/api/quotes?symbols=SAMPLE-GAMMA").json()["quotes"]["SAMPLE-GAMMA"]["price"]
        qty = int(800_000 // price)                              # most of the account, so a valuation error would show clearly
        assert c.post("/api/invest/orders", json={"symbol": "SAMPLE-GAMMA", "side": "BUY", "qty": qty}).status_code == 200
        px = repo.get_prices("SAMPLE-GAMMA", auto_refresh=False).sort_values("date")
        days = pd.bdate_range(end=pd.Timestamp.now().normalize() - pd.Timedelta(days=1), periods=12)
        start, split_day = days[0], days[6]
        db.execute(db.update(db.paper_accounts).where(db.paper_accounts.c.user_id == uid).values(started_at=start.to_pydatetime()))
        db.execute(db.update(db.paper_trades).where(db.paper_trades.c.user_id == uid).values(ts=(start + pd.Timedelta(hours=5)).to_pydatetime()))
        db.upsert(db.corporate_actions, [{"symbol": "SAMPLE-GAMMA", "date": split_day.date(), "type": "split", "value": 2.0, "source": "test"}],
                  ["symbol", "date", "type"])
        try:
            P.apply_corporate_actions(uid)
            perf = P.performance(uid).set_index("date")["portfolio"]
            before, after = perf[days[5]], perf[split_day]
            closes = px.set_index(pd.to_datetime(px["date"]))["close"]
            move = abs(float(closes[closes.index <= split_day].iloc[-1]) / float(closes[closes.index <= days[5]].iloc[-1]) - 1)
            # the provider's history is split-adjusted, so without the fix the holding would look half its value before the split
            assert abs(after / before - 1) <= move + 0.02
        finally:
            db.execute(db.delete(db.corporate_actions).where(db.corporate_actions.c.source == "test"))


def test_leaderboard_reveals_no_holdings_or_trades():
    for row in P.leaderboard():
        assert set(row) == {"display_name", "total_return", "since"}


# ------------------------------------------------------------------ search across the securities master
@pytest.fixture()
def securities_rows():
    rows = [
        {"isin": "INE745G01035", "name": "Multi Commodity Exchange of India Ltd", "nse_symbol": None, "bse_symbol": "MCX", "category": "Mid Cap",
         "mcap_rank": 180, "source": "AMFI"},
        {"isin": "INE745G01043", "name": "Multi Commodity Exchange of India Limited", "nse_symbol": "MCX", "bse_symbol": None, "category": None,
         "mcap_rank": None, "source": "NSE"},
        {"isin": "INE615R01029", "name": "TruCap Finance Limited", "nse_symbol": "TRU", "bse_symbol": "TRU", "category": "Small Cap", "mcap_rank": 4000, "source": "NSE"},
        {"isin": "INE976A01021", "name": "West Coast Paper Mills Limited", "nse_symbol": "WSTCSTPAPR", "bse_symbol": None, "category": "Small Cap",
         "mcap_rank": 900, "source": "NSE"},
    ] + [{"isin": f"INE9{i:05d}A01011", "name": f"Structural Infrastructure Trust {i} Limited", "nse_symbol": f"STRU{i}", "bse_symbol": None,
          "category": "Small Cap", "mcap_rank": 1000 + i, "source": "test"} for i in range(70)]
    db.upsert(db.securities, rows, ["isin"])
    yield
    with db.get_engine().begin() as conn:
        conn.execute(db.securities.delete().where(db.securities.c.isin.in_([r["isin"] for r in rows])))


def test_search_exact_symbol_never_lost_and_isin_changes_merged(securities_rows, real_companies):
    assert S.search("TRU", 5)[0]["symbol"] == "TRU.NS"                        # 70+ names contain "tru"
    mcx = S.search("MCX", 5)
    assert [r["symbol"] for r in mcx].count("MCX.NS") == 1 and not any(r["symbol"] == "MCX.BO" for r in mcx)
    assert mcx[0]["category"] == "Mid Cap"                                    # carried over from the AMFI row
    assert "WSTCSTPAPR.NS" not in [r["symbol"] for r in S.search("tcs", 5)]   # no padding with mid-word matches
    assert S.search("l&t", 3)[0]["symbol"] == "LT.NS" and S.search("ril", 3)[0]["symbol"] == "RELIANCE.NS"
    assert S.search("INE615R01029", 3)[0]["symbol"] == "TRU.NS"


def test_search_lists_new_research_tools(client):
    for q, to in (("earnings calendar", "/earnings"), ("record date", "/corporate-actions"), ("data quality", "/data-quality")):
        d = client.get("/api/search", params={"q": q}).json()
        assert any(t["to"] == to for t in d["tools"]), q


# ------------------------------------------------------------------ privacy: one user never sees another's data
def test_private_data_is_isolated_between_users():
    with TestClient(app) as a, TestClient(app) as b:
        assert a.post("/api/invest/orders", json={"symbol": "SAMPLE-ALPHA", "side": "BUY", "qty": 3}).status_code == 200
        assert a.post("/api/news/saved", json={"url": "https://x.test/saved", "title": "Saved by A"}).status_code == 200
        assert a.post("/api/alerts", json={"symbol": "SAMPLE-BETA", "direction": "above", "price": 1e9}).status_code == 200
        assert a.post("/api/portfolio/lots", json={"symbol": "SAMPLE-ALPHA", "quantity": 5, "avg_cost": 100, "buy_date": "2026-01-05"}).status_code == 200
        sa, sb = a.get("/api/invest/summary").json(), b.get("/api/invest/summary").json()
        assert sa["holdings"] and sb["holdings"] == [] and sb["cash"] == P.INITIAL_CASH
        assert a.get("/api/invest/trades").json() and b.get("/api/invest/trades").json() == []
        assert b.get("/api/news/saved").json()["items"] == []
        assert b.get("/api/alerts").json() == []
        assert a.get("/api/portfolio").json()["lots"] and b.get("/api/portfolio").json()["lots"] == []
        exp_b = b.get("/api/me/export").json()
        assert "Saved by A" not in str(exp_b) and "SAMPLE-ALPHA" not in str(exp_b.get("paper_trades", ""))
