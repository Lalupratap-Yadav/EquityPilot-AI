"""Building blocks of the Learning Centre curriculum: official sources, links to EquityPilot tools, and the lesson,
question, glossary-term and module constructors used by beginner.py, intermediate.py and advanced.py.

Every lesson follows the same nine parts: concept, why it matters, formula (or key rules), simple example,
interpretation, common mistakes, real-world application, quick revision and a knowledge check. Optional extras:
`detail` (an expandable deeper explanation), calculators, links to EquityPilot tools, glossary terms, ratio cards,
case studies and official sources.

Numbers in examples are illustrative unless a lesson says otherwise; real company figures are only ever shown by the
case-study widget, which reads EquityPilot's stored statements together with their source and period.
"""
from __future__ import annotations

import re

REVIEWED = "2026-11-23"      # when the facts, rules and links in the curriculum were last checked

# Official and primary sources only (regulators, exchanges, depositories, government). Lessons cite these by key.
SOURCES: dict[str, dict[str, str]] = {
    "sebi": {"name": "SEBI", "url": "https://www.sebi.gov.in/"},
    "sebi_investor": {"name": "SEBI investor website", "url": "https://investor.sebi.gov.in/"},
    "sebi_press": {"name": "SEBI press releases", "url": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=6&ssid=23&smid=0"},
    "sebi_fo_study": {"name": "SEBI press release, 20 Aug 2026: studies on retail participation and profitability in equity derivatives",
                      "url": "https://www.sebi.gov.in/media-and-notifications/press-releases/aug-2026/sebi-studies-indicate-key-trends-in-retail-participation-trading-behaviour-and-profitability-in-the-equity-derivatives_103838.html"},
    "scores": {"name": "SEBI SCORES complaint portal", "url": "https://scores.sebi.gov.in/"},
    "scores_faq": {"name": "SCORES FAQs (timelines and review stages)", "url": "https://scores.sebi.gov.in/faqs"},
    "scores_circular": {"name": "SEBI circular on SCORES and its link to online dispute resolution, 20 Sep 2023",
                        "url": "https://www.sebi.gov.in/legal/circulars/sep-2023/redressal-of-investor-grievances-through-the-sebi-complaint-redressal-scores-platform-and-linking-it-to-online-dispute-resolution-platform_77159.html"},
    "smartodr": {"name": "SMART ODR portal (online conciliation and arbitration)", "url": "https://smartodr.in/"},
    "nse": {"name": "National Stock Exchange of India (NSE)", "url": "https://www.nseindia.com/"},
    "bse": {"name": "BSE", "url": "https://www.bseindia.com/"},
    "nsdl": {"name": "NSDL (depository)", "url": "https://nsdl.co.in/"},
    "cdsl": {"name": "CDSL (depository)", "url": "https://www.cdslindia.com/"},
    "rbi": {"name": "Reserve Bank of India", "url": "https://www.rbi.org.in/"},
    "rbi_retail": {"name": "RBI Retail Direct (government securities for individuals)", "url": "https://rbiretaildirect.org.in/"},
    "amfi": {"name": "AMFI (Association of Mutual Funds in India)", "url": "https://www.amfiindia.com/"},
    "nism": {"name": "NISM (National Institute of Securities Markets)", "url": "https://www.nism.ac.in/"},
    "mospi": {"name": "Ministry of Statistics and Programme Implementation (GDP and CPI data)", "url": "https://www.mospi.gov.in/"},
    "budget": {"name": "Union Budget documents", "url": "https://www.indiabudget.gov.in/"},
    "mca": {"name": "Ministry of Corporate Affairs (Companies Act, Ind AS)", "url": "https://www.mca.gov.in/"},
    "dicgc": {"name": "DICGC: a guide to deposit insurance (₹5 lakh cover per depositor per bank)", "url": "https://www.dicgc.org.in/guide-to-deposit-insurance"},
    "iepf": {"name": "Investor Education and Protection Fund Authority", "url": "https://www.iepf.gov.in/"},
    "cybercrime": {"name": "National Cyber Crime Reporting Portal", "url": "https://cybercrime.gov.in/"},
    "i4c": {"name": "Indian Cybercrime Coordination Centre, Ministry of Home Affairs (cybercrime helpline 1930)", "url": "https://i4c.mha.gov.in/"},
}

# EquityPilot pages a lesson can send the learner to (tests check every path against the web app's routes).
TOOLS: dict[str, tuple[str, str]] = {
    "company": ("Company page", "/company/{symbol}"),
    "valuation": ("Valuation Lab", "/valuation"),
    "markets": ("Market Tracker", "/markets"),
    "screener": ("Screener", "/screener"),
    "portfolio": ("Portfolio", "/portfolio"),
    "invest": ("Virtual Invest", "/invest"),
    "compare": ("Compare companies", "/compare"),
    "news": ("News & Intelligence", "/news"),
    "earnings": ("Earnings calendar", "/earnings"),
    "corporate-actions": ("Corporate actions", "/corporate-actions"),
    "industries": ("Industries", "/industries"),
    "documents": ("Documents", "/documents"),
    "data-quality": ("Data quality", "/data-quality"),
    "assistant": ("AI Assistant", "/assistant"),
}

LEVELS = [
    {"id": "beginner", "title": "Beginner", "summary": "Money, the economy, how the Indian market works, corporate actions and how investors are protected."},
    {"id": "intermediate", "title": "Intermediate", "summary": "Financial statements, ratios, investment products, technical analysis and the basics of valuation."},
    {"id": "advanced", "title": "Advanced", "summary": "Discounted cash flow valuation, portfolio risk and the research process, with real company case studies."},
]

ILLUSTRATIVE = "_Illustrative numbers, not company data._"


# ------------------------------------------------------------------ questions
def v(fn: str, *args, unit: str = "", pick: int | str | None = None, expect: float | None = None) -> dict:
    """How the tests recompute a numerical answer: calc.<fn>(*args), item `pick` of a tuple/dict result, x100 when
    unit is '%'. `expect` is the number the question states (defaults to a numerical question's answer)."""
    return {"fn": fn, "args": list(args), "unit": unit, "pick": pick, "expect": expect}


def mcq(q: str, options: list[str], answer: int, explain: str, wrong: list[str | None] | None = None, *,
        level: str = "easy", kind: str = "concept", verify: dict | None = None, steps: str | None = None) -> dict:
    """A multiple-choice question. `wrong` gives, for each option, why it is wrong (the entry for the correct option is
    ignored). `verify` (see v()) lets the tests recompute the number in the correct option.
    kind: concept | numerical | statement (reading a financial statement) | case (case-based) | rule (regulation)."""
    return {"type": "mcq", "q": q, "options": options, "answer": answer, "explain": explain,
            "wrong": [None if i == answer else (w or None) for i, w in enumerate(wrong or [None] * len(options))],
            "level": level, "kind": kind, "verify": verify, "steps": steps}


def num(q: str, answer: float, explain: str, steps: str, *, unit: str = "", tolerance: float | None = None,
        level: str = "medium", kind: str = "numerical", verify: dict | None = None) -> dict:
    """A numerical problem answered by typing a number. `unit` is shown beside the box (%, ₹, x, years ...).
    The default tolerance accepts sensible rounding but rejects the usual mistakes (e.g. simple instead of compound)."""
    tol = tolerance if tolerance is not None else (abs(answer) * 0.002 if abs(answer) >= 100 else 0.05)
    return {"type": "num", "q": q, "answer": answer, "unit": unit, "tolerance": tol, "explain": explain, "steps": steps,
            "level": level, "kind": kind, "verify": verify}


# ------------------------------------------------------------------ glossary terms defined by lessons
def term(name: str, definition: str, *, formula: str | None = None, example: str | None = None,
         aliases: tuple[str, ...] = (), related: tuple[str, ...] = (), interpretation: str | None = None) -> dict:
    return {"term": name, "definition": definition, "formula": formula, "example": example,
            "aliases": [a.lower() for a in aliases], "related": list(related), "interpretation": interpretation}


# ------------------------------------------------------------------ lessons and modules
def lesson(id: str, title: str, *, concept: str, why: str, example: str, interpret: str, mistakes: list[str],
           application: str, revision: list[str], check: list[dict], formulas: list[str] | None = None,
           rules: list[str] | None = None, detail: str | None = None, calculators: tuple[str, ...] = (),
           tools: tuple[tuple[str, str], ...] = (), sources: tuple[str, ...] = (), terms: tuple = (),
           cards: tuple[str, ...] = (), case: tuple[str, ...] = (), summary: str | None = None) -> dict:
    text = " ".join([concept, why, example, interpret, application, " ".join(mistakes), " ".join(revision),
                     " ".join(formulas or []), " ".join(rules or []), detail or ""])
    words = len(re.findall(r"\w+", text))
    return {
        "id": id, "title": title, "summary": summary or _first_sentence(concept),
        "minutes": max(3, round(words / 140 + len(check) * 0.75)),     # unhurried reading of technical text, plus the questions
        "concept": concept.strip(), "why": why.strip(), "formulas": formulas or [], "rules": rules or [],
        "example": example.strip(), "interpret": interpret.strip(), "mistakes": mistakes, "application": application.strip(),
        "revision": revision, "check": check, "detail": detail.strip() if detail else None,
        "calculators": list(calculators), "tools": [_tool(t, why_) for t, why_ in tools], "sources": list(sources),
        "terms": list(terms), "cards": list(cards), "case": list(case),
    }


def module(id: str, title: str, level: str, summary: str, lessons: list[dict], test: list[dict], *,
           page: str = "views/learning.py") -> dict:
    """`test` is the module completion test. `page` is the classic (Streamlit) page the module links to."""
    return {"id": id, "title": title, "level": level, "summary": summary, "lessons": lessons, "test": test, "page": page}


def _tool(key: str, text: str) -> dict:
    name, sym = (key.split(":", 1) + [""])[:2]
    label, path = TOOLS[name]
    return {"tool": name, "label": label, "to": path.replace("{symbol}", sym) if sym else path, "text": text}


def _first_sentence(md: str) -> str:
    plain = re.sub(r"[*_#>|]", "", md).strip().split("\n")[0]
    m = re.match(r"(.+?[.!?])(\s|$)", plain)
    return (m.group(1) if m else plain)[:220]
