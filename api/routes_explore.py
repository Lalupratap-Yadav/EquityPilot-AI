"""Explore markets, Industry Intelligence Centre, screener (incl. saved screens) and comparison."""
from __future__ import annotations

import json
import logging
import threading
import time

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from equitypilot import config, db
from equitypilot.analytics import bank as B
from equitypilot.analytics.screener import METRIC_COLUMNS, PRESETS, apply_filters, company_metrics, universe_metrics
from equitypilot.content.industries import BY_ID, INDUSTRIES, industry_of
from equitypilot.content.learning import MODULES
from equitypilot.data import feeds as N
from equitypilot.data import marketdata as M
from equitypilot.data import repository as repo
from equitypilot.data import securities as S

from .core import clean, current_user, not_found
from .routes_market import universe_snapshot

router = APIRouter(prefix="/api", tags=["explore"])
log = logging.getLogger("equitypilot.api")

COLLECTIONS = [
    {"id": "quality", "title": "Quality compounders", "description": "ROE and ROCE above 15%, low debt, 8%+ revenue CAGR",
     "preset": "Quality compounders"},
    {"id": "debt-free", "title": "Low-debt value", "description": "P/E under 20, debt/equity under 0.3, ROE above 10%",
     "preset": "Low-debt value"},
    {"id": "growth", "title": "High growth", "description": "Revenue and profit both growing 15%+ year on year", "preset": "High growth"},
    {"id": "cash", "title": "Cash generators", "description": "Cash from operations ≥ 90% of profit and FCF margin above 8%",
     "preset": "Cash generators"},
    {"id": "dividend", "title": "Dividend payers", "description": "Dividend yield above 2% with net margin above 8%",
     "preset": "Dividend payers"},
]


# ------------------------------------------------------------------ universe metrics (stale-while-revalidate)
# Computing ratios for the whole universe takes minutes (≈1 s per company), so the last result is kept in memory and
# on disk, served immediately, and recomputed in the background; only one computation runs at a time.
METRICS_TTL = 600
_SNAPSHOT = config.DATA_DIR / "cache" / "universe_metrics.json"
_mf_lock = threading.Lock()          # held while computing
_mf_state: dict = {"df": None, "at": 0.0}


def _compute_metrics() -> pd.DataFrame:
    df = universe_metrics()
    df["industry_id"] = [industry_of(s, sec, ind) for s, sec, ind in zip(df["symbol"], df["sector"], df["industry"])]
    cats = S.category_map()
    df["category"] = [cats.get(s.rsplit(".", 1)[0], (None, None))[0] if not s.startswith("SAMPLE-") else None for s in df["symbol"]]
    return df


def _refresh_metrics() -> pd.DataFrame | None:
    if not _mf_lock.acquire(blocking=False):
        return None                  # another thread is already computing
    try:
        df = _compute_metrics()
        _mf_state.update(df=df, at=time.time())
        try:
            _SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            tmp = _SNAPSHOT.with_suffix(".tmp")
            tmp.write_text(df.to_json(orient="records", date_format="iso"), encoding="utf-8")
            tmp.replace(_SNAPSHOT)
        except OSError as exc:
            log.warning("could not save metrics snapshot: %s", exc)
        return df
    finally:
        _mf_lock.release()


def _load_snapshot() -> pd.DataFrame | None:
    try:
        df = pd.DataFrame(json.loads(_SNAPSHOT.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
    if df.empty or "symbol" not in df:
        return None
    df["is_sample"] = df["is_sample"].astype(bool)
    _mf_state.update(df=df, at=_SNAPSHOT.stat().st_mtime)
    return df


def metrics_frame(wait: bool = False) -> pd.DataFrame:
    """Universe metrics. Returns cached (possibly stale) data at once and refreshes in the background;
    blocks only when nothing has ever been computed, or when wait=True (background warmer)."""
    df = _mf_state["df"] if _mf_state["df"] is not None else _load_snapshot()
    fresh = df is not None and time.time() - _mf_state["at"] < METRICS_TTL
    if fresh:
        return df
    if df is None or wait:
        out = _refresh_metrics()
        if out is not None:
            return out
        with _mf_lock:               # someone else is computing - wait for their result
            pass
        return _mf_state["df"] if _mf_state["df"] is not None else _compute_metrics()
    if not _mf_lock.locked():
        threading.Thread(target=_refresh_metrics, name="metrics-refresh", daemon=True).start()
    return df


def invalidate_metrics() -> None:
    """Mark metrics stale (e.g. after a company is tracked or refreshed); the next read triggers a background refresh."""
    _mf_state["at"] = 0.0


metrics_frame.cache_clear = invalidate_metrics  # type: ignore[attr-defined]


def _cards(df: pd.DataFrame, n: int = 12) -> list[dict]:
    snap = {r["symbol"]: r for r in universe_snapshot()}
    out = []
    for _, r in df.head(n).iterrows():
        q = snap.get(r["symbol"], {})
        out.append({"symbol": r["symbol"], "name": r["name"], "industry": r.get("industry_id"), "category": r.get("category"),
                    "market_cap": r.get("market_cap"), "pe": r.get("pe"), "roe": r.get("roe"),
                    "price": q.get("price") or r.get("price"), "change_pct": q.get("change_pct"), "status": q.get("status")})
    return out


@router.get("/explore")
def explore(request: Request):
    uid = current_user(request)
    df = metrics_frame()
    real = df[~df["is_sample"]].sort_values("market_cap", ascending=False)
    collections = []
    for c in COLLECTIONS:
        hits = apply_filters(real, PRESETS[c["preset"]])
        collections.append({**c, "companies": _cards(hits, 12), "count": len(hits)})
    cats = []
    for cat in ("Large Cap", "Mid Cap", "Small Cap"):
        sub = real[real["category"] == cat]
        cats.append({"category": cat, "tracked": len(sub), "companies": _cards(sub, 12),
                     "listed": int(db.read_df(db.select(db.securities.c.isin).where(db.securities.c.category == cat)).shape[0])})
    views = db.read_df(db.select(db.recent_views.c.symbol))
    trending = views["symbol"].value_counts().head(12).index.tolist() if not views.empty else []
    trend_df = real[real["symbol"].isin(trending)]
    fav = db.read_df(db.select(db.fav_industries.c.industry).where(db.fav_industries.c.user_id == uid))["industry"].tolist()
    return clean({
        "collections": collections, "categories": cats, "trending": _cards(trend_df, 12),
        "featured": _cards(real, 10), "favourite_industries": fav,
        "topics": [{"id": m["id"], "title": m["title"], "summary": m["summary"]} for m in MODULES],
        "categories_as_of": db.get_setting("securities_as_of"),
        "note": "Collections are rule-based screens on EquityPilot's tracked universe - they are not recommendations.",
    })


@router.get("/industries")
def industries(request: Request):
    uid = current_user(request)
    df = metrics_frame()
    snap = pd.DataFrame(universe_snapshot())
    fav = set(db.read_df(db.select(db.fav_industries.c.industry).where(db.fav_industries.c.user_id == uid))["industry"])
    idx = {i["industry"]: i for i in M.index_overview() if i["kind"] == "sector"}
    out = []
    for ind in INDUSTRIES:
        sub = df[df["industry_id"] == ind["id"]]
        s2 = snap[snap["industry"] == ind["id"]] if not snap.empty else snap
        w = s2["market_cap"].fillna(0) if not s2.empty else pd.Series(dtype=float)
        day = float((s2["change_pct"].fillna(0) * w).sum() / w.sum()) if not s2.empty and w.sum() else None
        out.append({"id": ind["id"], "name": ind["name"], "icon": ind["icon"], "overview": ind["overview"],
                    "companies": len(sub), "market_cap": float(sub["market_cap"].sum()) if len(sub) else None,
                    "median_pe": float(sub["pe"].median()) if sub["pe"].notna().any() else None,
                    "median_roe": float(sub["roe"].median()) if sub["roe"].notna().any() else None,
                    "day_change": day, "index": idx.get(ind["id"]), "favourite": ind["id"] in fav})
    return clean({"industries": out})


@router.get("/industries/{iid}")
def industry(iid: str, request: Request):
    current_user(request)
    ind = BY_ID.get(iid)
    if not ind:
        raise not_found("Industry")
    df = metrics_frame()
    sub = df[df["industry_id"] == iid].sort_values("market_cap", ascending=False)
    snap = {r["symbol"]: r for r in universe_snapshot()}
    rows = []
    for _, r in sub.iterrows():
        q = snap.get(r["symbol"], {})
        row = {"symbol": r["symbol"], "name": r["name"], "category": r["category"], "price": q.get("price"),
               "change_pct": q.get("change_pct"), **{k: r.get(k) for k in ind["compare_metrics"]}}
        if ind.get("bank_metrics"):
            bm = repo.get_bank_metrics(r["symbol"])
            for k in ("gnpa", "nnpa", "crar", "casa", "nim"):
                row[k] = B.latest(bm, k)
        rows.append(row)
    news = N.query(symbols=ind["symbols"], limit=25)
    yahoo = repo.get_disclosures(None, limit=400)
    if not yahoo.empty:
        yahoo = yahoo[yahoo["symbol"].isin(ind["symbols"]) & (yahoo["category"] == "News")].head(15)
    idx = next((i for i in M.index_overview() if i.get("industry") == iid), None)
    metric_defs = {k: {"label": METRIC_COLUMNS[k][0], "kind": METRIC_COLUMNS[k][1]} for k in ind["compare_metrics"]}
    if ind.get("bank_metrics"):
        metric_defs.update({k: {"label": B.BANK_METRICS[k][0], "kind": "pctpt"} for k in ("gnpa", "nnpa", "crar", "casa", "nim")})
    return clean({**{k: ind[k] for k in ("id", "name", "icon", "overview", "drivers", "trends", "risks", "valuation", "disclosure_kpis")},
                  "metrics": metric_defs, "companies": rows, "index": idx,
                  "announcements": news.to_dict("records"),
                  "news": yahoo.to_dict("records") if not yahoo.empty else [],
                  "editorial_note": "Industry overview, drivers, trends and risks are EquityPilot editorial background "
                                    "(general and educational, not real-time). Company figures are from the data sources shown."})


@router.post("/industries/{iid}/favourite")
def toggle_favourite(iid: str, request: Request):
    uid = current_user(request)
    if iid not in BY_ID:
        raise not_found("Industry")
    have = db.read_df(db.select(db.fav_industries).where(db.fav_industries.c.user_id == uid).where(db.fav_industries.c.industry == iid))
    if have.empty:
        db.upsert(db.fav_industries, [{"user_id": uid, "industry": iid}], ["user_id", "industry"])
        return {"favourite": True}
    db.execute(db.delete(db.fav_industries).where(db.fav_industries.c.user_id == uid).where(db.fav_industries.c.industry == iid))
    return {"favourite": False}


# ------------------------------------------------------------------ screener
@router.get("/screener")
def screener_data(request: Request):
    current_user(request)
    df = metrics_frame()
    snap = {r["symbol"]: r for r in universe_snapshot()}
    df = df.assign(change_pct=[snap.get(s, {}).get("change_pct") for s in df["symbol"]])
    return clean({"rows": df.to_dict("records"), "metrics": {k: {"label": v[0], "kind": v[1]} for k, v in METRIC_COLUMNS.items()},
                  "presets": PRESETS, "industries": [{"id": i["id"], "name": i["name"]} for i in INDUSTRIES]})


class Screen(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    filters: dict


@router.get("/screens")
def list_screens(request: Request):
    uid = current_user(request)
    df = db.read_df(db.select(db.saved_screens).where(db.saved_screens.c.user_id == uid).order_by(db.saved_screens.c.id.desc()))
    return clean([{**r, "filters": json.loads(r["filters"])} for r in df.to_dict("records")])


@router.post("/screens")
def save_screen(body: Screen, request: Request):
    uid = current_user(request)
    if len(json.dumps(body.filters)) > 5000:
        raise HTTPException(400, "Filter definition too large.")
    res = db.execute(db.insert(db.saved_screens).values(user_id=uid, name=body.name.strip(), filters=json.dumps(body.filters),
                                                        created_at=db.utcnow()))
    return {"id": int(res.inserted_primary_key[0])}


@router.delete("/screens/{sid}")
def delete_screen(sid: int, request: Request):
    uid = current_user(request)
    db.execute(db.delete(db.saved_screens).where(db.saved_screens.c.id == sid).where(db.saved_screens.c.user_id == uid))
    return {"deleted": sid}


@router.get("/compare")
def compare(symbols: str, request: Request):
    current_user(request)
    syms = [s for s in symbols.split(",") if s][:5]
    rows = [company_metrics(s) for s in syms if repo.get_company(s)]
    series = {}
    for s in syms:
        fd = repo.get_financials(s, auto_refresh=False)
        if not fd.empty:
            r = fd.get("revenue").dropna()
            if len(r) and r.iloc[0] > 0:
                series[s] = {"revenue_index": [{"label": f"FY{pd.Timestamp(p).year}", "value": float(v / r.iloc[0] * 100)} for p, v in r.items()]}
        p = repo.get_prices(s, auto_refresh=False)
        if not p.empty:
            p = p[p["date"] >= p["date"].max() - pd.Timedelta(days=365)]
            series.setdefault(s, {})["price_index"] = [{"date": str(d.date()), "value": float(v / p["close"].iloc[0] * 100)}
                                                      for d, v in zip(p["date"], p["close"])]
    return clean({"rows": rows, "series": series, "metrics": {k: {"label": v[0], "kind": v[1]} for k, v in METRIC_COLUMNS.items()}})
