"""Learning Centre v2.8: curriculum completeness, the nine-part lesson format, quiz quality, formula checks against
calc.py, glossary, links to tools and official sources, progress (private per user), case studies and the assistant's
learning mode."""
import json
import os
import re
from pathlib import Path

import pytest

os.environ["EQUITYPILOT_NO_WARMER"] = "1"
from fastapi.testclient import TestClient  # noqa: E402

from api import assistant as A  # noqa: E402
from api.main import app  # noqa: E402
from equitypilot.ai import learning as LRN  # noqa: E402
from equitypilot.content import curriculum as CU  # noqa: E402
from equitypilot.content.curriculum import calc as K  # noqa: E402
from equitypilot.content.curriculum import progress as PR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Every test client shares one address, so the assistant's per-minute limit would otherwise carry over into the
    assistant tests that run after this file."""
    from api.core import LIMITER
    yield
    with LIMITER.lock:
        LIMITER.hits.clear()


# ------------------------------------------------------------------ structure and coverage
def test_levels_modules_and_lessons():
    assert [lv["id"] for lv in CU.LEVELS] == ["beginner", "intermediate", "advanced"]
    by_level = {lv["id"]: [m for m in CU.MODULES if m["level"] == lv["id"]] for lv in CU.LEVELS}
    assert all(len(v) >= 3 for v in by_level.values())
    assert len(CU.MODULES) == 13 and len(CU.LESSONS) >= 50
    assert len(set(CU.LESSONS)) == len(CU.ORDER)
    # previous / next links walk the whole curriculum in order
    assert CU.LESSONS[CU.ORDER[0]]["prev"] is None and CU.LESSONS[CU.ORDER[-1]]["next"] is None
    for a, b in zip(CU.ORDER, CU.ORDER[1:]):
        assert CU.LESSONS[a]["next"] == b and CU.LESSONS[b]["prev"] == a


@pytest.mark.parametrize("lid", sorted(CU.LESSONS))
def test_every_lesson_has_the_nine_parts(lid):
    les = CU.LESSONS[lid]
    for part in ("concept", "why", "example", "interpret", "application"):
        assert len(les[part].split()) >= 12, (lid, part)
    assert les["formulas"] or les["rules"], lid                      # 3. formula or key rules
    assert len(les["mistakes"]) >= 3 and len(les["revision"]) >= 3, lid
    assert len(les["check"]) >= 2, lid                                # 9. knowledge check
    assert 3 <= les["minutes"] <= 8, lid
    assert les["summary"]


# every topic area of the brief (A-I) is taught: each concept has a glossary entry linked to a lesson
REQUIRED = {
    "A fundamentals": ["Time value of money", "Simple interest", "Compound interest", "Inflation", "Real return", "GDP", "Repo rate",
                       "Monetary policy", "Fiscal deficit", "Risk premium", "Expected return"],
    "B Indian market": ["SEBI", "Stock exchange", "Primary market", "Secondary market", "IPO", "Equity share", "NIFTY 50", "SENSEX",
                        "Demat account", "Trading account", "Depository", "Stock broker", "Market order", "Limit order", "Stop-loss order",
                        "Settlement", "Price band", "Market-wide circuit breaker", "Dividend", "Bonus issue", "Stock split", "Buyback", "Rights issue"],
    "C statements": ["Revenue", "EBITDA", "EBIT", "PAT", "EPS", "Cash flow from operations", "Free cash flow", "Working capital", "Goodwill",
                     "Depreciation", "Capital expenditure", "Retained earnings", "Three-statement link"],
    "D ratios": ["P/E ratio", "P/B ratio", "EV/EBITDA", "PEG ratio", "ROE", "ROCE", "ROA", "Debt to equity", "Interest coverage",
                 "Current ratio", "Quick ratio", "Gross margin", "Operating margin", "Net margin", "Dividend yield", "Asset turnover", "Net interest margin"],
    "E valuation": ["Market capitalisation", "Intrinsic value", "Present value", "DCF", "FCFF", "FCFE", "WACC", "Terminal value",
                    "Terminal growth", "Relative valuation", "Margin of safety", "Sensitivity analysis", "Scenario analysis", "Enterprise value"],
    "F products": ["Mutual fund", "Index fund", "ETF", "Bond", "Government security", "Fixed deposit", "REIT", "InvIT", "Option",
                   "Futures", "Commodity derivatives", "Currency derivatives"],
    "G technicals": ["Candlestick", "Support and resistance", "Trendline", "Moving average", "RSI", "MACD", "Bollinger Bands",
                     "Trading volume", "Volatility"],
    "H portfolio": ["Diversification", "Asset allocation", "Systematic and unsystematic risk", "Beta", "Standard deviation", "Sharpe ratio",
                    "Treynor ratio", "Jensen's alpha", "Maximum drawdown", "Correlation", "Risk-adjusted return", "Position sizing", "Investment horizon"],
    "I protection": ["Insider trading", "Front-running", "Pump and dump", "Market manipulation", "Ponzi scheme", "Stock broker", "SCORES",
                     "SMART ODR", "Investor Protection Fund", "KYC", "Investment adviser"],
}


@pytest.mark.parametrize("area", sorted(REQUIRED))
def test_curriculum_covers_every_area(area):
    for name in REQUIRED[area]:
        e = CU.GLOSSARY_ENTRIES.get(name)
        assert e, (area, name)
        assert e["lessons"], (area, name, "no lesson teaches it")


def test_ratio_cards_cover_meaning_formula_limits_and_unsuitable_cases():
    keys = {k for les in CU.LESSONS.values() for k in les["cards"]}
    for k in ("pe", "pb", "ev_ebitda", "peg", "roe", "roce", "roa", "eps", "debt_to_equity", "interest_coverage", "current_ratio",
              "quick_ratio", "gross_margin", "ebit_margin", "net_margin", "dividend_yield", "asset_turnover"):
        assert k in keys, k
        card = CU.ratio_card(k)
        for f in ("what", "why", "read", "example", "formula", "limits", "unsuitable"):
            assert card[f], (k, f)


# ------------------------------------------------------------------ questions
LEVELS, KINDS = {"easy", "medium", "hard"}, {"concept", "numerical", "statement", "case", "rule"}


def test_question_bank_quality():
    assert len(CU.QUESTIONS) >= 200
    for qid, q in CU.QUESTIONS.items():
        assert q["level"] in LEVELS and q["kind"] in KINDS, qid
        assert len(q["q"]) > 15 and len(q["explain"]) > 10, qid
        if q["type"] == "mcq":
            opts = q["options"]
            assert len(opts) == 4 and len(set(o.lower() for o in opts)) == 4, qid        # no duplicate (ambiguous) options
            assert 0 <= q["answer"] < 4, qid
            assert q["wrong"][q["answer"]] is None, qid
            assert all(q["wrong"][i] for i in range(4) if i != q["answer"]), (qid, "every wrong option needs a reason")
        else:
            assert q["steps"] and q["tolerance"] > 0, qid
            assert abs(q["answer"]) > q["tolerance"] or q["answer"] == 0, qid


def test_tests_mix_levels_and_question_types():
    for m in CU.MODULES:
        test = m["test"]
        assert len(test) >= 8, m["id"]
        assert len({q["level"] for q in test}) >= 2, m["id"]
        types = {q["kind"] for q in test} | {q["type"] for q in test}
        assert types & {"numerical", "num", "statement", "case"}, m["id"]
    kinds = {q["kind"] for q in CU.QUESTIONS.values()}
    assert kinds == KINDS


def _scaled(spec: dict) -> float:
    res = getattr(K, spec["fn"])(*spec["args"])
    if spec["pick"] is not None:
        res = res[spec["pick"]]
    return res * 100 if spec["unit"] == "%" else res


def _numbers(text: str) -> list[float]:
    return [float(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*\.?\d*", text)]


VERIFIED = [qid for qid, q in CU.QUESTIONS.items() if q.get("verify")]


@pytest.mark.parametrize("qid", VERIFIED)
def test_numeric_answers_match_the_formulas(qid):
    q = CU.QUESTIONS[qid]
    spec = q["verify"]
    value = _scaled(spec)
    if q["type"] == "num":
        if spec["expect"] is not None:                     # verifies an intermediate step shown in the working
            assert abs(value - spec["expect"]) <= max(0.011, abs(spec["expect"]) * 0.002), (qid, value)
            assert any(abs(n - spec["expect"]) < 0.011 for n in _numbers(q["steps"])), (qid, "step not shown")
        else:
            assert abs(q["answer"] - value) <= q["tolerance"], (qid, value, q["answer"])
    else:
        expect = spec["expect"]
        assert expect is not None, qid
        assert abs(value - expect) <= max(0.011, abs(expect) * 0.006), (qid, value, expect)
        nums = _numbers(q["options"][q["answer"]]) + _numbers(q["explain"])
        assert any(abs(n - expect) <= max(0.011, abs(expect) * 0.006) for n in nums), (qid, nums)


def test_enough_numerical_questions_are_machine_checked():
    nums = [q for q in CU.QUESTIONS.values() if q["type"] == "num"]
    assert len(VERIFIED) >= 50 and len(nums) >= 60


def test_calc_formulas_by_hand():
    assert round(K.fv(10_000, 0.08, 3)) == 12_597 and round(K.pv(121_000, 0.10, 2)) == 100_000
    assert round(K.effective_rate(0.12, 12), 4) == 0.1268 and round(K.real_return(0.07, 0.05), 4) == 0.019
    assert K.terp(4, 100, 1, 80) == 96 and round(K.approx_ytm(80, 1000, 950, 5), 4) == 0.0923
    d = K.dcf(100, 0.10, 5, 0.12, 0.05, net_debt=200, shares=10)
    assert round(d["enterprise_value"], 1) == 1844.6 and round(d["per_share"], 2) == 164.46 and round(d["terminal_share"], 2) == 0.74
    with pytest.raises(ValueError):
        K.gordon(100, 0.05, 0.06)
    assert round(K.two_asset_sd(0.5, 0.2, 0.2, 0.3), 4) == 0.1612 and K.position_size(1_000_000, 0.01, 500, 460) == 250
    assert round(K.wacc(0.136, 0.09, 0.25, 0.8), 4) == 0.1223 and round(K.capm(0.07, 1.2, 0.06), 3) == 0.142


def test_worked_examples_in_lessons_are_consistent():
    """Spot-check the headline numbers printed in lesson examples against the formulas."""
    ex = {les["id"]: les["example"] for les in CU.LESSONS.values()}
    assert "12,597" in ex["money-tvm"] and "1,53,862" in ex["money-interest"] and "55,839" in ex["money-inflation"]
    assert "₹96" in ex["corporate-buyback-rights"] and "10.53" in ex["corporate-buyback-rights"]
    assert "9.23%" in ex["products-bonds"] and "164.5" in ex["dcf-build"] and "12.23%" in ex["dcf-wacc"]
    assert "1,022.5" in ex["statements-linked"]                    # the linked statements balance
    table = re.findall(r"\| (1[1-3])% \| ([\d.]+) \| \**([\d.]+)\** \| ([\d.]+) \|", ex["dcf-sensitivity"])
    assert len(table) == 3
    for w, *vals in table:
        for g, v in zip((0.04, 0.05, 0.06), vals):
            assert abs(K.dcf(100, 0.10, 5, int(w) / 100, g, 200, 10)["per_share"] - float(v)) < 0.06, (w, g, v)


# ------------------------------------------------------------------ regulation, sources and tool links
OFFICIAL = ("sebi.gov.in", "nseindia.com", "bseindia.com", "nsdl.co.in", "cdslindia.com", "rbi.org.in", "rbiretaildirect.org.in",
            "amfiindia.com", "nism.ac.in", "mospi.gov.in", "indiabudget.gov.in", "mca.gov.in", "dicgc.org.in", "iepf.gov.in",
            "smartodr.in", "cybercrime.gov.in", "mha.gov.in")


def test_sources_are_official_and_dated():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", CU.REVIEWED)
    for key, s in CU.SOURCES.items():
        host = re.match(r"https://([^/]+)/", s["url"]).group(1)
        assert any(host == d or host.endswith("." + d) for d in OFFICIAL), (key, host)
    for les in CU.LESSONS.values():
        assert all(k in CU.SOURCES for k in les["sources"]), les["id"]
    for mid in ("protection", "markets"):
        assert all(les["sources"] for les in CU.MODULE_BY_ID[mid]["lessons"]), mid      # regulatory lessons cite sources


def test_regulatory_facts_match_the_checked_sources():
    text = json.dumps([CU.LESSONS[x] for x in ("protection-grievance", "protection-sebi", "markets-settlement", "products-bonds", "products-reits")],
                      ensure_ascii=False)
    for fact in ("21 calendar days", "15 calendar days", "10 calendar days", "SEBI Act, 1992", "T+1", "₹5 lakh per depositor per bank",
                 "at least 90%", "smartodr.in", "scores.sebi.gov.in"):
        assert fact in text, fact
    # rules that change are presented with a pointer to the current official version, not as timeless facts
    rates = CU.LESSONS["economy-rates"]
    assert any("check RBI" in r for r in rates["rules"])
    assert "regulations have been amended" in " ".join(CU.LESSONS["analysis-process"]["rules"])


def _app_routes() -> list[str]:
    src = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
    return re.findall(r'<Route path="([^"]+)"', src)


def test_tool_links_point_to_real_pages():
    routes = _app_routes()
    patterns = [re.compile("^/" + re.sub(r":\w+", r"[^/]+", r) + "$") for r in routes if r != "*"]
    for les in CU.LESSONS.values():
        for t in les["tools"]:
            assert any(p.match(t["to"]) for p in patterns), (les["id"], t["to"])
            if t["tool"] == "company":
                assert re.fullmatch(r"/company/[A-Z&-]+\.NS", t["to"]), t["to"]
        assert all(c in CU.CALCULATORS for c in les["calculators"]), les["id"]
    calc_ts = (ROOT / "web" / "src" / "pages" / "learn" / "Calculators.tsx").read_text(encoding="utf-8")
    for cid in CU.CALCULATORS:
        assert f"'{cid}'" in calc_ts or f" {cid}:" in calc_ts or f"{cid}: " in calc_ts, cid


def test_no_advice_journal_or_thesis_tracker():
    text = json.dumps(CU.MODULES).lower()
    for banned in ("investment journal", "thesis tracker", "you should buy", "we recommend", "guaranteed return of", "target price of"):
        assert banned not in text, banned
    assert all("not company data" in les["example"].lower() or les["id"] in NON_NUMERIC_EXAMPLES or "real data" in les["example"].lower()
               for les in CU.LESSONS.values() if re.search(r"₹\s?\d", les["example"]))


NON_NUMERIC_EXAMPLES = {"markets-structure", "markets-accounts", "protection-sebi", "protection-misconduct", "protection-fraud",
                        "protection-grievance", "analysis-process", "analysis-quality", "technical-charts"}


# ------------------------------------------------------------------ glossary
def test_glossary_entries_and_cross_links():
    assert CU.UNRESOLVED_TERMS == []
    g = CU.glossary()
    assert len(g) >= 200
    names = {e["term"] for e in g}
    seen_alias: dict[str, str] = {}
    for e in g:
        assert e["definition"] and e["letter"].isalpha() or e["letter"] == "#"
        assert all(r in names for r in e["related"]), e["term"]
        for a in e["aliases"]:
            assert a not in seen_alias, (a, e["term"], seen_alias.get(a))
            seen_alias[a] = e["term"]
        for les in e["lessons"]:
            assert les["id"] in CU.LESSONS
    assert CU.find_term("explain the repo rate") == "Repo rate" and CU.find_term("what is bvps") == "Book value per share"
    assert CU.find_terms("difference between ROE and ROCE") == ["ROE", "ROCE"]


def test_search_finds_new_learning_terms(client):
    d = client.get("/api/search", params={"q": "SCORES complaint"}).json()
    assert any(c["name"] == "SCORES" and c["to"].startswith("/learn?tab=glossary&term=") for c in d["concepts"])
    d = client.get("/api/search", params={"q": "repo rate"}).json()
    assert d["concepts"] and d["concepts"][0]["name"] == "Repo rate"


# ------------------------------------------------------------------ API and progress
def test_learn_overview_and_module_endpoints(client):
    d = client.get("/api/learn").json()
    assert [lv["id"] for lv in d["levels"]] == ["beginner", "intermediate", "advanced"]
    assert d["counts"]["lessons"] == len(CU.LESSONS) and d["reviewed"] == CU.REVIEWED
    card = d["levels"][0]["modules"][0]
    assert {"id", "title", "level", "summary", "minutes", "lessons", "questions"} <= set(card)
    assert "concept" not in card["lessons"][0]                       # the overview stays light; lessons load per module
    assert d["progress"]["lessons_done"] == 0 and d["progress"]["continue"] == CU.ORDER[0]
    m = client.get("/api/learn/modules/ratios").json()
    assert m["lessons"][0]["concept"] and m["lessons"][0]["cards"] and "verify" not in json.dumps(m)
    assert client.get("/api/learn/modules/risk").json()["id"] == "portfolio"           # links from the earlier Learning Centre
    assert client.get("/api/learn/modules/nope").status_code == 404
    les = client.get("/api/learn/lessons/protection-grievance").json()["lesson"]
    assert les["sources"][0]["url"].startswith("https://") and les["terms"]


def test_quiz_endpoints(client):
    assert len(client.get("/api/learn/quiz/money-tvm").json()["questions"]) == 2
    assert len(client.get("/api/learn/quiz/dcf").json()["questions"]) == len(CU.MODULE_BY_ID["dcf"]["test"])
    a = client.get("/api/learn/quiz/revision", params={"modules": "money,markets", "n": 10, "seed": 7}).json()["questions"]
    b = client.get("/api/learn/quiz/revision", params={"modules": "money,markets", "n": 10, "seed": 7}).json()["questions"]
    assert len(a) == 10 and [q["id"] for q in a] == [q["id"] for q in b]
    assert {q["source"]["module"] for q in a} == {"money", "markets"}
    assert client.get("/api/learn/quiz/unknown").status_code == 404


def test_progress_records_lessons_quizzes_and_recent(client):
    p = client.post("/api/learn/progress", json={"viewed": "money-interest"}).json()
    assert p["recent"][0] == "money-interest" and p["continue"] == "money-interest"
    p = client.post("/api/learn/progress", json={"lesson": "money-interest", "done": True}).json()
    assert "money-interest" in p["lessons"] and p["lessons_done"] == 1 and p["continue"] == "money-tvm"
    p = client.post("/api/learn/progress", json={"quiz": "money", "score": 6, "total": 8}).json()
    assert p["modules"]["money"]["test"]["best"] == 6 and p["modules"]["money"]["passed"]
    p = client.post("/api/learn/progress", json={"quiz": "money", "score": 3, "total": 8}).json()
    assert p["quizzes"]["money"]["best"] == 6 and p["quizzes"]["money"]["last"] == 3 and p["quizzes"]["money"]["attempts"] == 2
    p = client.post("/api/learn/progress", json={"lesson": "money-interest", "done": False}).json()
    assert p["lessons_done"] == 0
    assert client.post("/api/learn/progress", json={"quiz": "money", "score": 9, "total": 8}).status_code == 422
    assert client.post("/api/learn/progress", json={"quiz": "money", "score": 5, "total": 40}).status_code == 422
    assert client.post("/api/learn/progress", json={"lesson": "nope"}).status_code == 404
    assert client.post("/api/learn/progress", json={}).status_code == 422
    # the earlier format still works
    p = client.post("/api/learn/progress", json={"module": "risk", "score": 4}).json()
    assert p["quizzes"]["portfolio"]["best"] == 4
    assert client.delete("/api/learn/progress").json()["lessons_done"] == 0


def test_progress_is_private_to_each_user():
    with TestClient(app) as a, TestClient(app) as b:
        a.post("/api/learn/progress", json={"lesson": "markets-orders", "done": True})
        assert "markets-orders" in a.get("/api/learn").json()["progress"]["lessons"]
        assert b.get("/api/learn").json()["progress"]["lessons"] == {}


def test_version_one_progress_is_migrated():
    old = {"markets": {"best": 4, "last": 3, "attempts": 2, "updated": "x"}, "risk": {"best": 5, "last": 5, "attempts": 1}, "gone": {"best": 1}}
    p = PR.normalise(old)
    assert p["v"] == 2 and p["quizzes"]["markets"]["total"] == 5 and p["quizzes"]["portfolio"]["best"] == 5 and "gone" not in p["quizzes"]
    s = PR.summary(p)
    assert not s["modules"]["markets"]["passed"]                    # an old 5-question score does not pass the new test
    PR.record_quiz(p, "markets", 8, 10, "now")
    assert p["quizzes"]["markets"] == {"best": 8, "last": 8, "total": 10, "attempts": 3, "updated": "now"}
    assert PR.normalise(None) == PR.empty() and PR.normalise("junk") == PR.empty()


def test_case_study_uses_stored_data_with_provenance(client):
    from equitypilot.analytics import ratios as R
    from equitypilot.data import repository as repo
    d = client.get("/api/learn/case/SAMPLE-ALPHA").json()
    assert d["available"] and d["period"].startswith("FY") and d["source"] and d["basis_note"] and d["sample"]
    assert d["figures"] and d["ratios"] and all(r["steps"] and r["formula"] for r in d["ratios"])
    rt = R.compute_ratios(repo.get_financials("SAMPLE-ALPHA", auto_refresh=False))
    for r in d["ratios"]:
        if r["key"] in rt.index:
            assert abs(r["value"] - float(rt.loc[r["key"]].iloc[-1])) < 1e-9, r["key"]
    bank = client.get("/api/learn/case/SAMPLE-EPSILON").json()
    assert bank["financial"] and not {"roce", "debt_to_equity", "ebitda_margin", "net_margin"} & {r["key"] for r in bank["ratios"]}
    assert client.get("/api/learn/case/NOSUCH.NS").status_code == 404


def test_legacy_adapter_keeps_older_callers_working():
    from equitypilot.content.learning import MODULES, module, total_questions
    assert len(MODULES) == 13 and module("risk")["id"] == "portfolio" and total_questions() >= 80
    for m in MODULES:
        assert m["sections"] and all(len(q) == 4 for q in m["quiz"]) and Path(m["page"]).exists()


# ------------------------------------------------------------------ the assistant's learning mode
def _ask(client, q, history=None, symbol=None):
    r = client.post("/api/assistant/stream", json={"question": q, "history": history or [], "symbol": symbol})
    assert r.status_code == 200, r.text
    return [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")][-1]


def test_offline_assistant_learning_answers(client):
    simple = _ask(client, "Explain ROE in simple words")["text"]
    assert "ROE in plain words" in simple and "not company data" in simple and "Learning Centre" in simple
    ex = _ask(client, "Give me another numerical example of WACC")
    assert "Illustrative example: WACC" in ex["text"] and "not company data" in ex["text"]
    assert any(s["Source"] == "EquityPilot Learning Centre" for s in ex["sources"])
    assert "Formula" in _ask(client, "How do I calculate ROCE step by step?")["text"]
    diff = _ask(client, "What is the difference between FCFF and FCFE?")["text"]
    assert "| Discount at | WACC | Cost of equity |" in diff
    prac = _ask(client, "Practice questions on the P/E ratio")["text"]
    assert "**Q1.**" in prac and "**Answers**" in prac
    why = _ask(client, 'Why is my quiz answer wrong? Question money-tvm:c2: I chose "Rises"')["text"]
    assert "Why it is not right" in why and "Correct answer**: Falls" in why
    assert "SMART ODR" in _ask(client, "What is SCORES?")["text"]


def test_learning_mode_does_not_take_over_company_questions(client):
    t = _ask(client, "What is the ROE of SAMPLE-ALPHA?")["text"]
    assert "ROE in plain words" not in t and "Illustrative example" not in t
    hist = [{"role": "user", "content": "How has SAMPLE-ALPHA grown?"}, {"role": "assistant", "content": "Revenue grew 12% with ROE of 18%."}]
    t = _ask(client, "Explain it more simply", history=hist)["text"]
    assert "Illustrative example" not in t
    assert "can't give buy, sell or hold" in _ask(client, "Should I buy based on P/E?", symbol="SAMPLE-ALPHA")["text"]


def test_learning_examples_are_fresh_and_correct():
    a = LRN.example_md("ROE", 1)
    b = LRN.example_md("ROE", 2)
    assert a != b and LRN.ILLUSTRATIVE in a
    for name in LRN.GENERATORS:                                      # every generator runs for many seeds without errors
        assert name in CU.GLOSSARY_ENTRIES, name
        for seed in range(25):
            assert "Result" in LRN.example_md(name, seed)


def test_claude_gets_learning_tool_and_prefetch():
    assert any(t["name"] == "learning_content" for t in A.TOOLS)
    assert "learning_content" in A.AGENT_PROMPT and "illustrative" in A.AGENT_PROMPT
    calls, _ = A.plan_prefetch("Explain terminal value in simple words", None, [])
    assert calls == [("learning_content", {"topic": "Explain terminal value in simple words"})]
    calls, _ = A.plan_prefetch("Why is my answer wrong? Question dcf-wacc:c1", None, [])
    assert calls == [("learning_content", {"question_id": "dcf-wacc:c1"})]
    tb = A.ToolBox(1, [])
    text = tb.run("learning_content", {"question_id": "money-tvm:c2"})
    assert text.startswith("[T1]") and "(correct)" in text and "wrong because" in text
    assert "Lesson: Cost of capital" in tb.run("learning_content", {"topic": "WACC"})
