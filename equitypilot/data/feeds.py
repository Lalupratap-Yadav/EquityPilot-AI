"""News & market-intelligence feeds from official RSS sources and the Yahoo aggregator.

Official feeds (published by the organisations for subscription):
* NSE - corporate announcements, financial results (links to the original filing PDFs)
* RBI - press releases, notifications
* SEBI - press releases, circulars, orders (combined RSS)
Third-party: Yahoo Finance headlines for market indices and global benchmarks.
Every item keeps its original link, publisher and publication time.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import pandas as pd
import requests
from defusedxml import ElementTree as ET

from .. import config, db
from .securities import USER_AGENT

log = logging.getLogger(__name__)

FEEDS = {
    "nse_announcements": {"url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
                          "source": "NSE India - corporate announcements (RSS)", "category": "Exchange disclosure", "ttl": 10},
    "nse_results": {"url": "https://nsearchives.nseindia.com/content/RSS/Financial_Results.xml",
                    "source": "NSE India - financial results (RSS)", "category": "Quarterly results", "ttl": 30},
    "rbi_press": {"url": "https://www.rbi.org.in/pressreleases_rss.xml", "source": "Reserve Bank of India - press releases (RSS)",
                  "category": "Economy & RBI", "ttl": 60},
    "rbi_notifications": {"url": "https://www.rbi.org.in/notifications_rss.xml", "source": "Reserve Bank of India - notifications (RSS)",
                          "category": "Economy & RBI", "ttl": 120},
    "sebi": {"url": "https://www.sebi.gov.in/sebirss.xml", "source": "SEBI (RSS)", "category": "Regulation & SEBI", "ttl": 60},
}
MARKET_NEWS_SYMBOLS = {"^NSEI": "Indian market", "^BSESN": "Indian market", "^GSPC": "Global", "CL=F": "Global", "USDINR=X": "Global"}

SUBJECT_TAGS = [
    ("Quarterly results", ["financial result", "outcome of board meeting", "results"]),
    ("Dividend & corporate action", ["dividend", "bonus", "split", "buyback", "record date", "rights"]),
    ("Board meeting", ["board meeting", "intimation"]),
    ("Investor meet & presentation", ["investor presentation", "analysts/institutional investor meet", "con. call", "earnings call"]),
    ("Credit rating", ["credit rating"]),
    ("Acquisition & restructuring", ["acquisition", "amalgamation", "merger", "scheme of arrangement", "demerger"]),
    ("Management change", ["change in directors", "change in management", "appointment", "resignation", "cessation"]),
    ("Shareholding & insider", ["shareholding", "sast", "insider", "pledge", "regulation 31", "regulation 29"]),
    ("Litigation & regulatory", ["litigation", "dispute", "penalty", "order", "show cause"]),
]


def tag_subject(text: str) -> str:
    t = (text or "").lower()
    for tag, words in SUBJECT_TAGS:
        if any(w in t for w in words):
            return tag
    return "General update"


def _norm(name: str) -> str:
    n = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    n = re.sub(r"\b(limited|ltd|the|india|co|company|corporation|corp)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _name_to_symbol() -> dict[str, str]:
    m = {}
    sec = db.read_df(db.select(db.securities.c.name, db.securities.c.nse_symbol).where(db.securities.c.nse_symbol.isnot(None)))
    for _, r in sec.iterrows():
        m[_norm(r["name"])] = f"{r['nse_symbol']}.NS"
    comp = db.read_df(db.select(db.companies.c.name, db.companies.c.symbol))
    for _, r in comp.iterrows():
        m[_norm(r["name"])] = r["symbol"]
    return m


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S", "%d %b %Y %H:%M:%S %z",
                "%d %b, %Y %z", "%d %b %Y"):
        try:
            d = datetime.strptime(s, fmt)
            if d.tzinfo:
                return d.astimezone(tz=None).replace(tzinfo=None) - (datetime.now().astimezone().utcoffset() or timedelta())
            return d - timedelta(hours=5, minutes=30)      # feeds publish IST; store UTC
        except ValueError:
            continue
    try:
        t = pd.Timestamp(s)
        return (t.tz_convert(None) if t.tzinfo else t - pd.Timedelta(hours=5, minutes=30)).to_pydatetime()
    except (ValueError, TypeError):
        return None


def _clean(text: str | None) -> str:
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = re.sub(r"&#?\w+;", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_rss(content: bytes) -> list[dict]:
    root = ET.fromstring(content)
    items = []
    for it in root.iter("item"):
        items.append({"title": _clean(it.findtext("title")), "link": (it.findtext("link") or "").strip(),
                      "description": _clean(it.findtext("description")), "pubDate": it.findtext("pubDate")})
    return items


def refresh_feed(key: str, force: bool = False) -> tuple[bool, str]:
    cfg = FEEDS[key]
    last = db.get_setting(f"feed_refreshed:{key}")
    if not force and last and datetime.utcnow() - datetime.fromisoformat(last) < timedelta(minutes=cfg["ttl"]):
        return True, "cached"
    if config.OFFLINE:
        return False, "offline"
    try:
        r = requests.get(cfg["url"], headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        items = parse_rss(r.content)
    except Exception as exc:  # network, HTTP or XML errors - keep cached items
        log.warning("feed %s failed: %s", key, exc)
        return False, f"{cfg['source']} unavailable: {exc}"
    now = db.utcnow()
    names = _name_to_symbol() if key.startswith("nse") else {}
    rows = []
    for it in items:
        if not it["title"]:
            continue
        symbol, category, summary = None, cfg["category"], it["description"][:600]
        if key.startswith("nse"):
            symbol = names.get(_norm(it["title"]))
            if key == "nse_announcements":
                subj = it["description"].split("SUBJECT:")[-1].strip() if "SUBJECT:" in it["description"] else it["description"]
                category = tag_subject(subj)
        source = cfg["source"]
        if key == "sebi":
            if not it["title"].strip("� ") and it["description"]:
                it["title"] = it["description"][:300]
            link = it["link"].lower()
            kind = ("circular" if "/circulars/" in link else "enforcement order" if "/enforcement/" in link
                    else "press release" if "press-release" in link else "update")
            source = f"SEBI - {kind} (RSS)"
        rows.append({"feed": key, "category": category, "title": it["title"][:500], "summary": summary,
                     "url": it["link"] or None, "published": _parse_date(it["pubDate"]), "source": source,
                     "symbol": symbol, "fetched_at": now})
    db.upsert(db.news_items, rows, ["feed", "url", "title"])
    db.set_setting(f"feed_refreshed:{key}", now.isoformat())
    return True, f"{len(rows)} items"


def refresh_market_news(force: bool = False) -> tuple[bool, str]:
    last = db.get_setting("feed_refreshed:yahoo_market")
    if not force and last and datetime.utcnow() - datetime.fromisoformat(last) < timedelta(minutes=30):
        return True, "cached"
    if config.OFFLINE:
        return False, "offline"
    from . import yahoo
    rows, now = [], db.utcnow()
    for sym, cat in MARKET_NEWS_SYMBOLS.items():
        try:
            for n in yahoo.fetch_news(sym):
                rows.append({"feed": "yahoo_market", "category": "Global markets" if cat == "Global" else "Market news",
                             "title": n["title"][:500], "summary": None, "url": n["url"], "published": n["date"],
                             "source": f"{n['publisher'] or 'Publisher n/a'} via Yahoo Finance", "symbol": None, "fetched_at": now})
        except yahoo.ProviderError:
            continue
    db.upsert(db.news_items, rows, ["feed", "url", "title"])
    db.set_setting("feed_refreshed:yahoo_market", now.isoformat())
    return True, f"{len(rows)} items"


def refresh_all(force: bool = False) -> dict[str, str]:
    out = {k: refresh_feed(k, force)[1] for k in FEEDS}
    out["yahoo_market"] = refresh_market_news(force)[1]
    return out


def query(feeds: list[str] | None = None, category: str | None = None, symbols: list[str] | None = None,
          q: str | None = None, limit: int = 60) -> pd.DataFrame:
    n = db.news_items.c
    stmt = db.select(db.news_items)
    if feeds:
        stmt = stmt.where(n.feed.in_(feeds))
    if category:
        stmt = stmt.where(n.category == category)
    if symbols:
        stmt = stmt.where(n.symbol.in_(symbols))
    if q:
        stmt = stmt.where(n.title.ilike(f"%{q}%") | n.summary.ilike(f"%{q}%"))
    return db.read_df(stmt.order_by(n.published.desc().nulls_last(), n.id.desc()).limit(limit))
