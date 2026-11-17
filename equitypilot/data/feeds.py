"""News & market-intelligence feeds from official RSS sources and the Yahoo aggregator.

Official feeds (published by the organisations for subscription):
* NSE - corporate announcements, financial results (links to the original filing PDFs), board meetings and
  corporate actions (ex-dates, record dates; used by the Earnings & Results and Corporate Actions pages)
* RBI - press releases, notifications
* SEBI - press releases, circulars, orders (combined RSS)
Third-party: Yahoo Finance headlines for market indices and global benchmarks.
Every item keeps its original link, publisher and publication time.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from collections import defaultdict
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
    "nse_board_meetings": {"url": "https://nsearchives.nseindia.com/content/RSS/Board_Meetings.xml",
                           "source": "NSE India - board meetings (RSS)", "category": "Board meeting", "ttl": 30},
    "nse_corporate_actions": {"url": "https://nsearchives.nseindia.com/content/RSS/Corporate_action.xml",
                              "source": "NSE India - corporate actions (RSS)", "category": "Dividend & corporate action", "ttl": 60},
    "rbi_press": {"url": "https://www.rbi.org.in/pressreleases_rss.xml", "source": "Reserve Bank of India - press releases (RSS)",
                  "category": "Economy & RBI", "ttl": 60},
    "rbi_notifications": {"url": "https://www.rbi.org.in/notifications_rss.xml", "source": "Reserve Bank of India - notifications (RSS)",
                          "category": "Economy & RBI", "ttl": 120},
    "sebi": {"url": "https://www.sebi.gov.in/sebirss.xml", "source": "SEBI (RSS)", "category": "Regulation & SEBI", "ttl": 60},
    "bse_notices": {"url": "https://www.bseindia.com/data/xml/notices.xml", "source": "BSE India - notices (RSS)",
                    "category": "Exchange notice", "ttl": 60},
}

# Established publishers' own RSS feeds (headline + short description + link to the original article), offered by the
# publishers for syndication. Used for personal, non-commercial research with attribution; set EQUITYPILOT_MEDIA_RSS=0
# to switch them off. Articles are never copied - readers follow the link to the publisher.
MEDIA_FEEDS = {
    "media_et_markets": ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "The Economic Times", "Indian market"),
    "media_et_stocks": ("https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms", "The Economic Times", "Indian market"),
    "media_mint_markets": ("https://www.livemint.com/rss/markets", "Mint", "Indian market"),
    "media_bs_markets": ("https://www.business-standard.com/rss/markets-106.rss", "Business Standard", "Indian market"),
    "media_et_commodities": ("https://economictimes.indiatimes.com/markets/commodities/rssfeeds/1808152121.cms", "The Economic Times", "Commodities & currency"),
    "media_et_forex": ("https://economictimes.indiatimes.com/markets/forex/rssfeeds/1150221130.cms", "The Economic Times", "Commodities & currency"),
    "media_et_banking": ("https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms", "The Economic Times", "Banking & financial services"),
    "media_et_ipo": ("https://economictimes.indiatimes.com/markets/ipos/fpos/rssfeeds/14655708.cms", "The Economic Times", "IPO & corporate actions"),
    "media_et_economy": ("https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", "The Economic Times", "Economy"),
    "media_bs_economy": ("https://www.business-standard.com/rss/economy-102.rss", "Business Standard", "Economy"),
    "media_mint_companies": ("https://www.livemint.com/rss/companies", "Mint", "Company news"),
}
if os.environ.get("EQUITYPILOT_MEDIA_RSS", "1") != "0":
    for _k, (_u, _pub, _cat) in MEDIA_FEEDS.items():
        FEEDS[_k] = {"url": _u, "source": f"{_pub} (RSS)", "publisher": _pub, "category": _cat, "ttl": 15}
# Yahoo Finance headline streams (third-party publishers) and the news section each one feeds
MARKET_NEWS_SYMBOLS = {"^NSEI": "Indian market", "^BSESN": "Indian market", "^NSEBANK": "Banking & financial services",
                       "^GSPC": "Global markets", "^IXIC": "Global markets", "CL=F": "Commodities & currency",
                       "GC=F": "Commodities & currency", "USDINR=X": "Commodities & currency"}

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
    """Plain text from an RSS field: decode HTML entities (some feeds double-encode them, e.g. '&amp;nbsp;'),
    drop tags, collapse whitespace. '&' and quotes are kept as characters, never deleted."""
    import html
    t = text or ""
    for _ in range(2):
        t = html.unescape(t)
    t = re.sub(r"<[^>]+>", " ", t).replace("\xa0", " ")
    t = re.sub(r"(?<![a-z])nbsp;", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_rss(content: bytes) -> list[dict]:
    root = ET.fromstring(content)
    items = []
    for it in root.iter("item"):
        items.append({"title": _clean(it.findtext("title")), "link": (it.findtext("link") or "").strip(),
                      "description": _clean(it.findtext("description")), "pubDate": it.findtext("pubDate")})
    return items


FAIL_BACKOFF = timedelta(minutes=10)     # after a failed download, don't ask the publisher again for a while
_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)


def _recent(setting: str, within: timedelta) -> bool:
    ts = db.get_setting(setting)
    return bool(ts) and db.utcnow() - datetime.fromisoformat(ts) < within


def refresh_feed(key: str, force: bool = False) -> tuple[bool, str]:
    cfg = FEEDS[key]
    if not force and _recent(f"feed_refreshed:{key}", timedelta(minutes=cfg["ttl"])):
        return True, "cached"
    if config.OFFLINE:
        return False, "offline"
    if not force and _recent(f"feed_failed:{key}", FAIL_BACKOFF):
        return False, f"{cfg['source']} unavailable (retrying later); showing cached items"
    lock = _locks[key]
    if not lock.acquire(blocking=False):        # another request is already downloading this feed
        return True, "refreshing"
    try:
        return _download_feed(key, cfg)
    finally:
        lock.release()


def _download_feed(key: str, cfg: dict) -> tuple[bool, str]:
    try:
        r = requests.get(cfg["url"], headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        items = parse_rss(r.content)
    except Exception as exc:  # network, HTTP or XML errors (e.g. a truncated download) - keep cached items
        log.warning("feed %s failed (next attempt in %d min): %s", key, FAIL_BACKOFF.seconds // 60, exc)
        db.set_setting(f"feed_failed:{key}", db.utcnow().isoformat())
        return False, f"{cfg['source']} unavailable: {exc}"
    now = db.utcnow()
    names = _name_to_symbol() if key.startswith("nse") else {}
    rows = []
    for it in items:
        if not it["title"]:
            continue
        symbol, category, summary = None, cfg["category"], it["description"][:600]
        if key.startswith("nse"):
            company = it["title"].split(" - Ex-Date")[0] if key == "nse_corporate_actions" else it["title"]
            symbol = names.get(_norm(company))
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
    if not force and last and db.utcnow() - datetime.fromisoformat(last) < timedelta(minutes=30):
        return True, "cached"
    if config.OFFLINE:
        return False, "offline"
    from . import yahoo
    rows, now = [], db.utcnow()
    for sym, cat in MARKET_NEWS_SYMBOLS.items():
        try:
            for n in yahoo.fetch_news(sym):
                rows.append({"feed": "yahoo_market", "category": cat,
                             "title": n["title"][:500], "summary": (n.get("summary") or None), "url": n["url"], "published": n["date"],
                             "source": f"{n['publisher'] or 'Publisher n/a'} via Yahoo Finance", "symbol": None, "fetched_at": now})
        except yahoo.ProviderError:
            continue
    db.upsert(db.news_items, rows, ["feed", "url", "title"])
    db.set_setting("feed_refreshed:yahoo_market", now.isoformat())
    return True, f"{len(rows)} items"


RETENTION_DAYS = {"filings_untracked": 30, "default": 365}


def prune_news(force: bool = False) -> int:
    """Keep the news table bounded. NSE alone files about 9,000 announcements a day: filings of companies EquityPilot
    does not track are kept for 30 days, everything else for a year. Runs at most once a day."""
    if not force and _recent("news_pruned", timedelta(hours=23)):
        return 0
    from sqlalchemy import and_, or_
    n = db.news_items.c
    now = db.utcnow()
    tracked = db.read_df(db.select(db.companies.c.symbol))["symbol"].tolist()
    old_filing = and_(n.feed.in_(["nse_announcements", "nse_results", "bse_notices"]),
                      or_(n.symbol.is_(None), n.symbol.notin_(tracked) if tracked else n.symbol.isnot(None)),
                      n.published < now - timedelta(days=RETENTION_DAYS["filings_untracked"]))
    very_old = n.published < now - timedelta(days=RETENTION_DAYS["default"])
    with db.get_engine().begin() as conn:
        removed = conn.execute(db.news_items.delete().where(or_(old_filing, very_old))).rowcount or 0
    db.set_setting("news_pruned", now.isoformat())
    if removed:
        log.info("pruned %d old news items", removed)
    return removed


def refresh_all(force: bool = False) -> dict[str, str]:
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as ex:          # feeds are independent; fetch them in parallel
        res = dict(zip(FEEDS, ex.map(lambda k: refresh_feed(k, force)[1], list(FEEDS))))
    out = dict(res)
    out["yahoo_market"] = refresh_market_news(force)[1]
    try:
        prune_news()
    except Exception as exc:                       # housekeeping must never break a refresh
        log.warning("news prune failed: %s", exc)
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
