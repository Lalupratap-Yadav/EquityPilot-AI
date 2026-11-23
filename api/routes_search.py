"""Global search: one query, results grouped by kind and ranked by match strength.

Groups: companies (with a quick price preview), indices, industries/sectors, financial concepts, research tools
(screens, valuation, comparison), and recent news. Everything is database/rule backed - no AI is involved - so results
are deterministic, fast and never invented. Company matching is typo-tolerant (see securities.resolve).
"""
from __future__ import annotations

import difflib
import logging
import re
import threading
import time

import pandas as pd
from fastapi import APIRouter, Query, Request

from equitypilot import db
from equitypilot.content.industries import BY_ID, INDUSTRIES
from equitypilot.data import feeds as N
from equitypilot.data import marketdata as M
from equitypilot.data import securities as S
from equitypilot.data import source_tiers as ST

from .core import LIMITER, clean, current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search"])

# ------------------------------------------------------------------ vocabularies
INDEX_ALIASES = {
    "^NSEI": ["nifty", "nifty 50", "nifty50", "nse index"], "^BSESN": ["sensex", "bse sensex", "bse 30"],
    "^NSEBANK": ["bank nifty", "banknifty", "nifty bank"], "^CNX100": ["nifty 100"], "^NSEMDCP50": ["nifty midcap", "midcap", "midcap 50"],
    "^INDIAVIX": ["india vix", "vix", "volatility index", "fear index"],
}
INDUSTRY_ALIASES = {
    "banking": ["bank", "banks", "banking", "psu bank", "private bank", "lender"], "financial-services": ["nbfc", "insurance", "finance", "financial services", "amc"],
    "it": ["it", "tech", "technology", "software", "information technology", "it services"], "pharma": ["pharma", "pharmaceutical", "drug", "medicine"],
    "healthcare": ["hospital", "healthcare", "diagnostics"], "automobiles": ["auto", "automobile", "car", "two wheeler", "ev", "vehicle"],
    "fmcg": ["fmcg", "consumer staples", "consumer goods"], "agriculture": ["agri", "agriculture", "fertiliser", "fertilizer", "agrochemical"],
    "energy": ["energy", "power", "oil", "gas", "utilities", "renewable", "electricity"], "infrastructure": ["infra", "infrastructure", "cement", "construction", "capital goods"],
    "metals": ["metal", "metals", "steel", "mining", "aluminium", "copper"], "real-estate": ["real estate", "realty", "housing", "property"],
    "telecom": ["telecom", "telecommunication", "mobile"], "consumer-durables": ["consumer durables", "appliances", "electronics", "durables"],
    "chemicals": ["chemical", "chemicals", "paint", "paints", "speciality chemicals"],
}
TOOLS = [  # (pattern, label, description, link)
    (r"\b(high roe|roe|return on equity)\b", "Companies with high ROE", "Ranked by return on equity", "/assistant?q=Top%2010%20companies%20by%20ROE"),
    (r"\b(roce)\b", "Companies with high ROCE", "Ranked by return on capital employed", "/assistant?q=Top%2010%20companies%20by%20ROCE"),
    (r"\b(debt[- ]?free|low debt|zero debt)\b", "Debt-free companies", "Debt to equity at or below 0.1", "/assistant?q=Which%20companies%20are%20debt%20free%3F"),
    (r"\b(earnings?|results? (date|calendar)|quarterly results?|board meetings?|result season|q[1-4] results?)\b", "Earnings & Results",
     "Confirmed result dates from board-meeting filings, and results filed", "/earnings"),
    (r"\b(corporate actions?|dividends?|ex-?date|record date|splits?|bonus|buy-?backs?|rights issue|demerger)\b", "Corporate Actions",
     "Dividends, splits, bonus issues and buybacks with exchange ex-dates", "/corporate-actions"),
    (r"\b(data quality|data sources?|freshness|data coverage|stale data|provenance)\b", "Data Quality",
     "Where each dataset comes from, how fresh it is and what is missing", "/data-quality"),
    (r"\b(dividend|yield)\b", "Dividend payers", "Screener preset", "/screener?preset=Dividend%20payers"),
    (r"\b(growth|growing|fast growing)\b", "High-growth companies", "Screener preset", "/screener?preset=High%20growth"),
    (r"\b(quality|compounder)", "Quality compounders", "Screener preset", "/screener?preset=Quality%20compounders"),
    (r"\b(value|cheap|undervalued|low pe)\b", "Low-debt value", "Screener preset", "/screener?preset=Low-debt%20value"),
    (r"\b(cash|free cash flow|fcf)\b", "Cash generators", "Screener preset", "/screener?preset=Cash%20generators"),
    (r"\b(dcf|intrinsic|valuation|fair value|discounted cash)", "Valuation Lab", "DCF (FCFF/FCFE), multiples, scenarios", "/valuation"),
    (r"\b(compare|comparison|vs|versus|peer)", "Compare companies", "Side-by-side metrics for up to 5 companies", "/compare"),
    (r"\b(screen|screener|filter)", "Screener", "Filter the tracked universe by any metric", "/screener"),
    (r"\b(gainer|loser|mover|market today|breadth|heat ?map)", "Market Tracker", "Indices, movers and live-updating charts", "/markets"),
    (r"\b(news|announcement|result|ipo|rbi|sebi|filing|disclosure)", "News & Intelligence", "Exchange filings, RBI, SEBI and market news", "/news"),
    (r"\b(paper|virtual|practice|practise|portfolio)", "Virtual Invest", "Practise with ₹10 lakh virtual money", "/invest"),
    (r"\b(learn|course|module|quiz|nism)", "Learning Centre", "Modules with quizzes", "/learn"),
]
_GENERIC = re.compile(r"\b(indian|india|sector|sectors|industry|industries|companies|company|stocks?|shares?|listed|top|best|list of|all)\b")


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 /&-]+", " ", (s or "").lower()).split())


_INDEX_TERMS = {"NIFTY 50", "SENSEX"}      # the indices group already answers these


def _concepts() -> list[dict]:
    """Every Learning Centre glossary entry (the original glossary, the metric guide and terms defined by lessons)."""
    from urllib.parse import quote

    from equitypilot.content import curriculum as CU
    out = []
    for e in CU.glossary():
        if e["term"] in _INDEX_TERMS:
            continue
        out.append({"key": e.get("ratio") or e["term"], "name": e["term"], "aliases": [_norm(a) for a in e["aliases"]] + [_norm(e["term"])],
                    "summary": e.get("definition", ""), "to": f"/learn?tab=glossary&term={quote(e['term'])}"})
    return out


_CONCEPTS = _concepts()
_CONCEPT_VOCAB = sorted({a for c in _CONCEPTS for a in c["aliases"]})


def _score_text(q: str, cands: list[str]) -> int:
    best = 0
    for a in cands:
        if not a:
            continue
        if q == a:
            best = max(best, 100)
        elif a.startswith(q) and len(q) >= 2:
            best = max(best, 85)
        elif re.search(rf"\b{re.escape(a)}\b", q) and len(a) >= 2:
            best = max(best, 80)          # alias contained in the query: "nifty 50 chart", "debt to equity ratio"
        elif len(q) >= 4 and q in a:
            best = max(best, 60)
    return best


# ------------------------------------------------------------------ groups
def _companies(q: str, limit: int) -> tuple[list[dict], str | None, int]:
    res = S.search(q, limit + 4)
    if not res:
        return [], None, 0
    best = S.resolve(q, 1)
    top = max(int(res[0].get("score") or 0), int(best[0]["score"]) if best else 0)
    if top >= 90:                                      # an exact match exists: drop weak substring hits
        res = [r for r in res if (r.get("score") or 0) >= 50 or (best and r["symbol"] == best[0]["symbol"])]
    if best and best[0]["score"] >= 95 and res and res[0]["symbol"] != best[0]["symbol"]:
        res = sorted(res, key=lambda r: r["symbol"] != best[0]["symbol"])
    res = res[:limit]
    dym = next((r.get("did_you_mean") for r in res if r.get("did_you_mean")), None)
    from .routes_explore import metrics_frame
    from .routes_market import universe_snapshot
    snap = {r["symbol"]: r for r in universe_snapshot()}
    try:
        mf = metrics_frame().set_index("symbol")
    except Exception:
        mf = pd.DataFrame()
    out = []
    for r in res:
        sym = r["symbol"]
        sq = snap.get(sym, {})
        pe = mf.at[sym, "pe"] if sym in mf.index and "pe" in mf.columns else None
        out.append({**r, "exchange": "BSE" if sym.endswith(".BO") else "Sample" if sym.startswith("SAMPLE-") else "NSE",
                    "industry_name": BY_ID.get(sq.get("industry") or "", {}).get("name") or r.get("industry"),
                    "price": sq.get("price"), "change_pct": sq.get("change_pct"), "market_cap": sq.get("market_cap"),
                    "pe": None if pe is None or pd.isna(pe) else float(pe), "status": sq.get("status")})
    return out, dym, top


def _indices(q: str) -> tuple[list[dict], int]:
    names = {**M.BROAD_INDICES, **{s: v[0] for s, v in M.SECTOR_INDICES.items()}}
    hits = []
    for sym, name in names.items():
        sc = _score_text(q, [_norm(name)] + INDEX_ALIASES.get(sym, []))
        if sc >= 60:
            hits.append((sc, {"symbol": sym, "name": name}))
    if hits:                                           # prices only when an index matched (cached tiles, no provider call)
        rows = {t["symbol"]: t for t in M.index_overview()}
        for _, h in hits:
            t = rows.get(h["symbol"], {})
            h.update(last=t.get("last"), change_pct=t.get("change_pct"), as_of=t.get("as_of"))
    hits.sort(key=lambda x: -x[0])
    return [h for _, h in hits[:5]], (hits[0][0] if hits else 0)


def _industries(q: str) -> tuple[list[dict], int]:
    core = _GENERIC.sub(" ", q).strip() or q
    hits = []
    for ind in INDUSTRIES:
        sc = _score_text(core, [_norm(ind["name"]), ind["id"]] + INDUSTRY_ALIASES.get(ind["id"], []))
        if sc >= 60:
            hits.append((sc + (5 if _GENERIC.search(q) else 0), {"id": ind["id"], "name": ind["name"], "companies": len(ind.get("symbols", []))}))
    hits.sort(key=lambda x: -x[0])
    return [h for _, h in hits[:4]], (hits[0][0] if hits else 0)


def _concept_hits(q: str) -> tuple[list[dict], int]:
    core = re.sub(r"\b(ratio|meaning|what is|define|definition|explain|formula)\b", " ", q).strip() or q
    hits = []
    for c in _CONCEPTS:
        sc = max(_score_text(q, c["aliases"]), _score_text(core, c["aliases"]))
        if sc >= 60:
            hits.append((sc, c))
    if not hits and len(core) >= 4:                    # typo tolerance: "debt to equty"
        m = difflib.get_close_matches(core, _CONCEPT_VOCAB, n=2, cutoff=0.8)
        hits = [(70, c) for c in _CONCEPTS if any(a in m for a in c["aliases"])]
    hits.sort(key=lambda x: -x[0])
    return [{"key": c["key"], "name": c["name"], "summary": c["summary"], "to": c["to"]} for _, c in hits[:3]], (hits[0][0] if hits else 0)


def _tools(q: str) -> list[dict]:
    return [{"label": label, "description": desc, "to": to} for pat, label, desc, to in TOOLS if re.search(pat, q)][:4]


_SEARCH_NEWS_FEEDS = [k for k in N.FEEDS if not k.startswith("nse_")] + ["yahoo_market"]
NEWS_INDEX_TTL = 120
_NEWS_INDEX: dict = {"t": 0.0, "rows": []}
_NEWS_INDEX_LOCK = threading.Lock()


def _news_rows() -> list[tuple[str, dict]]:
    """Publisher and regulator headlines (newest first, with their lower-case titles), reloaded every 2 minutes.
    Exchange filing titles are just company names - the company group covers those - and they are 95% of the news
    table; matching words in memory over the rest takes about a millisecond, whatever the words."""
    if time.time() - _NEWS_INDEX["t"] < NEWS_INDEX_TTL and _NEWS_INDEX["rows"]:
        return _NEWS_INDEX["rows"]
    with _NEWS_INDEX_LOCK:
        if time.time() - _NEWS_INDEX["t"] < NEWS_INDEX_TTL and _NEWS_INDEX["rows"]:
            return _NEWS_INDEX["rows"]
        n = db.news_items.c
        df = db.read_df(db.select(n.title, n.url, n.source, n.published, n.symbol).where(n.feed.in_(_SEARCH_NEWS_FEEDS))
                        .order_by(n.published.desc().nulls_last()).limit(20000))
        rows = [(str(r["title"] or "").lower(), r) for r in df.to_dict("records")]
        _NEWS_INDEX.update(t=time.time(), rows=rows)
        return rows


def _news(q: str) -> list[dict]:
    words = [w for w in re.findall(r"[a-z0-9]{3,}", q) if w not in {"the", "and", "news", "latest", "today"}][:4]
    if not words:
        return []
    out, seen = [], set()
    fund_query = "fund" in q or "etf" in q
    for low, r in _news_rows():
        if len(out) >= 4:
            break
        if not all(w in low for w in words):
            continue
        title = (r["title"] or "").strip()
        if title.lower() in seen or (not fund_query and re.search(r"mutual fund|\betf\b", title, re.I)):
            continue
        seen.add(title.lower())
        tier = "primary" if any(k in (r["source"] or "") for k in ("NSE", "RBI", "SEBI", "BSE")) else ST.tier((r["source"] or "").replace(" via Yahoo Finance", ""))
        if tier == "unrated":
            continue
        out.append({**r, "tier": tier})
    return out[:4]


_CACHE: dict[str, tuple[float, dict]] = {}


def search_all(query: str, limit: int = 8) -> dict:
    q = _norm(query)[:80]
    key = f"{q}|{limit}"
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    if not q:
        return {"query": "", "companies": [], "indices": [], "industries": [], "concepts": [], "tools": [], "news": [], "order": [], "results": []}
    companies, dym, cs = _companies(query.strip(), limit)
    indices, is_ = _indices(q)
    industries, ins = _industries(q)
    concepts, cos = _concept_hits(q)
    tools = _tools(q)
    news = _news(q) if len(q) >= 3 else []
    # group order by best match strength (ties: companies first); weak company matches yield to exact concepts/indices
    screen_like = bool(re.search(r"\b(companies|stocks|shares|with|top|best|highest|lowest)\b", q))
    scores = {"companies": cs if companies else -1, "indices": is_ if indices else -1, "industries": ins if industries else -1,
              "concepts": cos if concepts else -1, "tools": (92 if screen_like else 50) if tools else -1, "news": 10 if news else -1}
    prio = ["companies", "indices", "industries", "concepts", "tools", "news"]
    order = sorted((g for g in prio if scores[g] >= 0), key=lambda g: (-scores[g], prio.index(g)))
    out = {"query": query, "did_you_mean": dym, "companies": companies, "indices": indices, "industries": industries, "concepts": concepts,
           "tools": tools, "news": news, "order": order, "results": companies}
    if len(_CACHE) > 500:
        _CACHE.clear()
    _CACHE[key] = (time.time(), out)
    return out


@router.get("/search")
def search(request: Request, q: str = Query("", max_length=100), limit: int = Query(8, ge=1, le=20)):
    uid = current_user(request)
    LIMITER.check(request, "search", 120, 60)
    t = time.perf_counter()
    out = search_all(q, limit)
    if len(q.strip()) >= 2 and (out["companies"] or out["indices"] or out["industries"] or out["concepts"]):
        db.upsert(db.recent_searches, [{"user_id": uid, "query": q.strip()[:60], "ts": db.utcnow()}], ["user_id", "query"])
    out = {**out, "ms": round((time.perf_counter() - t) * 1000, 1),
           # backward compatible shape for older clients (company picker): industries as {id, name}
           "industries": out["industries"]}
    return clean(out)
