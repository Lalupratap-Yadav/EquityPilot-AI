"""Tests for the v2.1 research-quality features: FCFE, margin of safety, historical multiple bands,
working-capital ratios, plain-English benchmark assessments, source tiers, industry policies and
the comparison extras. Hand-calculated where a number is involved."""
import os

import pandas as pd
import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from equitypilot import db  # noqa: E402
from equitypilot.analytics import ratios as R  # noqa: E402
from equitypilot.analytics import valuation as V  # noqa: E402
from equitypilot.content import metrics_guide as MG  # noqa: E402
from equitypilot.content.industries import INDUSTRIES  # noqa: E402
from equitypilot.content.policies import POLICIES  # noqa: E402
from equitypilot.data import source_tiers as ST  # noqa: E402
from tests.test_analytics import FD, make_fd  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------ valuation maths
def test_fcfe_hand_calculation():
    # Year 1: revenue 1,100; net profit 110; net reinvestment = capex 77 - D&A 55 + ΔNWC 10 = 32; FCFE = 78
    # TV = 78 × 1.04 / (0.12 - 0.04) = 1,014;  equity = 78/1.12 + 1,014/1.12 = 975 -> ₹97.50 per share
    r = V.run_fcfe(V.FCFEInputs(base_revenue=1000, growth_start=0.1, growth_end=0.1, net_margin=0.1, da_pct=0.05,
                                capex_pct=0.07, nwc_pct=0.1, debt_ratio=0.0, cost_of_equity=0.12, terminal_growth=0.04,
                                shares=10, years=1))
    assert r.projection.loc[1, "FCFE"] == pytest.approx(78)
    assert r.terminal_value == pytest.approx(1014)
    assert r.per_share == pytest.approx(97.5)


def test_fcfe_debt_funding_reduces_equity_reinvestment():
    base = dict(base_revenue=1000, growth_start=0.1, growth_end=0.1, net_margin=0.1, da_pct=0.05, capex_pct=0.07,
                nwc_pct=0.1, cost_of_equity=0.12, terminal_growth=0.04, shares=10, years=1)
    r = V.run_fcfe(V.FCFEInputs(debt_ratio=0.25, **base))
    assert r.projection.loc[1, "Equity-funded reinvestment"] == pytest.approx(32 * 0.75)
    assert r.projection.loc[1, "FCFE"] == pytest.approx(110 - 24)


def test_fcfe_rejects_bad_inputs():
    base = dict(base_revenue=1000, growth_start=0.1, growth_end=0.1, net_margin=0.1, da_pct=0.05, capex_pct=0.07,
                nwc_pct=0.1, debt_ratio=0.0, shares=10)
    with pytest.raises(V.DCFError):
        V.run_fcfe(V.FCFEInputs(cost_of_equity=0.05, terminal_growth=0.05, **base))
    with pytest.raises(V.DCFError):
        V.run_fcfe(V.FCFEInputs(cost_of_equity=0.12, terminal_growth=0.04, **{**base, "debt_ratio": 1.0}))


def test_margin_of_safety():
    assert V.margin_of_safety(100, 80) == pytest.approx(0.20)
    assert V.margin_of_safety(100, 125) == pytest.approx(-0.25)
    assert V.margin_of_safety(-10, 50) is None          # undefined for a non-positive estimate
    assert V.margin_of_safety(None, 50) is None


def test_multiple_bands_ignore_negative_and_missing():
    hist = [{"pe": 10, "pb": 2}, {"pe": 20, "pb": 4}, {"pe": None, "pb": 3}, {"pe": -5, "pb": None}]
    b = V.multiple_bands(hist, {"pe": 30, "pb": 3})
    assert b["pe"]["n"] == 2 and b["pe"]["median"] == 15 and b["pe"]["vs_median"] == pytest.approx(1.0)
    assert b["pb"]["median"] == 3 and b["pb"]["min"] == 2 and b["pb"]["max"] == 4
    assert V.multiple_bands([{"pe": 12, "pb": 1}], {"pe": 12})["pe"]["median"] is None   # one year is not a band


# ------------------------------------------------------------------ working capital
def test_working_capital_ratios():
    rt = R.compute_ratios(FD)
    y = rt.columns[-1]
    assert pd.isna(rt.loc["payable_days", y])                      # payables not reported -> blank, never zero
    assert pd.isna(rt.loc["cash_conversion_cycle", y])
    assert rt.loc["nwc_to_revenue", y] == pytest.approx((600 - 300) / 1200)
    fd = make_fd({**{k: FD.wide.loc[k].tolist() for k in FD.wide.index}, "payables": [60.0, 70.0]})
    rt2 = R.compute_ratios(fd)
    assert rt2.loc["payable_days", y] == pytest.approx(70 / 700 * 365)
    ccc = 150 / 1200 * 365 + 120 / 700 * 365 - 70 / 700 * 365
    assert rt2.loc["cash_conversion_cycle", y] == pytest.approx(ccc)


# ------------------------------------------------------------------ plain-English guide
def test_assessments_use_benchmarks_only_where_fair():
    assert MG.assess("roe", 0.20)["level"] == "strong"
    assert MG.assess("roe", 0.12)["level"] == "moderate"
    assert MG.assess("roe", 0.05)["level"] == "weak"
    assert MG.assess("interest_coverage", 1.2)["level"] == "weak"
    assert MG.assess("interest_coverage", -2)["level"] == "weak"
    assert MG.assess("debt_to_equity", 0.2)["level"] == "strong"
    assert MG.assess("pe", 50) is None                              # no universal 'good' P/E
    assert MG.assess("debt_to_equity", 8, financial=True) is None   # leverage benchmark meaningless for banks
    assert MG.assess("roa", 0.012, financial=True)["level"] == "strong"
    assert MG.assess("roa", 0.012) is None
    assert MG.assess("roe", None) is None and MG.assess("roe", float("nan")) is None


def test_guide_covers_every_ratio():
    missing = [k for k in R.RATIOS if k not in MG.GUIDE]
    assert not missing, missing
    for k, g in MG.GUIDE.items():
        assert all(g.get(f) for f in ("what", "why", "read", "example")), k


# ------------------------------------------------------------------ source tiers
@pytest.mark.parametrize("source,data_type,expected", [
    ("Reuters via Yahoo Finance", None, "established"),
    ("The Wall Street Journal", "third_party", "established"),
    ("Motley Fool via Yahoo Finance", None, "unrated"),
    ("Zacks", "third_party", "unrated"),
    ("NSE India - corporate announcements (RSS)", None, "primary"),
    ("Reserve Bank of India - press releases (RSS)", None, "primary"),
    ("Obsessed with BSE stocks blog", None, "unrated"),
    ("Sample dataset", "sample", "sample"),
    ("User entry", "user_entered", "user"),
    (None, None, "unrated"),
])
def test_source_tiers(source, data_type, expected):
    assert ST.tier(source, data_type) == expected


def test_unrated_headlines_hidden_by_default(client):
    now = db.utcnow()
    db.upsert(db.disclosures, [
        {"symbol": "SAMPLE-BETA", "date": now, "title": "Is this a multibagger? Tip site says yes", "category": "News",
         "publisher": "Random Stock Tips", "url": "https://example.com/tip", "source": "Yahoo Finance news aggregator",
         "data_type": "third_party", "fetched_at": now},
        {"symbol": "SAMPLE-BETA", "date": now, "title": "Beta Infotech wins contract", "category": "News",
         "publisher": "Reuters", "url": "https://example.com/reuters", "source": "Yahoo Finance news aggregator",
         "data_type": "third_party", "fetched_at": now},
    ], ["symbol", "title", "url"])
    r = client.get("/api/news?section=company&symbol=SAMPLE-BETA").json()
    titles = {i["title"]: i["tier"] for i in r["items"]}
    assert "Beta Infotech wins contract" in titles and titles["Beta Infotech wins contract"] == "established"
    assert "Is this a multibagger? Tip site says yes" not in titles and r["hidden_unrated"] >= 1
    r2 = client.get("/api/news?section=company&symbol=SAMPLE-BETA&include_unrated=true").json()
    assert any(i["tier"] == "unrated" for i in r2["items"])
    # the assistant's evidence never includes unrated publishers
    from equitypilot.ai import context as C
    text = C.build_context("SAMPLE-BETA", "latest news", include_news=True).render()
    assert "Tip site" not in text and "Beta Infotech wins contract" in text


# ------------------------------------------------------------------ API wiring
def test_valuation_api_returns_bands_fcfe_and_mos(client):
    v = client.get("/api/companies/SAMPLE-BETA/valuation").json()
    assert set(v["bands"]) == {"pe", "pb"} and "implied_from_history" in v
    assert v["fcfe_defaults"] and 0 <= v["fcfe_defaults"]["debt_ratio"] < 1
    body = {**v["dcf_defaults"], "fcfe": {**v["fcfe_defaults"], "cost_of_equity": 0.13}}
    r = client.post("/api/companies/SAMPLE-BETA/dcf", json=body).json()
    assert r["fcfe"]["per_share"] > 0 and len(r["fcfe"]["projection"]) == v["dcf_defaults"]["years"]
    assert r["margin_of_safety"] == pytest.approx((r["per_share"] - r["price"]) / r["per_share"])
    bad = client.post("/api/companies/SAMPLE-BETA/dcf", json={**body, "fcfe": {**v["fcfe_defaults"], "cost_of_equity": 0.01}}).json()
    assert "error" in bad["fcfe"]                                       # FCFE error does not break the FCFF result
    assert bad["per_share"] == pytest.approx(r["per_share"])


def test_financials_include_guide_and_assessment(client):
    d = client.get("/api/companies/SAMPLE-ALPHA/financials").json()
    roe = next(r for r in d["ratios"] if r["key"] == "roe")
    assert roe["guide"]["what"] and roe["assessment"]["level"] in ("strong", "moderate", "weak")
    q = client.get("/api/companies/SAMPLE-ALPHA/financials?period=quarterly").json()
    if not q.get("empty"):
        assert all(r["assessment"] is None for r in q["ratios"])         # quarterly ratios are not rated
    g = client.get("/api/learn/metrics").json()
    assert "pe" in g["guide"] and g["benchmark_note"]


def test_every_industry_has_policies_with_official_links(client):
    assert {i["id"] for i in INDUSTRIES} == set(POLICIES)
    for items in POLICIES.values():
        assert items and all(p["url"].startswith("https://") and p["body"] and p["what"] for p in items)
    d = client.get("/api/industries/banking").json()
    assert d["policies"] and d["policy_note"]


def test_compare_extras(client):
    d = client.get("/api/compare?symbols=SAMPLE-ALPHA,SAMPLE-GAMMA").json()
    assert {"return_1y", "promoter_pct"} <= set(d["metrics"])
    gamma = next(r for r in d["rows"] if r["symbol"] == "SAMPLE-GAMMA")
    assert isinstance(gamma["highlights"], list) and "industry_risks" in gamma
    for h in gamma["highlights"]:
        assert h["kind"] in ("strength", "watch") and h["text"]
