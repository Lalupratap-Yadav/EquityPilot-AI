"""Market overview, movers, breadth, sector performance, quotes, charts and WebSocket quote stream."""
from __future__ import annotations

import asyncio
import logging
import threading
import time

import pandas as pd
from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect

from equitypilot import db
from equitypilot.analytics import technicals as T
from equitypilot.content.industries import BY_ID, industry_of
from equitypilot.data import marketdata as M
from equitypilot.data import repository as repo

from .core import LIMITER, clean, current_user, ttl_cache

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["market"])


def tracked_real() -> list[str]:
    c = repo.list_companies()
    return [s for s in c["symbol"] if not s.startswith("SAMPLE-")]


@ttl_cache(30)
def universe_snapshot() -> list[dict]:
    comps = repo.list_companies()
    comps = comps[~comps["is_sample"].astype(bool)]
    quotes = M.QUOTES.get(comps["symbol"].tolist(), stale_ok=True)   # background warmer keeps these fresh
    qdb = db.read_df(db.select(db.quotes.c.symbol, db.quotes.c.market_cap))
    mcap = dict(zip(qdb["symbol"], qdb["market_cap"]))
    out = []
    for _, c in comps.iterrows():
        q = quotes.get(c["symbol"], {})
        out.append({"symbol": c["symbol"], "name": c["name"], "sector": c["sector"],
                    "industry": industry_of(c["symbol"], c["sector"], c["industry"]),
                    "market_cap": mcap.get(c["symbol"]), **{k: q.get(k) for k in ("price", "change", "change_pct", "volume", "time", "status")}})
    return out


@router.get("/market/overview")
def overview():
    idx = M.index_overview()
    return clean({"status": M.market_status(), "indices": idx,
                  "source": "Yahoo Finance (via yfinance) - delayed / end-of-day; index values are not real-time"})


@router.get("/market/movers")
def movers(n: int = Query(6, ge=1, le=20)):
    rows = [r for r in universe_snapshot() if r.get("change_pct") is not None]
    df = pd.DataFrame(rows)
    if df.empty:
        return {"gainers": [], "losers": [], "active": [], "breadth": None, "universe": 0}
    for col in ("price", "change_pct", "volume"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df["turnover"] = df["price"] * df["volume"].fillna(0)
    adv, dec = int((df["change_pct"] > 0).sum()), int((df["change_pct"] < 0).sum())
    return clean({
        "gainers": df.nlargest(n, "change_pct").to_dict("records"), "losers": df.nsmallest(n, "change_pct").to_dict("records"),
        "active": df.nlargest(n, "turnover").to_dict("records"),
        "breadth": {"advances": adv, "declines": dec, "unchanged": int(len(df) - adv - dec),
                    "median_change": float(df["change_pct"].median())},
        "universe": len(df), "latest_time": df["time"].dropna().max(),
        "note": f"Computed over the {len(df)} companies tracked in EquityPilot, not the whole exchange.",
    })


@router.get("/market/sectors")
def sectors():
    df = pd.DataFrame([r for r in universe_snapshot() if r.get("change_pct") is not None])
    out = []
    if not df.empty:
        for iid, g in df.groupby("industry"):
            if iid not in BY_ID:
                continue
            w = g["market_cap"].fillna(0)
            wavg = float((g["change_pct"] * w).sum() / w.sum()) if w.sum() else float(g["change_pct"].mean())
            out.append({"industry": iid, "name": BY_ID[iid]["name"], "companies": len(g), "avg_change": wavg,
                        "advances": int((g["change_pct"] > 0).sum()), "declines": int((g["change_pct"] < 0).sum())})
    idx = [i for i in M.index_overview() if i["kind"] == "sector"]
    return clean({"industries": sorted(out, key=lambda x: -x["avg_change"]), "indices": idx,
                  "note": "Industry moves are market-cap-weighted averages of tracked companies (delayed prices)."})


@router.get("/quotes")
def quotes(symbols: str):
    syms = [s.strip() for s in symbols.split(",") if s.strip()][:60]
    return clean({"quotes": M.QUOTES.get(syms), "market": M.market_status()})


# trading days kept when a range is cut from stored daily history (sample data / provider fallback)
_DAILY_TAIL = {"1D": 1, "1W": 5, "5D": 5, "1M": 22, "3M": 66, "6M": 126, "1Y": 252, "3Y": 756, "5Y": 1260}
_RANGE_LABEL = {"1D": "today", "1W": "1 week", "5D": "1 week", "1M": "1 month", "3M": "3 months", "6M": "6 months",
                "1Y": "1 year", "3Y": "3 years", "5Y": "5 years", "MAX": "all time"}


_BARS_CACHE: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
_BARS_LOCK = threading.Lock()


def _bars_cached(symbol: str, rng: str) -> pd.DataFrame:
    """Provider bars with a short TTL (60 s intraday, 15 min daily+) so switching ranges feels instant."""
    ttl = 60 if rng in ("1D", "1W", "5D", "1M") else 900
    key = (symbol, rng)
    with _BARS_LOCK:
        hit = _BARS_CACHE.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    df = M.provider().bars(symbol, rng)
    with _BARS_LOCK:
        if len(_BARS_CACHE) > 500:
            _BARS_CACHE.clear()
        _BARS_CACHE[key] = (time.time(), df)
    return df


def _previous_close(symbol: str, session_date: str) -> float | None:
    """Close of the last trading day before the session shown on a 1D chart (exchange convention for 'today's change')."""
    q = M.QUOTES.get([symbol], stale_ok=True).get(symbol) or {}
    if q.get("prev_close") and q.get("time") and str(q["time"])[:10] >= session_date[:10]:
        return float(q["prev_close"])
    try:
        daily = _bars_cached(symbol, "3M")
    except Exception as exc:   # provider failure: no baseline rather than a wrong one
        log.warning("daily bars failed %s: %s", symbol, exc)
        return None
    if daily.empty:
        return None
    before = daily[pd.to_datetime(daily["time"]) < pd.Timestamp(session_date)]
    return float(before["close"].iloc[-1]) if not before.empty else None


def _daily_slice(px: pd.DataFrame, rng: str) -> pd.DataFrame:
    bars = px.rename(columns={"date": "time"})[["time", "open", "high", "low", "close", "volume"]]
    n = _DAILY_TAIL.get(rng)
    return bars.tail(n) if n else bars


@router.get("/chart/{symbol}")
def chart(symbol: str, request: Request, range: str = Query("1Y", pattern="^(1D|1W|5D|1M|3M|6M|1Y|3Y|5Y|MAX)$"),
          indicators: bool = True):
    LIMITER.check(request, "chart", 60, 60)
    intraday = range in ("1D", "1W", "5D", "1M")
    if symbol.startswith("SAMPLE-"):
        bars = _daily_slice(repo.get_prices(symbol, auto_refresh=False), "1W" if range == "1D" else range)
        intraday = False                      # sample data is daily only
        status, source = "sample", "EquityPilot sample dataset (fictional)"
    else:
        try:
            bars = _bars_cached(symbol, range)
        except Exception as exc:
            log.warning("bars failed %s: %s", symbol, exc)
            bars = pd.DataFrame()
        if bars.empty:   # fall back to stored daily history
            px = repo.get_prices(symbol, auto_refresh=False)
            bars = _daily_slice(px, "1W" if range == "1D" else range) if not px.empty else px
            intraday = False
            status, source = "historical", "EquityPilot cache (end-of-day)"
        else:
            status = "delayed" if range in ("1D", "1W", "5D") else "historical"
            source = M.provider().name
    out = {"symbol": symbol, "range": range, "status": status, "source": source, "bars": [], "indicators": {},
           "intraday": intraday, "range_label": _RANGE_LABEL.get(range, range)}
    if bars is None or bars.empty:
        return out
    bars = bars.reset_index(drop=True)
    tt = pd.to_datetime(bars["time"])
    # intraday: ISO UTC timestamp (the browser shifts to IST); daily and longer: the IST calendar date
    bars["time"] = tt.dt.strftime("%Y-%m-%dT%H:%M:%S") if intraday else tt.dt.strftime("%Y-%m-%d")
    out["bars"] = clean(bars.to_dict("records"))
    out["has_volume"] = bool((pd.to_numeric(bars["volume"], errors="coerce").fillna(0) > 0).mean() > 0.5)
    # baseline the period change is measured from: previous close for 1D (as exchanges quote it), else the first close
    first_close = float(bars["close"].iloc[0])
    baseline = {"value": first_close, "label": "Start of period"}
    if range == "1D" and intraday:
        out["session_date"] = str((tt.iloc[-1] + pd.Timedelta(hours=5, minutes=30)).date())
        prev = _previous_close(symbol, out["session_date"])
        if prev:
            baseline = {"value": prev, "label": "Previous close"}
    out["baseline"] = baseline
    last = float(bars["close"].iloc[-1])
    out["change"] = {"abs": last - baseline["value"], "pct": last / baseline["value"] - 1 if baseline["value"] else None}
    if indicators and len(bars) > 30:
        c = bars["close"]
        # Daily ranges shorter than 5 years: compute indicators on 5 years of daily closes and keep the visible dates,
        # so a 200-day average is drawn across the whole 1Y chart instead of starting 200 bars in (as trading terminals do).
        calc = c
        if not intraday and range in ("3M", "6M", "1Y", "3Y") and status != "sample":
            try:
                long = _bars_cached(symbol, "5Y")
                if not long.empty:
                    lc = pd.Series(long["close"].to_numpy(), index=pd.to_datetime(long["time"]).dt.strftime("%Y-%m-%d"))
                    lc = lc[~lc.index.duplicated(keep="last")]
                    if set(bars["time"]).issubset(lc.index):
                        calc = lc
            except Exception as exc:
                log.warning("long history for indicators failed %s: %s", symbol, exc)

        def visible(s: pd.Series) -> list:
            if calc is c:
                return clean(s.tolist())
            return clean(s.reindex(bars["time"]).tolist())

        ind = {"sma20": T.sma(calc, 20), "sma50": T.sma(calc, 50), "sma200": T.sma(calc, 200), "ema20": T.ema(calc, 20),
               "rsi14": T.rsi(calc, 14)}
        m = T.macd(calc)
        bb = T.bollinger(calc)
        ind.update(macd=m["MACD"], macd_signal=m["Signal"], macd_hist=m["Histogram"], bb_upper=bb["Upper"], bb_lower=bb["Lower"])
        out["indicators"] = {k: visible(v) for k, v in ind.items()}
        r = c.pct_change().dropna()
        # annualise by the actual bar spacing (weekly bars on 'All', daily otherwise)
        gap_days = float(tt.diff().dt.days.median()) if len(tt) > 2 else 1.0
        per_year = 52 if gap_days >= 5 else 252
        out["stats"] = clean({"return": float(c.iloc[-1] / c.iloc[0] - 1), "high": float(bars["high"].max()),
                              "low": float(bars["low"].min()), "max_drawdown": T.max_drawdown(c),
                              "volatility": float(r.std() * (per_year ** 0.5)) if not intraday else None})
    return out


@router.websocket("/ws/quotes")
async def ws_quotes(ws: WebSocket):
    """Push quote snapshots for subscribed symbols every 30 s (provider status labelled on each quote).
    Client sends {"subscribe": ["TCS.NS", ...]} at any time."""
    await ws.accept()
    symbols: list[str] = []
    try:
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=30 if symbols else 300)
                if isinstance(msg, dict) and isinstance(msg.get("subscribe"), list):
                    symbols = [str(s)[:30] for s in msg["subscribe"]][:50]
            except asyncio.TimeoutError:
                pass
            if symbols:
                data = await asyncio.to_thread(M.QUOTES.get, symbols, len(symbols) > 5)
                await ws.send_json(clean({"type": "quotes", "quotes": data, "market": M.market_status()}))
    except WebSocketDisconnect:
        return
    except Exception as exc:  # never crash the server on a bad client
        log.info("websocket closed: %s", exc)


@router.get("/market/status")
def status(request: Request):
    current_user(request)
    return clean(M.market_status())
