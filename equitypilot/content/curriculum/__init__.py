"""Learning Centre curriculum: three levels, thirteen modules, lessons in a fixed nine-part format, knowledge checks,
module tests, a merged glossary, ratio cards and official sources.

Content lives in beginner.py, intermediate.py, intermediate_more.py and advanced.py; this module assembles it once at
import (ids, previous/next links, glossary cross-links) and offers the read functions the API, the offline assistant
and the classic Streamlit page use. Nothing here calls a network service.
"""
from __future__ import annotations

import random
import re
from copy import deepcopy

from .. import metrics_guide as MG
from ..glossary import GLOSSARY
from . import advanced, beginner, intermediate, intermediate_more
from .core import LEVELS, REVIEWED, SOURCES, TOOLS
from .intermediate import RATIO_CARDS

MODULES: list[dict] = beginner.MODULES + intermediate.MODULES + intermediate_more.MODULES + advanced.MODULES
MODULE_ALIASES = {"ra": "analysis", "risk": "portfolio"}      # module ids of the earlier eight-module Learning Centre
LEGACY_TOTALS = {"markets": 5, "ra": 5, "statements": 5, "ratios": 5, "valuation": 5, "technical": 5, "risk": 5, "corporate": 4}
PASS_MARK = 0.6                                                # share of a module test needed to pass it

# Calculators the lessons can embed (implemented in web/src/lib/learnCalc.ts with the same formulas as calc.py).
CALCULATORS = {
    "interest": "Simple vs compound interest", "real-return": "Nominal vs real return", "eps-pe": "EPS and P/E",
    "roe-roce": "ROE and ROCE", "statements": "Linked financial statements", "fcf": "Free cash flow",
    "bond": "Bond yield", "portfolio": "Portfolio return and Sharpe ratio", "diversification": "Diversification (two assets)",
    "dcf": "Basic DCF", "wacc": "Cost of equity and WACC",
}

# Classic (Streamlit) pages the legacy adapter links each module to.
_LEGACY_PAGES = {"markets": "views/dashboard.py", "corporate": "views/news.py", "statements": "views/financials.py",
                 "ratios": "views/financials.py", "technical": "views/technicals.py", "valuation": "views/valuation.py",
                 "dcf": "views/valuation.py", "portfolio": "views/portfolio.py", "analysis": "views/report.py",
                 "products": "views/portfolio.py", "protection": "views/guide.py", "money": "views/guide.py", "economy": "views/news.py"}

LESSONS: dict[str, dict] = {}
QUESTIONS: dict[str, dict] = {}
MODULE_BY_ID: dict[str, dict] = {m["id"]: m for m in MODULES}
ORDER: list[str] = []                    # every lesson id in curriculum order
UNRESOLVED_TERMS: list[tuple[str, str]] = []     # (lesson, term) string references that match no glossary entry


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9&/+ -]+", " ", s.lower().replace("’", "'").replace("'", "")).split())


# ------------------------------------------------------------------ glossary
# Metric-guide keys whose plain names would duplicate a concept that a lesson names differently.
_MG_NAMES = {"bvps": "Book value per share", "cfo_to_net_income": "Cash conversion", "ebit_margin": "Operating margin",
             "dividend_payout": "Payout ratio", "net_income_growth": "Net profit growth"}


def _nice(key: str) -> str:
    if key in _MG_NAMES:
        return _MG_NAMES[key]
    name = key.replace("_", " ")
    nice = name[0].upper() + name[1:]
    for a, b in (("Roe", "ROE"), ("Roce", "ROCE"), ("Roa", "ROA"), ("Ebitda", "EBITDA"), ("ebitda", "EBITDA"), ("Cfo", "CFO"),
                 ("cfo", "CFO"), ("Fcf", "FCF"), ("fcf", "FCF"), ("Eps", "EPS"), ("eps", "EPS"), ("Pe", "P/E"), ("Ebit", "EBIT"),
                 ("ebit", "EBIT"), ("Bvps", "BVPS"), ("Nwc", "NWC"), ("nwc", "NWC")):
        nice = re.sub(rf"\b{a}\b", b, nice)
    return nice


def _build_glossary() -> dict[str, dict]:
    entries: dict[str, dict] = {}

    def index() -> dict[str, str]:
        out: dict[str, str] = {}
        for name, e in entries.items():
            for a in e["aliases"]:
                out.setdefault(_norm(a), name)
        for name in entries:                     # exact names win over aliases
            out[_norm(name)] = name
        return out

    for name, e in GLOSSARY.items():
        entries[name] = {"term": name, "aliases": list(e.get("aliases", [])), "definition": e["definition"],
                         "formula": e.get("formula") if e.get("formula") not in (None, "—") else None,
                         "interpretation": e.get("interpretation"), "example": None, "ratio": e.get("ratio"),
                         "related": [], "lessons": []}
    have = index()
    for key, g in MG.GUIDE.items():
        if _norm(key.replace("_", " ")) in have:
            continue
        nice = _nice(key)
        card = RATIO_CARDS.get(key, {})
        entries[nice] = {"term": nice, "aliases": [key.replace("_", " ")], "definition": g.get("what", ""),
                         "formula": card.get("formula"), "interpretation": " ".join(x for x in (g.get("why"), g.get("read")) if x) or None,
                         "example": g.get("example"), "ratio": key, "related": [], "lessons": []}
    # terms defined by lessons
    for m in MODULES:
        for les in m["lessons"]:
            for t in les["terms"]:
                if isinstance(t, str):
                    continue
                have = index()
                hit = have.get(_norm(t["term"]))
                if hit and _norm(hit) == _norm(t["term"]):
                    e = entries[hit]                 # the same concept, already defined: enrich it
                    e["aliases"] += [a for a in t["aliases"] if a not in e["aliases"]]
                    for f in ("formula", "example", "interpretation"):
                        e[f] = e[f] or t.get(f)
                    e["related"] += t["related"]
                else:
                    entries[t["term"]] = {"term": t["term"], "aliases": list(t["aliases"]), "definition": t["definition"],
                                          "formula": t.get("formula"), "interpretation": t.get("interpretation"),
                                          "example": t.get("example"), "ratio": None, "related": list(t["related"]), "lessons": []}
    # lesson links and related terms
    have = index()
    for m in MODULES:
        for les in m["lessons"]:
            names = []
            for t in les["terms"]:
                raw = t if isinstance(t, str) else t["term"]
                name = have.get(_norm(raw))
                if not name:
                    UNRESOLVED_TERMS.append((les["id"], raw))
                    continue
                names.append(name)
                links = entries[name]["lessons"]
                if not any(x["id"] == les["id"] for x in links):
                    links.append({"id": les["id"], "title": les["title"], "module": m["id"]})
            les["term_names"] = names
            for n in names:
                entries[n]["related"] += [x for x in names if x != n]
    names_n = {_norm(n): n for n in entries}        # an alias that is another entry's name belongs to that entry
    for e in entries.values():
        seen, rel = set(), []
        for r in e["related"]:
            name = have.get(_norm(r))
            if name and name != e["term"] and name not in seen:
                seen.add(name)
                rel.append(name)
        e["related"] = rel[:6]
        e["aliases"] = sorted({_norm(a) for a in e["aliases"] if _norm(a) and _norm(a) != _norm(e["term"])
                               and not (_norm(a) in names_n and names_n[_norm(a)] != e["term"])})
        first = next((c for c in e["term"].upper() if c.isalpha()), "#")
        e["letter"] = first
    return dict(sorted(entries.items(), key=lambda kv: kv[0].lower()))


def ratio_card(key: str) -> dict:
    g = MG.GUIDE.get(key, {})
    c = RATIO_CARDS.get(key, {})
    return {"key": key, "name": c.get("name") or _nice(key), **{f: c.get(f) or g.get(f) for f in
            ("what", "why", "read", "example", "formula", "limits", "unsuitable")}}


# ------------------------------------------------------------------ assembly
def _assemble() -> None:
    flat = []
    for m in MODULES:
        m["minutes"] = 0
        for les in m["lessons"]:
            les["module"], les["level"] = m["id"], m["level"]
            for j, q in enumerate(les["check"], start=1):
                q["id"] = f"{les['id']}:c{j}"
                q["source"] = {"lesson": les["id"], "module": m["id"]}
                QUESTIONS[q["id"]] = q
            m["minutes"] += les["minutes"]
            LESSONS[les["id"]] = les
            flat.append(les)
        for j, q in enumerate(m["test"], start=1):
            q["id"] = f"{m['id']}:t{j}"
            q["source"] = {"module": m["id"]}
            QUESTIONS[q["id"]] = q
    for i, les in enumerate(flat):
        les["prev"] = flat[i - 1]["id"] if i else None
        les["next"] = flat[i + 1]["id"] if i + 1 < len(flat) else None
        ORDER.append(les["id"])


_assemble()
GLOSSARY_ENTRIES: dict[str, dict] = _build_glossary()
_TERM_INDEX: dict[str, str] = {}
for _name, _e in GLOSSARY_ENTRIES.items():
    for _a in _e["aliases"]:
        _TERM_INDEX.setdefault(_a, _name)
for _name in GLOSSARY_ENTRIES:
    _TERM_INDEX[_norm(_name)] = _name


# ------------------------------------------------------------------ read API
def resolve_module(mid: str) -> dict | None:
    return MODULE_BY_ID.get(MODULE_ALIASES.get(mid, mid))


def public_question(q: dict) -> dict:
    """A question as the browser sees it (answers included: quizzes are graded in the browser, there is nothing at stake)."""
    out = {k: v for k, v in q.items() if k != "verify"}
    return out


def lesson_payload(les: dict) -> dict:
    out = {k: deepcopy(v) for k, v in les.items() if k not in ("terms", "check", "cards", "sources")}
    out["check"] = [public_question(q) for q in les["check"]]
    out["cards"] = [ratio_card(k) for k in les["cards"]]
    out["sources"] = [{"key": k, **SOURCES[k]} for k in les["sources"]]
    out["terms"] = [{"term": n, "definition": GLOSSARY_ENTRIES[n]["definition"]} for n in les.get("term_names", [])]
    out["calculators"] = [{"id": c, "title": CALCULATORS[c]} for c in les["calculators"]]
    return out


def module_card(m: dict) -> dict:
    return {"id": m["id"], "title": m["title"], "level": m["level"], "summary": m["summary"], "minutes": m["minutes"],
            "lessons": [{"id": les["id"], "title": les["title"], "minutes": les["minutes"], "summary": les["summary"]} for les in m["lessons"]],
            "questions": len(m["test"])}


def module_payload(m: dict) -> dict:
    i = MODULES.index(m)
    return {**module_card(m), "lessons": [lesson_payload(les) for les in m["lessons"]],
            "test": [public_question(q) for q in m["test"]],
            "prev_module": MODULES[i - 1]["id"] if i else None, "next_module": MODULES[i + 1]["id"] if i + 1 < len(MODULES) else None}


def overview() -> dict:
    return {"levels": [{**lv, "modules": [module_card(m) for m in MODULES if m["level"] == lv["id"]]} for lv in LEVELS],
            "reviewed": REVIEWED, "pass_mark": PASS_MARK, "calculators": [{"id": k, "title": v} for k, v in CALCULATORS.items()],
            "counts": {"modules": len(MODULES), "lessons": len(LESSONS), "questions": len(QUESTIONS), "terms": len(GLOSSARY_ENTRIES)}}


def glossary() -> list[dict]:
    return list(GLOSSARY_ENTRIES.values())


def find_term(text: str) -> str | None:
    """The glossary entry a piece of text names: longest name or alias found as whole words."""
    t = f" {_norm(text)} "
    best, best_len = None, 0
    for key, name in _TERM_INDEX.items():
        if len(key) > best_len and f" {key} " in t:
            best, best_len = name, len(key)
    return best


def find_terms(text: str, limit: int = 3) -> list[str]:
    """Every glossary entry named in the text, longest matches first, without overlapping words."""
    words = _norm(text).split()
    singular = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words]
    t = f" {' '.join(words)} | {' '.join(singular)} "      # 'real returns' also finds 'real return'
    found: list[str] = []
    for key in sorted(_TERM_INDEX, key=len, reverse=True):
        if f" {key} " in t and _TERM_INDEX[key] not in found:
            found.append(_TERM_INDEX[key])
            t = t.replace(f" {key} ", " | ")
            if len(found) >= limit:
                break
    order = " ".join(singular)
    return sorted(found, key=lambda n: min((order.find(k) for k, v in _TERM_INDEX.items() if v == n and order.find(k) >= 0), default=0))


def lessons_for_term(name: str) -> list[str]:
    return [x["id"] for x in GLOSSARY_ENTRIES.get(name, {}).get("lessons", [])]


def module_questions(mid: str) -> list[dict]:
    m = resolve_module(mid)
    return [q for les in m["lessons"] for q in les["check"]] + list(m["test"]) if m else []


def revision_quiz(module_ids: list[str], n: int = 10, seed: int | None = None) -> list[dict]:
    """A mixed quiz drawn from the knowledge checks and module tests of the given modules (all modules if none),
    balanced across modules and difficulty levels."""
    mods = [m for m in (resolve_module(x) for x in module_ids) if m] or MODULES
    rng = random.Random(seed)
    pools = {m["id"]: rng.sample(module_questions(m["id"]), len(module_questions(m["id"]))) for m in mods}
    picked: list[dict] = []
    while len(picked) < n and any(pools.values()):
        for mid in list(pools):
            if pools[mid] and len(picked) < n:
                picked.append(pools[mid].pop())
    rng.shuffle(picked)
    return [public_question(q) for q in picked]


# ------------------------------------------------------------------ legacy adapter (classic Streamlit page, explore topics)
def legacy_modules() -> list[dict]:
    """The curriculum in the shape of the earlier eight-module list: sections, formulas and an MCQ quiz per module."""
    out = []
    for m in MODULES:
        sections = []
        for les in m["lessons"]:
            body = les["concept"] + "\n\n**Why it matters.** " + les["why"] + "\n\n" + les["example"]
            sections.append((les["title"], body))
        formulas = [f for les in m["lessons"] for f in les["formulas"]]
        quiz = [(q["q"], q["options"], q["answer"], q["explain"]) for q in m["test"] if q["type"] == "mcq"]
        out.append({"id": m["id"], "title": m["title"], "level": m["level"], "page": _LEGACY_PAGES.get(m["id"], "views/guide.py"),
                    "summary": m["summary"], "sections": sections, "formulas": formulas, "quiz": quiz})
    return out


__all__ = ["CALCULATORS", "GLOSSARY_ENTRIES", "LESSONS", "LEVELS", "MODULES", "ORDER", "PASS_MARK", "QUESTIONS", "REVIEWED",
           "SOURCES", "TOOLS", "find_term", "glossary", "legacy_modules", "lesson_payload", "module_card", "module_payload",
           "overview", "ratio_card", "resolve_module", "revision_quiz"]
