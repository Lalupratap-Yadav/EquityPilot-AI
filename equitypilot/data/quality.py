"""Data Quality & Source Transparency: where every dataset comes from, how fresh it is and what is missing.

Labels (shown in the UI exactly as below)
  OFFICIAL     exchange, regulator or company filing        SECONDARY    established media publisher
  THIRD-PARTY  data aggregator (Yahoo Finance)              DELAYED      price that may lag the market by 15+ minutes
  HISTORICAL   past data as reported by the stated source   CALCULATED   computed by EquityPilot from the data shown
  ASSUMPTION   user-editable model input                    SAMPLE       fictional demonstration data
  USER-ENTERED typed in by a user from a cited filing

Freshness is judged against how often each dataset changes (a quote within a trading day, statements within a
quarter or a year). Missing data is reported as missing - it is never counted as zero.
"""
from __future__ import annotations

import pandas as pd

from .. import config, db
from . import feeds as N

LABELS = {
    "OFFICIAL": "Primary source: exchange, regulator or company filing",
    "SECONDARY": "Established media publisher reporting on events",
    "THIRD-PARTY": "Data aggregator (Yahoo Finance) - verify material figures with official filings",
    "DELAYED": "Market price that may lag the exchange by 15 minutes or more",
    "HISTORICAL": "Past data as reported by the stated source",
    "CALCULATED": "Computed by EquityPilot from the data shown, with the formula stated",
    "ASSUMPTION": "A model input you can change - not a reported figure",
    "SAMPLE": "Fictional demonstration data - not a real company",
    "USER-ENTERED": "Typed in by a user from a cited filing",
}

FEED_TIER = {"nse": "OFFICIAL", "bse": "OFFICIAL", "rbi": "OFFICIAL", "sebi": "OFFICIAL", "media": "SECONDARY",
             "yahoo": "THIRD-PARTY"}


def _age_hours(ts) -> float | None:
    if not ts:
        return None
    try:
        t = pd.Timestamp(ts)
    except (TypeError, ValueError):
        return None
    if t.tzinfo is not None:
        t = t.tz_convert(None)
    return (pd.Timestamp(db.utcnow()) - t).total_seconds() / 3600


def _fresh(age_h: float | None, ok_h: float, stale_h: float) -> str:
    if age_h is None:
        return "missing"
    return "fresh" if age_h <= ok_h else "ageing" if age_h <= stale_h else "stale"


def feeds_status() -> list[dict]:
    from sqlalchemy import func
    n = db.news_items.c
    counts = {r["feed"]: r for r in db.read_df(db.select(n.feed, func.count().label("items"), func.max(n.published).label("newest"))
                                              .group_by(n.feed)).to_dict("records")}
    out = []
    for key, cfg in list(N.FEEDS.items()) + [("yahoo_market", {"source": "Yahoo Finance headlines (third-party publishers)", "ttl": 30,
                                                               "url": "https://finance.yahoo.com"})]:
        last = db.get_setting(f"feed_refreshed:{key}")
        failed = db.get_setting(f"feed_failed:{key}")
        age = _age_hours(last)
        ttl_h = cfg.get("ttl", 30) / 60
        failing = bool(failed and (not last or failed > last))
        state = "failing" if failing else _fresh(age, max(1.0, ttl_h * 4), 24)
        c = counts.get(key) or {}
        name = f"{cfg['publisher']} - {cfg['category'].lower()}" if cfg.get("publisher") else cfg["source"].replace(" (RSS)", "")
        out.append({"key": key, "source": name, "url": cfg.get("url"),
                    "tier": FEED_TIER.get(key.split("_")[0], "THIRD-PARTY"), "refresh_minutes": cfg.get("ttl"),
                    "last_refreshed": last, "last_failed": failed, "state": state, "items_stored": int(c.get("items") or 0),
                    "newest_item": c.get("newest")})
    return out


def market_data_status() -> dict:
    from . import marketdata as M
    p = M.provider()
    realtime = type(p).__name__ == "KiteConnectProvider"
    q = db.read_df(db.select(db.quotes.c.symbol, db.quotes.c.fetched_at))
    ages = [a for a in (_age_hours(t) for t in q["fetched_at"]) if a is not None] if not q.empty else []
    return {"provider": "Zerodha Kite Connect (real-time quotes)" if realtime else "Yahoo Finance (delayed)",
            "tier": "OFFICIAL" if realtime else "DELAYED", "realtime": realtime,
            "quotes_stored": int(len(q)), "quotes_within_1d": sum(1 for a in ages if a <= 24),
            "newest_quote": str(q["fetched_at"].max()) if not q.empty else None,
            "note": ("Real-time quotes come from your own Kite Connect app; chart history still comes from Yahoo Finance."
                     if realtime else "Prices may lag the exchange by 15 minutes or more. Real-time NSE/BSE prices need a licensed "
                                      "vendor or a broker API linked to your own account (see docs/MARKET_DATA.md).")}


def statements_overview() -> dict:
    """Coverage of financial statements across tracked (non-sample) companies, with EPS and completeness checks."""
    from . import repository as repo
    comps = repo.list_companies()
    comps = comps[~comps["is_sample"].astype(bool)] if not comps.empty else comps
    from sqlalchemy import text
    agg = db.read_df(text(
        "SELECT symbol, period_type, COUNT(DISTINCT period_end) AS n, MAX(period_end) AS latest, MAX(fetched_at) AS fetched "
        "FROM financials GROUP BY symbol, period_type"))
    by = {(r["symbol"], r["period_type"]): r for r in agg.to_dict("records")} if not agg.empty else {}
    rows = []
    for sym, name in zip(comps["symbol"], comps["name"]):
        a, q = by.get((sym, "annual"), {}), by.get((sym, "quarterly"), {})
        rows.append({"symbol": sym, "name": name, "annual_years": int(a.get("n") or 0), "latest_fy": a.get("latest"),
                     "quarters": int(q.get("n") or 0), "latest_quarter": q.get("latest"),
                     "fetched_at": max(filter(None, [a.get("fetched"), q.get("fetched")]), default=None)})
    df = pd.DataFrame(rows)
    eps_flags = _eps_warnings(df["symbol"].tolist() if not df.empty else [])
    return {"companies": int(len(df)),
            "with_3y_annual": int((df["annual_years"] >= 3).sum()) if not df.empty else 0,
            "with_quarterly": int((df["quarters"] > 0).sum()) if not df.empty else 0,
            "no_statements": df[df["annual_years"] == 0]["symbol"].tolist() if not df.empty else [],
            "eps_warnings": eps_flags[:40], "eps_warning_count": len(eps_flags),
            "basis_note": "Yahoo Finance does not state whether its statements are consolidated or standalone. Uploaded "
                          "statements from annual reports record their basis.",
            "rows": rows}


def _eps_warnings(symbols: list[str]) -> list[dict]:
    """The EPS consistency check of analytics.ratios.eps_checks for many companies with one query and one pivot."""
    from ..analytics import ratios as R
    from . import repository as repo
    f = db.financials.c
    df = db.read_df(db.select(f.symbol, f.period_end, f.line_item, f.value)
                    .where(f.period_type == "annual").where(f.symbol.in_(symbols))
                    .where(f.line_item.in_(["eps_basic", "eps_diluted", "net_income", "shares_diluted"])))
    out: list[dict] = []
    if df.empty:
        return out
    w = df.pivot_table(index=["symbol", "period_end"], columns="line_item", values="value", aggfunc="last")
    for sym, g in w.groupby(level=0):
        wide = g.droplevel(0).T
        wide = wide.reindex(columns=sorted(wide.columns))
        fd = repo.FinancialData(wide=wide, period_type="annual", basis="")
        out += [{"symbol": sym, **chk} for chk in R.eps_checks(fd) if chk["level"] == "warning"]
    return out


_PQ_CACHE: dict = {"t": 0.0, "v": None}


def platform_quality(max_age: float = 300) -> dict:
    """Cached for 5 minutes: statement coverage changes at most a few times a day."""
    import time as _t
    if _PQ_CACHE["v"] is not None and _t.time() - _PQ_CACHE["t"] < max_age:
        feeds = feeds_status()
        return {**_PQ_CACHE["v"], "feeds": feeds, "feeds_failing": [f["key"] for f in feeds if f["state"] == "failing"],
                "feeds_stale": [f["key"] for f in feeds if f["state"] == "stale"]}
    v = _platform_quality()
    _PQ_CACHE.update({"t": _t.time(), "v": v})
    return v


def _platform_quality() -> dict:
    feeds = feeds_status()
    return {"generated_at": db.utcnow().isoformat(), "offline": config.OFFLINE, "labels": LABELS,
            "feeds": feeds, "feeds_failing": [f["key"] for f in feeds if f["state"] == "failing"],
            "feeds_stale": [f["key"] for f in feeds if f["state"] == "stale"],
            "market_data": market_data_status(), "statements": statements_overview(),
            "securities": {"count": int(db.read_df(db.select(db.securities.c.isin)).shape[0]),
                           "as_of": db.get_setting("securities_as_of"),
                           "source": "AMFI market-cap list and NSE equity list (official)"},
            "rules": ["Missing values are shown as missing ('—'), never as zero.",
                      "A ratio is left blank when one of its inputs is missing or not meaningful (for example P/E with a loss).",
                      "Every price carries its status (DELAYED, LIVE or SAMPLE) and timestamp.",
                      "Company news is attached to a company only when the exchange names it or the company is clearly named "
                      "in the headline or summary.",
                      "Result dates and corporate-action dates come only from exchange filings; nothing is estimated."]}


def company_coverage(symbol: str, uid: int | None = None) -> dict:
    """What EquityPilot holds for one company, with source, period, freshness and gaps. Uploaded documents are counted
    only when the viewing user may read them (their own uploads and shared ones)."""
    from ..analytics import ratios as R
    from . import repository as repo
    c = repo.get_company(symbol) or {}
    sample = bool(c.get("is_sample"))
    financial = R.is_financial(c)
    fd = repo.get_financials(symbol, auto_refresh=False)
    fq = repo.get_financials(symbol, "quarterly", auto_refresh=False)
    px = repo.get_prices(symbol, auto_refresh=False)
    quote = repo.get_quote(symbol) or {}
    sh = db.read_df(db.select(db.shareholding).where(db.shareholding.c.symbol == symbol))
    bm = repo.get_bank_metrics(symbol) if financial else pd.DataFrame()
    acts = db.read_df(db.select(db.corporate_actions.c.date).where(db.corporate_actions.c.symbol == symbol))
    dc = db.documents.c
    docs = db.read_df(db.select(dc.id).where(dc.symbol == symbol).where(dc.user_id.is_(None) | (dc.user_id == (uid if uid is not None else -1))))
    filings = db.read_df(db.select(db.news_items.c.published).where(db.news_items.c.symbol == symbol)
                         .where(db.news_items.c.feed.in_(["nse_announcements", "nse_results", "nse_board_meetings"]))
                         .order_by(db.news_items.c.published.desc()).limit(1))
    tp = "SAMPLE" if sample else None

    def item(key, label, available, tier, period=None, fetched=None, ok_h=24.0, stale_h=24 * 7, note=None, applicable=True):
        age = _age_hours(fetched)
        state = "not_applicable" if not applicable else ("missing" if not available else
                                                         ("fresh" if fetched is None else _fresh(age, ok_h, stale_h)))
        return {"key": key, "label": label, "available": bool(available), "tier": tp or tier, "period": period,
                "fetched_at": str(fetched) if fetched is not None else None, "state": state, "note": note, "applicable": applicable}
    latest_fy = pd.Timestamp(fd.periods[-1]) if not fd.empty else None
    latest_q = pd.Timestamp(fq.periods[-1]) if not fq.empty else None
    missing_items = [k for k in ("revenue", "net_income", "total_equity", "total_debt", "cfo", "eps_diluted")
                     if not fd.empty and pd.isna(fd.get(k).iloc[-1])]
    items = [
        item("quote", "Latest price", bool(quote.get("price") or quote.get("last")), "DELAYED", None, quote.get("fetched_at"), 24, 72,
             "Delayed quote from Yahoo Finance; the page header shows its exact time."),
        item("prices", "Price history", not px.empty, "HISTORICAL",
             f"{pd.Timestamp(px['date'].min()).date()} to {pd.Timestamp(px['date'].max()).date()}" if not px.empty else None,
             None, note="Daily closes as reported by Yahoo Finance (split-adjusted by the provider)."),
        item("annual", "Annual statements", not fd.empty, "THIRD-PARTY",
             f"{len(fd.periods)} years, latest FY ending {latest_fy.strftime('%b %Y')}" if latest_fy is not None else None,
             fd.fetched_at, 24 * 120, 24 * 400,
             ("Missing in the latest year: " + ", ".join(missing_items) + "." if missing_items else None)),
        item("quarterly", "Quarterly results", not fq.empty, "THIRD-PARTY",
             f"{len(fq.periods)} quarters, latest {latest_q.strftime('%b %Y')}" if latest_q is not None else None,
             fq.fetched_at, 24 * 45, 24 * 120),
        item("shareholding", "Shareholding pattern", not sh.empty, "USER-ENTERED",
             f"{sh['period'].nunique()} period(s), latest {sh['period'].max()}" if not sh.empty and "period" in sh else None,
             None, note=None if not sh.empty else "No free licensed source; enter it from the exchange filing on the Shareholding tab."),
        item("bank", "Bank metrics (NPA, CRAR, CASA)", not bm.empty, "USER-ENTERED",
             f"latest {bm['period'].max()}" if not bm.empty and "period" in bm else None, None,
             note=None if not bm.empty else "Enter from the bank's quarterly disclosure on the Bank metrics tab.", applicable=financial),
        item("actions", "Dividends and splits", not acts.empty, "THIRD-PARTY",
             f"{len(acts)} records, latest ex-date {pd.Timestamp(acts['date'].max()).date()}" if not acts.empty else None, None),
        item("filings", "Exchange filings", not filings.empty, "OFFICIAL",
             f"latest {pd.Timestamp(filings['published'].iloc[0]).strftime('%d %b %Y')}" if not filings.empty and filings['published'].iloc[0] is not None else None,
             None, note=None if not filings.empty else "No NSE filing collected for this company since EquityPilot started reading the feeds."),
    ]
    if not docs.empty:
        items.append(item("documents", "Uploaded documents", True, "OFFICIAL", f"{len(docs)} document(s)", None))
    applicable = [i for i in items if i["applicable"]]
    have = sum(1 for i in applicable if i["available"])
    checks = R.quality_checks(fd) if not fd.empty else []
    return {"symbol": symbol, "sample": sample, "is_financial": financial, "items": items,
            "available": have, "applicable": len(applicable), "coverage_pct": have / len(applicable) if applicable else None,
            "basis": fd.basis if not fd.empty else None,
            "basis_note": ("The provider does not state whether statements are consolidated or standalone."
                           if not fd.empty and (fd.basis or "").lower() in ("", "unspecified", "unknown") else None),
            "currency": fd.currency if not fd.empty else "INR", "units": "₹ crore for amounts; per-share figures in ₹",
            "checks": checks}


def stale_warning(ts, kind: str = "quote") -> str | None:
    """Short warning text when a timestamp is older than expected for its kind."""
    age = _age_hours(ts)
    if age is None:
        return None
    limits = {"quote": 72, "statements": 24 * 400}
    if age > limits.get(kind, 72):
        days = age / 24
        return f"Last updated {days:.0f} days ago"
    return None

