"""News & market intelligence: sectioned, de-duplicated, filterable news with source tiers, saved articles,
related items, a fact-based daily market summary and rule-based "what this means" explanations.

Accuracy rules enforced here:
- Titles, summaries, publishers, links and publication times are shown exactly as the source published them;
  publication time and the time EquityPilot fetched the item are kept separate.
- Official disclosures (NSE, RBI, SEBI feeds) are labelled as such; media reports are labelled as media reports.
- "Breaking" means published within the last 3 hours - older items never appear there.
- The same story from several publishers is shown once, with the other publishers listed.
- Explanations are generic guidance by announcement type, based only on the headline/summary shown.
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from equitypilot import db
from equitypilot.content.industries import BY_ID, industry_of
from equitypilot.data import feeds as N
from equitypilot.data import marketdata as M
from equitypilot.data import repository as repo
from equitypilot.data import source_tiers as ST

from .core import LIMITER, clean, current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/news", tags=["news"])
IST = timezone(timedelta(hours=5, minutes=30))
BREAKING_HOURS = 3

SECTIONS = {
    "top": "Top market news", "breaking": "Breaking business news", "market": "Indian stock market", "company": "Company news",
    "announcements": "Corporate announcements", "results": "Quarterly results", "banking": "Banking & financial services",
    "economy": "Economy & RBI", "regulation": "SEBI & regulation", "sector": "Sector & industry news", "global": "Global markets",
    "commodities": "Commodities & currency", "ipo": "IPO & corporate actions",
}
IMPORTANT_CATS = {"Quarterly results", "Dividend & corporate action", "Acquisition & restructuring", "Credit rating",
                  "Management change", "Litigation & regulatory"}
IPO_RE = re.compile(r"\b(ipo|initial public offer|public issue|listing|offer for sale|rights issue|bonus|split|buy-?back|red herring|drhp)\b", re.I)
TENTATIVE_RE = re.compile(r"\b(likely|may|might|plans?|reportedly|sources said|considering|in talks|mulls|eyes|could|expected to|rumou?r)\b", re.I)
RBI_KEY_RE = re.compile(r"\b(monetary policy|repo rate|policy rate|inflation|crr|slr|cash reserve ratio|penalty|cancell?ation of (licen[cs]e|registration))\b", re.I)
FIN_INDUSTRIES = {"banking", "financial-services"}


# ------------------------------------------------------------------ normalisation
def _clean_summary(title: str, summary: str | None) -> str | None:
    if not summary:
        return None
    import html
    s = html.unescape(html.unescape(summary)).replace("\xa0", " ")
    s = re.sub(r"(?<![a-z])nbsp;", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(rf"^{re.escape(title)}\s+has informed the Exchange (about|regarding)\s*", "", s, flags=re.I)
    s = s.replace("|SUBJECT:", " - Subject:").replace("|", " ").strip(" -")
    if s.lower() == title.lower():
        return None
    return s[:400] + ("…" if len(s) > 400 else "")


def names_tracked() -> list[str]:
    return repo.list_companies()["symbol"].tolist()


def _company_maps() -> tuple[dict, dict]:
    comps = repo.list_companies()
    names = dict(zip(comps["symbol"], comps["name"]))
    inds = {s: industry_of(s, sec, ind) for s, sec, ind in zip(comps["symbol"], comps["sector"], comps["industry"])}
    return names, inds


def _item(*, title, summary, url, source, publisher, published, fetched, feed, category, symbol, names, inds) -> dict:
    primary_feed = feed.startswith(("nse", "rbi", "sebi", "bse"))
    tier = "primary" if primary_feed else ST.tier(publisher or source)
    cat = category or "News"
    if cat == "Market news":
        cat = "Indian market"
    sections = set()
    if feed == "nse_announcements":
        sections |= {"announcements", "company"}
        if cat == "Quarterly results":
            sections.add("results")
        if cat == "Dividend & corporate action" or IPO_RE.search(f"{title} {summary or ''}"):
            sections.add("ipo")
    elif feed == "nse_results":
        sections |= {"results", "company"}
    elif feed.startswith("rbi"):
        sections |= {"economy", "banking"}
    elif feed == "sebi":
        sections.add("regulation")
        if IPO_RE.search(title):
            sections.add("ipo")
    elif feed == "bse_notices":
        sections.add("announcements")
        if IPO_RE.search(title):
            sections.add("ipo")
    elif feed.startswith("media_"):
        sections.add({"Indian market": "market", "Commodities & currency": "commodities", "Banking & financial services": "banking",
                      "IPO & corporate actions": "ipo", "Economy": "economy", "Company news": "company"}.get(cat, "market"))
        if IPO_RE.search(title):
            sections.add("ipo")
    elif feed == "yahoo_market":
        sections.add({"Indian market": "market", "Global markets": "global", "Commodities & currency": "commodities",
                      "Banking & financial services": "banking"}.get(cat, "market"))
        if cat == "Banking & financial services":
            sections.add("market")
        if IPO_RE.search(title):
            sections.add("ipo")
    elif feed == "company":
        sections |= {"company", "sector"}
    ind = inds.get(symbol) if symbol else None
    if ind in FIN_INDUSTRIES:
        sections.add("banking")
    if symbol:
        sections.add("sector")
    important = (primary_feed and cat in IMPORTANT_CATS) or (feed.startswith("rbi") and bool(RBI_KEY_RE.search(title))) \
        or (feed == "sebi" and "circular" in (source or "").lower())
    clean_sum = _clean_summary(title, summary)
    uid = hashlib.sha1(f"{feed}|{url}|{title}".encode()).hexdigest()[:16]
    import html as _html
    title = re.sub(r"(?<![a-z])nbsp;", " ", _html.unescape(_html.unescape(title))).strip()
    return {"id": uid, "title": title, "summary": clean_sum, "url": url, "source": source, "publisher": publisher,
            "tier": tier, "kind": "Official disclosure" if tier == "primary" else "Media report", "category": cat,
            "sections": sorted(sections), "symbol": symbol,
            "company": (names.get(symbol) or (title.strip() if feed.startswith("nse") else None)) if symbol else None,
            "industry": ind, "industry_name": BY_ID.get(ind or "", {}).get("name"),
            "published": published.isoformat() if isinstance(published, datetime) else (str(published) if published else None),
            "fetched_at": fetched.isoformat() if isinstance(fetched, datetime) else (str(fetched) if fetched else None),
            "important": bool(important), "tentative": bool(TENTATIVE_RE.search(title)) and tier != "primary", "also": [],
            "feed_kind": "filing" if feed.startswith(("nse", "bse")) else "media" if feed.startswith(("media_", "yahoo", "company")) else "official"}


FILING_FEEDS = ["nse_announcements", "nse_results"]


_LOAD_CACHE: dict[tuple, tuple[float, list[dict]]] = {}
LOAD_TTL = 45


def _load(days: int, symbols: list[str] | None = None, filings: bool | str = True) -> list[dict]:
    """Cached wrapper: the same window is reused for 45 s across users and sections (feeds refresh every 10-15 min)."""
    import time as _t
    key = (days, tuple(symbols) if symbols else None, filings)
    hit = _LOAD_CACHE.get(key)
    if hit and _t.time() - hit[0] < LOAD_TTL:
        return [{**i, "also": []} for i in hit[1]]
    items = _load_uncached(days, symbols, filings)
    if len(_LOAD_CACHE) > 64:
        _LOAD_CACHE.clear()
    _LOAD_CACHE[key] = (_t.time(), items)
    return [{**i, "also": []} for i in items]


def _load_uncached(days: int, symbols: list[str] | None = None, filings: bool | str = True) -> list[dict]:
    """Items from the last `days` days. Exchange filings (thousands a day) are loaded separately from everything else so
    they can never crowd out media, RBI or SEBI items; with `symbols`, only those companies' filings are loaded.
    filings="important": only important filings (results, dividends, deals, ratings, management, litigation) of tracked
    companies - what the Top and Breaking sections can show."""
    names, inds = _company_maps()
    since = db.utcnow() - timedelta(days=days) if days else None
    n = db.news_items.c

    def q(stmt, limit):
        if since is not None:
            stmt = stmt.where((n.published >= since) | (n.published.is_(None) & (n.fetched_at >= since)))
        return db.read_df(stmt.order_by(n.published.desc().nulls_last()).limit(limit))
    frames = [q(db.select(db.news_items).where(n.feed.notin_(FILING_FEEDS)), 5000)]
    if filings:
        st = db.select(db.news_items).where(n.feed.in_(FILING_FEEDS))
        if symbols:
            st = st.where(n.symbol.in_(symbols))
        if filings == "important":
            st = st.where(n.symbol.in_(list(names)) & n.category.in_(list(IMPORTANT_CATS)))
        frames.append(q(st, 3000))
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True) if any(not f.empty for f in frames) else frames[0]
    df = df.astype(object).where(df.notna(), None)
    out = [_item(title=r["title"], summary=r["summary"], url=r["url"], source=r["source"],
                 publisher=(r["source"] or "").replace(" via Yahoo Finance", "") if r["feed"] == "yahoo_market"
                 else N.FEEDS.get(r["feed"], {}).get("publisher") if r["feed"].startswith("media_") else None,
                 published=r["published"], fetched=r["fetched_at"], feed=r["feed"], category=r["category"], symbol=r["symbol"],
                 names=names, inds=inds) for r in df.to_dict("records")]
    d = db.disclosures.c
    stmt = db.select(db.disclosures).where(d.category == "News")
    if since is not None:
        stmt = stmt.where(d.date >= since)
    if symbols:
        stmt = stmt.where(d.symbol.in_(symbols))
    dd = db.read_df(stmt.order_by(d.date.desc().nulls_last()).limit(3000))
    dd = dd.astype(object).where(dd.notna(), None)
    out += [_item(title=r["title"], summary=None, url=r["url"], source=f"{r['publisher'] or 'Publisher n/a'} via Yahoo Finance",
                  publisher=r["publisher"], published=r["date"], fetched=r["fetched_at"], feed="company", category="Company news",
                  symbol=r["symbol"], names=names, inds=inds) for r in dd.to_dict("records")]
    return out


_TIER_RANK = {"primary": 0, "established": 1, "user": 2, "unrated": 3, "sample": 4}


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 3}


def dedupe(items: list[dict]) -> list[dict]:
    """One entry per story. Exchange filings are distinct when their subject differs (titles there are company names);
    media headlines merge when the wording is (nearly) the same within 48 hours; the most authoritative / earliest
    copy is kept and the other publishers are listed under `also`."""
    def key(it):
        base = re.sub(r"[^a-z0-9]+", " ", it["title"].lower()).strip()[:100]
        return base + "|" + re.sub(r"[^a-z0-9]+", " ", (it["summary"] or "").lower())[:80] if it["tier"] == "primary" else base
    order = sorted(items, key=lambda x: (_TIER_RANK.get(x["tier"], 9), x["published"] or "9999"))
    kept: dict[str, dict] = {}
    media: list[tuple[set, dict]] = []
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


def _age_h(it: dict) -> float:
    if not it.get("published"):
        return 1e6
    try:
        return (db.utcnow() - datetime.fromisoformat(it["published"][:19])).total_seconds() / 3600
    except ValueError:
        return 1e6


CATEGORY_WEIGHT = {"Quarterly results": 2.5, "Acquisition & restructuring": 2.5, "Dividend & corporate action": 1.8, "Credit rating": 1.5,
                   "Litigation & regulatory": 1.2, "Management change": 0.6}


def _score(it: dict, q_words: list[str]) -> float:
    weight = CATEGORY_WEIGHT.get(it["category"], 2.0) if it["important"] else 0
    s = {"primary": 2.0, "established": 1.5}.get(it["tier"], 0.5) + weight
    s += 1.5 if set(it["sections"]) & {"market", "economy", "banking"} and it["feed_kind"] != "filing" else 0
    s += max(0.0, 1.5 - _age_h(it) / 32)                       # fresher is more relevant (fades over ~2 days)
    text = f"{it['title']} {it['summary'] or ''}".lower()
    s += sum(1.5 for w in q_words if w in it["title"].lower()) + sum(0.5 for w in q_words if w in text)
    return s


def _interleave(items: list[dict]) -> list[dict]:
    """Top market news should read like a front page: market stories, important filings and regulator releases mixed,
    each stream keeping its own ranking."""
    buckets = {"media": [], "filing": [], "official": []}
    for i in items:
        buckets.get(i["feed_kind"], buckets["media"]).append(i)
    pattern = ["media", "filing", "media", "official", "filing", "media"]
    out, k = [], 0
    while any(buckets.values()):
        b = pattern[k % len(pattern)]
        if buckets[b]:
            out.append(buckets[b].pop(0))
        k += 1
        if k > 10 * len(items) + 10:
            break
    return out


def build_feed(section: str = "top", q: str | None = None, symbol: str | None = None, industry: str | None = None,
               source: str | None = None, days: int = 7, sort: str = "latest", limit: int = 40, offset: int = 0,
               include_unrated: bool = False, tracked_only: bool = False) -> dict:
    if section not in SECTIONS:
        raise HTTPException(404, "Unknown news section.")
    window = 2 if section in ("top", "breaking") and not days else days
    syms = [symbol] if symbol else (BY_ID[industry]["symbols"] if industry in BY_ID else None)
    if symbol and not symbol.startswith("SAMPLE-"):
        last = db.get_setting(f"company_news:{symbol}")
        if not last or db.utcnow() - datetime.fromisoformat(last) > timedelta(hours=6):   # company headlines: at most every 6 h
            repo.refresh_news(symbol)
            db.set_setting(f"company_news:{symbol}", db.utcnow().isoformat())
    needs_filings: bool | str = "important" if section in ("top", "breaking") and not (symbol or industry) else \
        section in ("top", "breaking", "company", "announcements", "results", "banking", "sector", "ipo")
    items = _load(window if window else 0, syms if section in ("company", "sector") or symbol or industry else None, filings=needs_filings)
    if symbol:
        items = [i for i in items if i["symbol"] == symbol]
    elif industry in BY_ID:
        items = [i for i in items if i["industry"] == industry]
    hidden = sum(1 for i in items if i["tier"] == "unrated")
    if not include_unrated:
        items = [i for i in items if i["tier"] != "unrated"]
    else:
        hidden = 0
    tracked = set(names_tracked())
    def market_moving(i: dict) -> bool:
        if i["feed_kind"] == "filing":
            return i["important"] and i["symbol"] in tracked          # filings: only important ones from tracked companies
        return i["tier"] in ("primary", "established")
    if section == "breaking":
        items = [i for i in items if _age_h(i) <= BREAKING_HOURS and market_moving(i)]
    elif section == "top":
        items = [i for i in items if market_moving(i)]
    elif section != "sector" or not (symbol or industry):
        items = [i for i in items if section in i["sections"]]
    if tracked_only and not symbol:
        tracked_set = set(names_tracked())
        items = [i for i in items if i["feed_kind"] != "filing" or i["symbol"] in tracked_set]
    if source:
        sl = source.lower()
        items = [i for i in items if sl in (i["source"] or "").lower() or sl in (i["publisher"] or "").lower()]
    q_words = [w for w in re.findall(r"[a-z0-9]+", (q or "").lower()) if len(w) >= 2][:6]
    if q_words:
        items = [i for i in items if all(w in f"{i['title']} {i['summary'] or ''} {i['company'] or ''} {i['symbol'] or ''}".lower() for w in q_words)]
    items = dedupe(items)
    facets_sources = sorted({(i["publisher"] or i["source"] or "").replace(" (RSS)", "") for i in items if i["publisher"] or i["source"]})[:40]
    if section == "top" and sort != "latest_only":
        items.sort(key=lambda i: -_score(i, q_words))
        items = _interleave(items)
    elif sort == "relevant":
        items.sort(key=lambda i: -_score(i, q_words))
    else:
        items.sort(key=lambda i: i["published"] or "", reverse=True)
    total = len(items)
    page = items[offset: offset + limit]
    feeds_status = {k: db.get_setting(f"feed_refreshed:{k}") for k in list(N.FEEDS) + ["yahoo_market"]}
    note = None
    if section == "breaking" and not page:
        note = f"Nothing from official or established sources in the last {BREAKING_HOURS} hours. Older stories are under Top market news."
    if section in ("global", "commodities", "market") and not page:
        note = "No recent headlines from established publishers in this category. Headlines come from Yahoo Finance's aggregation of third-party publishers."
    return {"section": section, "title": SECTIONS[section], "items": page, "total": total, "hidden_unrated": hidden,
            "sources": facets_sources, "note": note, "feeds_refreshed": feeds_status, "unrated_note": ST.UNRATED_NOTE,
            "sections": SECTIONS}


@router.get("/feed")
def feed(request: Request, section: str = "top", q: str | None = Query(None, max_length=100), symbol: str | None = None,
         industry: str | None = None, source: str | None = Query(None, max_length=60), days: int = Query(7, ge=0, le=365),
         sort: str = Query("latest", pattern="^(latest|relevant)$"), limit: int = Query(40, ge=1, le=100), offset: int = Query(0, ge=0),
         include_unrated: bool = False, tracked_only: bool = False):
    current_user(request)
    LIMITER.check(request, "news", 120, 60)
    _refresh_in_background()
    return clean(build_feed(section, q, symbol, industry, source, days, sort, limit, offset, include_unrated, tracked_only))


_REFRESHING = threading.Lock()


def _refresh_in_background() -> None:
    """Feeds are TTL-cached and also refreshed by the server's warmer; a page view never waits for a publisher."""
    if _REFRESHING.locked():
        return

    def run():
        with _REFRESHING:
            try:
                N.refresh_all()
            except Exception as exc:
                log.warning("news refresh failed: %s", exc)
    threading.Thread(target=run, name="news-refresh", daemon=True).start()


# ------------------------------------------------------------------ related, saved
@router.get("/related")
def related(request: Request, title: str = Query(..., max_length=500), symbol: str | None = None, limit: int = Query(5, ge=1, le=10)):
    current_user(request)
    items = [i for i in _load(14, [symbol] if symbol else None) if i["tier"] != "unrated" and i["title"] != title]
    if symbol:
        items = [i for i in items if i["symbol"] == symbol]
    else:
        w = _words(title) - {"india", "indian", "market", "markets", "stock", "stocks", "shares", "today", "says"}
        items = [i for i in items if len(w & _words(i["title"])) >= 2]
    items = dedupe(items)
    items.sort(key=lambda i: i["published"] or "", reverse=True)
    return clean({"items": items[:limit]})


class SaveBody(BaseModel):
    url: str = Field(min_length=4, max_length=1000)
    title: str = Field(min_length=1, max_length=500)
    source: str | None = Field(None, max_length=200)
    published: str | None = Field(None, max_length=40)
    symbol: str | None = Field(None, max_length=30)


@router.get("/saved")
def saved(request: Request):
    uid = current_user(request)
    df = db.read_df(db.select(db.saved_news).where(db.saved_news.c.user_id == uid).order_by(db.saved_news.c.saved_at.desc()))
    return clean({"items": df.drop(columns=["user_id"]).to_dict("records") if not df.empty else []})


@router.post("/saved")
def save(body: SaveBody, request: Request):
    uid = current_user(request)
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(400, "Only web links can be saved.")
    try:
        pub = datetime.fromisoformat(body.published[:19]) if body.published else None
    except ValueError:
        pub = None
    db.upsert(db.saved_news, [{"user_id": uid, "url": body.url, "title": body.title, "source": body.source, "published": pub,
                               "symbol": body.symbol, "saved_at": db.utcnow()}], ["user_id", "url"])
    return {"ok": True}


@router.delete("/saved")
def unsave(request: Request, url: str = Query(..., max_length=1000)):
    uid = current_user(request)
    with db.get_engine().begin() as conn:
        conn.execute(db.saved_news.delete().where((db.saved_news.c.user_id == uid) & (db.saved_news.c.url == url)))
    return {"ok": True}


# ------------------------------------------------------------------ daily market summary (facts only)
@router.get("/summary")
def daily_summary(request: Request):
    current_user(request)
    from .routes_market import movers, sectors
    st = M.market_status()
    idx = {i["symbol"]: i for i in M.index_overview()}
    mv = movers(3)
    sec = sectors()
    today = datetime.now(IST).date()
    start_utc = datetime(today.year, today.month, today.day) - timedelta(hours=5, minutes=30)
    from sqlalchemy import func
    n = db.news_items.c

    def count_where(cond) -> int:
        with db.get_engine().connect() as conn:
            return int(conn.execute(db.select(func.count()).select_from(db.news_items).where(cond & (n.published >= start_utc))).scalar() or 0)
    lines = []
    for sym in ("^NSEI", "^BSESN", "^NSEBANK"):
        i = idx.get(sym)
        if i and i.get("change_pct") is not None:
            lines.append({"label": i["name"], "value": i["last"], "change": i["change"], "change_pct": i["change_pct"], "as_of": i["as_of"]})
    b = mv.get("breadth")
    inds = sec.get("industries") or []
    nifty = idx.get("^NSEI")
    if nifty and nifty.get("change_pct") is not None:
        verb = "rose" if nifty["change_pct"] > 0 else "fell" if nifty["change_pct"] < 0 else "was flat"
        session = "today" if (nifty.get("as_of") or "") == today.isoformat() else f"in the last session ({nifty.get('as_of')})"
        headline = f"NIFTY 50 {verb} {abs(nifty['change_pct']) * 100:.2f}% {session} to {nifty['last']:,.2f}."
    else:
        headline = "Index data is not available right now."
    bullets = []
    if b:
        bullets.append(f"Breadth among {mv['universe']} tracked companies: {b['advances']} advanced, {b['declines']} declined.")
    if inds:
        bullets.append(f"Strongest sector: {inds[0]['name']} ({inds[0]['avg_change'] * 100:+.2f}%); weakest: {inds[-1]['name']} ({inds[-1]['avg_change'] * 100:+.2f}%).")
    if mv.get("gainers"):
        g, lo = mv["gainers"][0], (mv.get("losers") or [None])[0]
        bullets.append(f"Top gainer: {g['name']} ({g['change_pct'] * 100:+.2f}%)" + (f"; top loser: {lo['name']} ({lo['change_pct'] * 100:+.2f}%)." if lo else "."))
    filings = {"results": count_where((n.feed == "nse_results") | ((n.feed == "nse_announcements") & (n.category == "Quarterly results"))),
               "announcements": count_where(n.feed.in_(["nse_announcements", "bse_notices"])),
               "rbi": count_where(n.feed.in_(["rbi_press", "rbi_notifications"])), "sebi": count_where(n.feed == "sebi")}
    return clean({"date": today.isoformat(), "phase": st["phase"], "headline": headline, "indices": lines, "bullets": bullets,
                  "filings_today": filings, "status_note": st["note"],
                  "sources": ["Yahoo Finance (delayed index values)", "EquityPilot calculations over tracked companies",
                              "NSE, RBI and SEBI official feeds (counts of today's items)"]})


# ------------------------------------------------------------------ "what this means" (rule-based, no prediction)
GUIDE = {
    "Quarterly results": ("A company has filed its financial results for a quarter.",
                          "Results show how sales, profit and margins moved. Investors compare them with the same quarter last year, the previous quarter and their own expectations.",
                          ["Revenue and profit growth versus last year", "Whether margins widened or narrowed", "One-off gains or losses",
                           "Management's comments on demand and costs"]),
    "Dividend & corporate action": ("The company has announced a dividend, bonus, split, buyback or a related record date.",
                                    "These decide who receives a payout or extra shares. On the ex-date the share price usually adjusts by roughly the value distributed, so it is not a gain or loss by itself.",
                                    ["Record and ex-dates", "Size of the payout relative to the share price", "Whether it is regular or one-off"]),
    "Board meeting": ("The company has given notice of a board meeting.", "Board meetings often approve results, dividends, fund-raising or major decisions; the outcome is filed separately.",
                      ["The agenda stated in the notice", "The outcome filing after the meeting"]),
    "Investor meet & presentation": ("The company has filed an investor presentation, transcript or meeting schedule.",
                                     "Presentations and call transcripts explain management's view of the business; they rarely contain new financial numbers.",
                                     ["Guidance on growth, margins or capex", "Changes in tone compared with earlier calls"]),
    "Credit rating": ("A credit rating agency has rated or re-rated the company's debt.", "Ratings affect how cheaply the company can borrow; downgrades can raise borrowing costs.",
                      ["Direction of the rating action (upgrade, downgrade, reaffirmed)", "Outlook (stable, positive, negative)", "How much debt the company has"]),
    "Acquisition & restructuring": ("The company has disclosed an acquisition, merger, demerger or restructuring.",
                                    "Deals change what the company owns and can affect future earnings, debt and share count.",
                                    ["Price paid relative to the target's profits", "How it is funded (cash, debt, new shares)", "Approvals still required"]),
    "Management change": ("There is a change in directors or senior management.", "Leadership changes can matter when they involve the CEO, CFO or auditors, or are unexplained.",
                          ["Who is leaving or joining, and the stated reason", "Whether it was planned succession"]),
    "Shareholding & insider": ("A shareholding, pledge or insider-trading disclosure has been filed.",
                               "These show what promoters and large holders are doing with their shares; pledging can signal financing pressure.",
                               ["Direction and size of the change", "Whether shares are pledged or released"]),
    "Litigation & regulatory": ("The company has disclosed a legal, tax or regulatory matter.", "The importance depends on the amount involved relative to the company's size and whether it is final.",
                                ["Amount at stake versus annual profit", "Whether the order is final or can be appealed"]),
}


class ExplainBody(BaseModel):
    company: str | None = Field(None, max_length=200)
    title: str = Field(min_length=1, max_length=600)
    summary: str | None = Field(None, max_length=2000)
    source: str | None = Field(None, max_length=200)
    category: str | None = Field(None, max_length=80)
    symbol: str | None = Field(None, max_length=30)
    tier: str | None = Field(None, max_length=20)
    sections: list[str] = []


@router.post("/explain")
def explain(body: ExplainBody, request: Request):
    current_user(request)
    names, inds = _company_maps()
    cat, title, src = body.category or "", body.title, body.source or "the source"
    text = f"{title} {body.summary or ''}"
    who = None
    if body.symbol:
        ind = inds.get(body.symbol)
        who = f"{names.get(body.symbol) or body.company or body.symbol} ({body.symbol})" + (f", in {BY_ID[ind]['name']}" if ind in BY_ID else "") + \
            ". Its peers may also be watched if the news concerns the whole industry."
    if cat in GUIDE:
        what, why, factors = GUIDE[cat]
    elif "economy" in body.sections or cat.startswith("Economy"):
        what = "The Reserve Bank of India has published a press release or notification."
        if re.search(r"\b(vrr?r|reverse repo|liquidity|auction|laf)\b", text, re.I):
            why = "These operations manage how much cash is in the banking system. They influence short-term interest rates rather than signalling a policy change by themselves."
        elif re.search(r"\b(repo rate|monetary policy|policy rate)\b", text, re.I):
            why = "Policy-rate decisions change borrowing costs across the economy and affect banks' margins, loan demand and bond prices."
        else:
            why = "RBI releases can change rules or conditions for banks, NBFCs, borrowers and markets; most are routine."
        factors = ["Whether it is a routine operation or a policy change", "Which institutions it applies to", "The effective date"]
        who = who or "Banks, NBFCs, bond markets and borrowers (depending on the release)."
    elif "regulation" in body.sections:
        what = "SEBI has published a circular, order or press release."
        why = "Circulars change market rules; enforcement orders concern specific entities. Most orders affect only the named parties."
        factors = ["Who the order or circular applies to", "Effective date and transition period", "Whether penalties are final"]
        who = who or "Market participants named in the release (listed companies, intermediaries or individuals)."
    elif "commodities" in body.sections:
        what = "A media report about commodity prices or the rupee."
        why = "Commodity and currency moves change input costs and export earnings - for example crude oil for oil marketers, paints and airlines; the rupee for IT exporters and importers."
        factors = ["Size and persistence of the move", "How much of a company's costs or revenue it touches", "Hedging"]
        who = who or "Companies that use, produce or trade the commodity or currency."
    else:
        what = "A media report about the market or a company."
        why = "Media reports can move sentiment, but material company facts should be confirmed in an official filing."
        factors = ["Whether the company or regulator has confirmed it", "How large the matter is relative to the company", "What was already expected"]
    if body.tier == "primary":
        status = f"Confirmed: an official disclosure published by {src}. Read the linked filing for complete details."
    elif TENTATIVE_RE.search(title):
        status = "Developing / unconfirmed: the headline uses tentative language. Treat it as a report, not a fact, until confirmed in a filing."
    else:
        status = f"Media report by {src}. Check material facts against the company's or regulator's own release."
    return {"what": what, "who": who or "Not specific to one company.", "why": why, "factors": factors, "status": status,
            "note": "General guidance based on the type of item and the headline/summary shown - EquityPilot has not read the full article or filing. "
                    "It is not a prediction of how any share price will react."}
