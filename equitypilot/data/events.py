"""Earnings & Results calendar and Corporate Actions, built only from official exchange filings (plus labelled
third-party dividend/split history).

Official sources (RSS feeds NSE publishes for subscription; every item links to NSE):
* Board meetings feed and 'Board Meeting Intimation' announcements: the date a company's board will meet and the
  stated purpose (for example "to consider and approve the financial results for the quarter ended September 2026").
* 'Outcome of Board Meeting' / 'Financial Results' announcements and the financial-results feed: results actually filed.
* Corporate actions feed: purpose, ex-date and record date set by the exchange (dividends, bonus, split, rights, buyback).
Third-party: dividend and split history from Yahoo Finance (ex-dates and per-share amounts) for tracked companies.

Accuracy rules
* A result date is shown only when a board-meeting intimation states it - EquityPilot never estimates one. Each entry
  says which filing it came from and links to it.
* EquityPilot has no source of analyst estimates, so it shows no earnings "surprise".
* The feeds are rolling (each shows only the latest items). EquityPilot keeps what it has collected since it started
  reading them, so older periods may be incomplete; the pages say so.
* Payment dates are not in the exchange feed; they are left blank ("see the filing"), never guessed.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from .. import db

IST = timezone(timedelta(hours=5, minutes=30))
NSE_ACTIONS_PAGE = "https://www.nseindia.com/companies-listing/corporate-filings-actions"
NSE_BOARD_PAGE = "https://www.nseindia.com/companies-listing/corporate-filings-board-meetings"
NSE_RESULTS_PAGE = "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"

_DATE_RE = r"(\d{1,2}-[A-Za-z]{3}-\d{4})"
_HELD_RE = re.compile(r"(?:board meeting to be held on|meeting date:?)\s*" + _DATE_RE, re.I)
_PERIOD_RE = re.compile(r"((?:quarter(?:ly)?|half[- ]year(?:ly)?|nine months|year|period)\s+ended\s+(?:on\s+)?(?:the\s+)?"
                        r"(?:\d{1,2}(?:st|nd|rd|th)?\s+)?[A-Za-z]+\.?(?:\s+\d{1,2},?)?\s*,?\s*\d{4})", re.I)
_RESULTS_RE = re.compile(r"financial results?|\bresults\b", re.I)


_INFORMED_RE = re.compile(r"^\s*has (informed|submitted to) the Exchange( about| regarding| that)?\s*", re.I)


def _strip_company(summary: str, company: str) -> str:
    """'X Limited has informed the Exchange about ...' -> '...'."""
    s = summary.strip()
    if company and s.lower().startswith(company.lower()):
        s = _INFORMED_RE.sub("", s[len(company):])
    return s.strip(" ,")


def today_ist() -> date:
    return datetime.now(IST).date()


def _d(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%d-%b-%Y").date()
    except ValueError:
        return None


def _company_maps() -> tuple[dict[str, str], dict[str, str | None]]:
    from ..content.industries import industry_of
    from . import repository as repo
    comps = repo.list_companies()
    names = dict(zip(comps["symbol"], comps["name"]))
    inds = {s: industry_of(s, sec, ind) for s, sec, ind in zip(comps["symbol"], comps["sector"], comps["industry"])}
    return names, inds


def _iso(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, (datetime, pd.Timestamp)):
        return pd.Timestamp(x).isoformat()
    return str(x)


_ROWS_CACHE: dict[tuple, tuple[float, list[dict]]] = {}
ROWS_TTL = 60          # seconds; the feeds themselves refresh every 10-60 minutes


def _rows(feeds: list[str], since: datetime | None = None, extra=None, symbol: str | None = None, cache_key: str | None = None) -> list[dict]:
    import time as _t
    key = (tuple(feeds), since.date().isoformat() if since else None, cache_key, symbol)
    if cache_key:
        hit = _ROWS_CACHE.get(key)
        if hit and _t.time() - hit[0] < ROWS_TTL:
            return hit[1]
    rows = _rows_uncached(feeds, since, extra, symbol)
    if cache_key:
        if len(_ROWS_CACHE) > 64:
            _ROWS_CACHE.clear()
        _ROWS_CACHE[key] = (_t.time(), rows)
    return rows


def _rows_uncached(feeds: list[str], since: datetime | None, extra, symbol: str | None) -> list[dict]:
    n = db.news_items.c
    stmt = db.select(db.news_items).where(n.feed.in_(feeds))
    if symbol:
        stmt = stmt.where(n.symbol == symbol)
    if since is not None:
        stmt = stmt.where((n.published >= since) | n.published.is_(None))
    if extra is not None:
        stmt = stmt.where(extra)
    df = db.read_df(stmt.order_by(n.published.desc().nulls_last()).limit(20000))
    return df.astype(object).where(df.notna(), None).to_dict("records") if not df.empty else []


def _subject(summary: str | None) -> str:
    s = summary or ""
    return s.split("SUBJECT:")[-1].strip() if "SUBJECT:" in s else ""


def _purpose(summary: str | None) -> str:
    """The purpose text of a board-meeting intimation, without the boilerplate around it."""
    s = (summary or "").split("|SUBJECT:")[0]
    s = re.sub(r"^.*?board meeting to be held on\s*" + _DATE_RE + r"\s*", "", s, flags=re.I)
    s = re.sub(r"\|?\s*meeting date:?\s*" + _DATE_RE, "", s, flags=re.I)
    s = re.sub(r"^(to\s+)?(inter-?alia\s+)?", "", s.strip(), flags=re.I)
    s = re.sub(r"\s+\.", ".", s).strip(" .|")
    return (s[:1].upper() + s[1:])[:300] if s else "Purpose not stated in the feed"


def _period(text: str | None) -> str | None:
    m = _PERIOD_RE.search(text or "")
    if not m:
        return None
    p = re.sub(r"\s+", " ", m.group(1)).strip(" ,")
    return p[:1].upper() + p[1:]


# ------------------------------------------------------------------ earnings & results
def board_meetings(since_days: int = 120, symbol: str | None = None) -> list[dict]:
    """Board meetings with a stated date, merged per company and meeting date (the board-meetings feed and the
    announcement often report the same meeting)."""
    names, inds = _company_maps()
    since = db.utcnow() - timedelta(days=since_days)
    rows = _rows(["nse_board_meetings"], since, symbol=symbol, cache_key="bm") +         [r for r in _rows(["nse_announcements"], since, db.news_items.c.category == "Board meeting", symbol, cache_key="bm_ann")
         if _subject(r["summary"]).lower().startswith("board meeting intimation")]
    merged: dict[tuple, dict] = {}
    for r in rows:
        m = _HELD_RE.search(r["summary"] or "")
        meet = _d(m.group(1)) if m else None
        if not meet:
            continue
        company = (r["title"] or "").strip()
        key = (r["symbol"] or company.lower(), meet)
        purpose = _purpose(r["summary"])
        results = bool(_RESULTS_RE.search(purpose))
        src = {"label": "NSE board-meetings feed" if r["feed"] == "nse_board_meetings" else "NSE corporate announcement",
               "url": r["url"] or NSE_BOARD_PAGE, "filed": _iso(r["published"])}
        if key in merged:
            e = merged[key]
            if src["url"] not in {x["url"] for x in e["sources"]}:
                e["sources"].append(src)
            e["filed"] = min(filter(None, [e["filed"], src["filed"]]), default=None)
            e["results"] = e["results"] or results
            if len(purpose) > len(e["purpose"]) and not purpose.startswith("Purpose not"):
                e["purpose"] = purpose
            continue
        sym = r["symbol"]
        merged[key] = {"company": names.get(sym) or company, "symbol": sym, "tracked": sym in names,
                       "industry": inds.get(sym) if sym else None, "meeting_date": meet.isoformat(), "purpose": purpose,
                       "period": _period(r["summary"]), "results": results, "filed": src["filed"], "sources": [src],
                       "status": "confirmed", "status_label": "Confirmed - date stated in the company's board-meeting intimation"}
    return list(merged.values())


def results_filed(since_days: int = 120, symbol: str | None = None) -> list[dict]:
    """Results actually filed: 'Outcome of Board Meeting' / 'Financial Results' announcements and the results feed.
    Delay notices are reported separately (kind='delay')."""
    names, inds = _company_maps()
    since = db.utcnow() - timedelta(days=since_days)
    out = []
    for r in _rows(["nse_announcements", "nse_results"], since, db.news_items.c.category == "Quarterly results", symbol, cache_key="res"):
        subj = _subject(r["summary"]).lower()
        if r["feed"] == "nse_results":
            kind = "results"
        elif "delay" in subj or "non-submission" in subj:
            kind = "delay"
        elif subj.startswith("outcome of board meeting") or "financial result" in subj or _RESULTS_RE.search(r["summary"] or ""):
            kind = "results"
        else:
            continue
        sym = r["symbol"]
        summ = (r["summary"] or "").split("|SUBJECT:")[0]
        summ = _strip_company(summ, (r["title"] or "").strip())
        out.append({"company": names.get(sym) or (r["title"] or "").strip(), "symbol": sym, "tracked": sym in names,
                    "industry": inds.get(sym) if sym else None, "filed": _iso(r["published"]), "kind": kind,
                    "subject": _subject(r["summary"]) or ("Financial results" if r["feed"] == "nse_results" else ""),
                    "detail": summ[:400] or None, "period": _period(r["summary"]),
                    "basis": ("Consolidated" if "CONSOLIDATED:Consolidated" in (r["summary"] or "") else
                              "Standalone" if "Non-Consolidated" in (r["summary"] or "") else None),
                    "url": r["url"] or NSE_RESULTS_PAGE,
                    "source": "NSE financial-results feed" if r["feed"] == "nse_results" else "NSE corporate announcement"})
    return out


def results_calendar(view: str = "upcoming", q: str | None = None, industry: str | None = None, tracked_only: bool = False,
                     start: date | None = None, end: date | None = None, results_only: bool = True) -> dict:
    today = today_ist()
    meets = board_meetings()
    filed = results_filed()
    by_company: dict[str, list[dict]] = {}
    for f in filed:
        if f["kind"] == "results":
            by_company.setdefault(f["symbol"] or f["company"].lower(), []).append(f)
    for e in meets:
        md = date.fromisoformat(e["meeting_date"])
        later = [f for f in by_company.get(e["symbol"] or e["company"].lower(), [])
                 if f["filed"] and pd.Timestamp(f["filed"]).date() >= md - timedelta(days=1)]
        if md > today:
            e["state"] = "upcoming"
        elif later:
            e["state"] = "filed"
            e["results_filing"] = {"url": later[-1]["url"], "filed": later[-1]["filed"], "subject": later[-1]["subject"]}
        else:
            e["state"] = "awaiting" if md >= today - timedelta(days=3) else "not_seen"
        e["state_label"] = {"upcoming": "Upcoming", "filed": "Results filed", "awaiting": "Meeting held - filing not seen yet",
                            "not_seen": "Results filing not seen in the feed"}[e["state"]]

    def keep(e: dict) -> bool:
        if tracked_only and not e.get("tracked"):
            return False
        if industry and e.get("industry") != industry:
            return False
        if q:
            ql = q.lower()
            if ql not in (e.get("company") or "").lower() and ql not in (e.get("symbol") or "").lower():
                return False
        return True
    if view == "recent":
        items = [f for f in filed if keep(f)]
        items.sort(key=lambda f: f["filed"] or "", reverse=True)
    else:
        items = [e for e in meets if keep(e) and (e["results"] or not results_only)]
        if view == "upcoming":
            items = [e for e in items if e["meeting_date"] >= today.isoformat()]
        if start:
            items = [e for e in items if e["meeting_date"] >= start.isoformat()]
        if end:
            items = [e for e in items if e["meeting_date"] <= end.isoformat()]
        items.sort(key=lambda e: (e["meeting_date"], e["company"]), reverse=view == "past")
    last = {k: db.get_setting(f"feed_refreshed:{k}") for k in ("nse_board_meetings", "nse_announcements", "nse_results")}
    first = db.read_df(db.select(db.news_items.c.published).where(db.news_items.c.feed.in_(["nse_board_meetings", "nse_announcements"]))
                       .order_by(db.news_items.c.published).limit(1))
    collected_since = _iso(first["published"].iloc[0]) if not first.empty else None
    return {"view": view, "today": today.isoformat(), "items": items, "total": len(items),
            "counts": {"upcoming": sum(1 for e in meets if e["state"] == "upcoming" and e["results"]),
                       "filed_recent": sum(1 for f in filed if f["kind"] == "results"),
                       "tracked_upcoming": sum(1 for e in meets if e["state"] == "upcoming" and e["results"] and e["tracked"])},
            "collected_since": collected_since, "feeds_refreshed": last,
            "sources": [{"label": "NSE board meetings (RSS)", "url": NSE_BOARD_PAGE, "tier": "OFFICIAL"},
                        {"label": "NSE corporate announcements (RSS)", "url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements", "tier": "OFFICIAL"},
                        {"label": "NSE financial results (RSS)", "url": NSE_RESULTS_PAGE, "tier": "OFFICIAL"}],
            "notes": ["Dates come only from companies' board-meeting intimations filed with NSE; EquityPilot never estimates a result date.",
                      "No analyst-estimate source is connected, so no earnings surprise is shown.",
                      "The exchange feeds show only their latest items. EquityPilot keeps what it has collected"
                      + (f" since {pd.Timestamp(collected_since).strftime('%d %b %Y')}" if collected_since else "")
                      + ", so earlier periods may be incomplete."]}


def company_events(symbol: str) -> dict:
    meets = board_meetings(400, symbol)
    filed = results_filed(400, symbol)
    acts = exchange_actions(400, symbol)
    meets.sort(key=lambda e: e["meeting_date"], reverse=True)
    filed.sort(key=lambda f: f["filed"] or "", reverse=True)
    return {"symbol": symbol, "board_meetings": meets, "results_filed": filed, "actions": acts,
            "history": provider_actions(symbol)}


# ------------------------------------------------------------------ corporate actions
ACTION_TYPES = {
    "dividend": ("Dividend", "A cash payment to shareholders out of profits. You receive it if you hold the shares at the end "
                 "of the day before the ex-date. On the ex-date the share price usually falls by about the dividend amount, "
                 "so the payout is not a gain by itself."),
    "bonus": ("Bonus issue", "Free extra shares in a fixed ratio (for example 1:1 = one new share for each share held). The "
              "share price adjusts on the ex-date, so the value of your holding does not change."),
    "split": ("Stock split", "Each share is divided into several shares of a lower face value (for example ₹10 into five of ₹2). "
              "You hold more shares at a proportionally lower price; the value of your holding does not change."),
    "rights": ("Rights issue", "Existing shareholders may buy new shares, usually at a discount, in proportion to what they hold. "
               "It is optional; not taking part dilutes your share of the company."),
    "buyback": ("Buyback", "The company buys back its own shares, often at a premium, through a tender offer or the market. "
                "Holders on the record date may offer shares; acceptance is usually proportional."),
    "merger": ("Merger / demerger", "A scheme that combines companies or separates a business into a new company. Shareholders "
               "receive shares in the resulting company in the approved ratio."),
    "distribution": ("REIT / InvIT distribution", "A payout by a real-estate or infrastructure trust (interest, dividend or "
                     "capital repayment) to unit holders on the record date."),
    "meeting": ("Shareholder meeting", "An annual or extraordinary general meeting, or a postal ballot, where shareholders vote."),
    "debt": ("Bond / debenture payment", "Interest or redemption on a listed debt security, not on the equity shares."),
    "other": ("Other action", "Another corporate action. Read the exchange record for details."),
}


def classify_action(purpose: str, series: str | None = None) -> str:
    p = (purpose or "").upper()
    if series and series not in ("EQ", "BE", "BZ", "SM", "ST", "RR", "IV") and re.search(r"INTEREST|REDEMPTION", p):
        return "debt"
    if re.search(r"INTEREST PAYMENT|REDEMPTION|COUPON", p) and "DIVIDEND" not in p:
        return "debt"
    if re.search(r"DISTRIBUTION|INCOME DISTRIBUTION", p) or series in ("RR", "IV"):
        return "distribution"
    if "BONUS" in p:
        return "bonus"
    if re.search(r"SPLIT|SUB-?DIVISION", p):
        return "split"
    if "RIGHTS" in p:
        return "rights"
    if re.search(r"BUY ?-?BACK", p):
        return "buyback"
    if re.search(r"DEMERGER|AMALGAMATION|MERGER|SCHEME OF ARRANGEMENT", p):
        return "merger"
    if "DIVIDEND" in p or re.search(r"\bDIV\b", p):
        return "dividend"
    if re.search(r"ANNUAL GENERAL MEETING|\bAGM\b|\bEGM\b|POSTAL BALLOT", p):
        return "meeting"
    return "other"


def _parse_fields(desc: str) -> dict[str, str]:
    out = {}
    for part in (desc or "").split("|"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().upper()] = v.strip()
    return out


def _amount(purpose: str) -> float | None:
    m = re.search(r"\b(?:RS|RE|INR)\.?\s*([\d]+(?:\.\d+)?)\s*/?-?\s*PER\s+(?:SHARE|UNIT)", purpose or "", re.I)
    return float(m.group(1)) if m else None


def _ratio(purpose: str) -> str | None:
    m = re.search(r"(\d+)\s*:\s*(\d+)", purpose or "")
    return f"{m.group(1)}:{m.group(2)}" if m else None


def _split_terms(purpose: str) -> str | None:
    """'From Rs 10/- Per Share To Rs 2/- Per Share' -> 'Face value ₹10 → ₹2 (each share becomes 5)'."""
    m = re.search(r"FROM\s+(?:RS|RE)\.?\s*([\d.]+).*?TO\s+(?:RS|RE)\.?\s*([\d.]+)", purpose or "", re.I)
    if not m:
        return None
    a, b = float(m.group(1)), float(m.group(2))
    if b <= 0:
        return None
    f = a / b
    return f"Face value ₹{a:g} → ₹{b:g} (each share becomes {f:g})"


def exchange_actions(since_days: int = 400, symbol: str | None = None) -> list[dict]:
    """Corporate actions from the NSE corporate-actions feed (exchange-set ex-date and record date)."""
    names, inds = _company_maps()
    since = db.utcnow() - timedelta(days=since_days)
    out, seen = [], set()
    for r in _rows(["nse_corporate_actions"], since, symbol=symbol, cache_key="ca"):
        title = (r["title"] or "").strip()
        company = title.split(" - Ex-Date")[0].strip()
        m = re.search(r"Ex-Date:\s*" + _DATE_RE, title)
        ex = _d(m.group(1)) if m else None
        f = _parse_fields(r["summary"] or "")
        purpose = f.get("PURPOSE", "")
        series = f.get("SERIES")
        typ = classify_action(purpose, series)
        rec = _d(f.get("RECORD DATE"))
        key = (company.lower(), ex, purpose)
        if key in seen:
            continue
        seen.add(key)
        sym = r["symbol"]
        out.append({"company": names.get(sym) or company, "symbol": sym, "tracked": sym in names,
                    "industry": inds.get(sym) if sym else None, "type": typ, "type_label": ACTION_TYPES[typ][0],
                    "purpose": purpose.title() if purpose.isupper() else purpose, "series": series,
                    "ex_date": ex.isoformat() if ex else None, "record_date": rec.isoformat() if rec else None,
                    "book_closure": (f"{f.get('BOOK CLOSURE START DATE')} to {f.get('BOOK CLOSURE END DATE')}"
                                     if f.get("BOOK CLOSURE START DATE", "-") not in ("-", "") else None),
                    "face_value": f.get("FACE VALUE"), "amount": _amount(purpose) if typ in ("dividend", "distribution") else None,
                    "ratio": _ratio(purpose) if typ in ("bonus", "rights") else _split_terms(purpose) if typ == "split" else None,
                    "payment_date": None, "announced": _iso(r["published"]),
                    "status": "confirmed", "status_label": "Ex-date set by the exchange",
                    "source": "NSE corporate-actions feed", "tier": "OFFICIAL", "url": NSE_ACTIONS_PAGE})
    return out


def board_announcements(since_days: int = 60) -> list[dict]:
    """Board decisions on dividends, bonus, splits and buybacks filed as announcements (before the exchange sets dates)."""
    names, inds = _company_maps()
    since = db.utcnow() - timedelta(days=since_days)
    out = []
    for r in _rows(["nse_announcements"], since, db.news_items.c.category == "Dividend & corporate action", cache_key="ca_ann"):
        subj = _subject(r["summary"])
        typ = classify_action(subj + " " + (r["summary"] or ""))
        if typ == "debt" or "/debt/" in (r["url"] or ""):
            continue
        sym = r["symbol"]
        detail = (r["summary"] or "").split("|SUBJECT:")[0]
        detail = _strip_company(detail, (r["title"] or "").strip())
        out.append({"company": names.get(sym) or (r["title"] or "").strip(), "symbol": sym, "tracked": sym in names,
                    "industry": inds.get(sym) if sym else None, "type": typ, "type_label": ACTION_TYPES[typ][0],
                    "subject": subj, "detail": detail[:400] or None, "filed": _iso(r["published"]),
                    "status": "announced", "status_label": "Announced in a filing - check the filing for dates",
                    "source": "NSE corporate announcement", "tier": "OFFICIAL", "url": r["url"]})
    out.sort(key=lambda a: a["filed"] or "", reverse=True)
    return out


def provider_actions(symbol: str | None = None, limit: int = 400) -> list[dict]:
    """Dividend and split history from the market-data provider (THIRD-PARTY; amounts adjusted for later splits/bonuses)."""
    c = db.corporate_actions.c
    stmt = db.select(db.corporate_actions)
    if symbol:
        stmt = stmt.where(c.symbol == symbol)
    df = db.read_df(stmt.order_by(c.date.desc()).limit(limit))
    out = []
    for r in df.to_dict("records"):
        typ = "split" if r["type"] == "split" else "dividend"
        out.append({"symbol": r["symbol"], "type": typ, "type_label": ACTION_TYPES[typ][0], "ex_date": _iso(r["date"]),
                    "value": r["value"], "source": r["source"], "tier": "THIRD-PARTY",
                    "note": ("Split factor (shares after / before); bonus issues appear as splits."
                             if typ == "split" else "Per-share amount as reported by the provider, adjusted for later splits and bonus issues.")})
    return out


def actions_centre(when: str = "upcoming", typ: str | None = None, q: str | None = None, industry: str | None = None,
                   tracked_only: bool = False, equity_only: bool = True) -> dict:
    today = today_ist().isoformat()
    acts = exchange_actions()
    if equity_only:
        acts = [a for a in acts if a["type"] not in ("debt",)]

    def keep(a: dict) -> bool:
        if typ and a["type"] != typ:
            return False
        if tracked_only and not a.get("tracked"):
            return False
        if industry and a.get("industry") != industry:
            return False
        if q:
            ql = q.lower()
            if ql not in (a.get("company") or "").lower() and ql not in (a.get("symbol") or "").lower():
                return False
        return True
    acts = [a for a in acts if keep(a)]
    if when == "upcoming":
        acts = [a for a in acts if (a["ex_date"] or "") >= today]
        acts.sort(key=lambda a: (a["ex_date"] or "", a["company"]))
    else:
        acts = [a for a in acts if (a["ex_date"] or "") < today]
        acts.sort(key=lambda a: (a["ex_date"] or ""), reverse=True)
    ann = [a for a in board_announcements() if keep(a)]
    counts: dict[str, int] = {}
    for a in exchange_actions():
        if (a["ex_date"] or "") >= today and a["type"] != "debt":
            counts[a["type"]] = counts.get(a["type"], 0) + 1
    return {"when": when, "today": today, "items": acts, "total": len(acts), "announcements": ann[:60],
            "counts_upcoming": counts, "types": {k: {"label": v[0], "explain": v[1]} for k, v in ACTION_TYPES.items()},
            "feeds_refreshed": {k: db.get_setting(f"feed_refreshed:{k}") for k in ("nse_corporate_actions", "nse_announcements")},
            "sources": [{"label": "NSE corporate actions (RSS)", "url": NSE_ACTIONS_PAGE, "tier": "OFFICIAL"},
                        {"label": "NSE corporate announcements (RSS)", "url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements", "tier": "OFFICIAL"},
                        {"label": "Yahoo Finance dividend and split history (company pages)", "url": None, "tier": "THIRD-PARTY"}],
            "notes": ["Ex-dates and record dates are those set by the exchange. Payment dates are not in the exchange feed - see the company's filing.",
                      "Announcements are board decisions filed before the exchange sets the dates; they are not confirmed ex-dates.",
                      "The exchange feed shows only its latest items; EquityPilot keeps what it has collected, so older periods may be incomplete."]}
