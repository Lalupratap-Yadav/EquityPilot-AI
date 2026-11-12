"""Market overview, movers, breadth, sector performance, quotes, charts and WebSocket quote stream."""
from __future__ import annotations

import asyncio
import logging

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


@router.get("/chart/{symbol}")
def chart(symbol: str, request: Request, range: str = Query("1Y", pattern="^(1D|5D|1M|6M|1Y|5Y|MAX)$"),
          indicators: bool = True):
    LIMITER.check(request, "chart", 60, 60)
    if symbol.startswith("SAMPLE-"):
        px = repo.get_prices(symbol, auto_refresh=False)
        bars = px.rename(columns={"date": "time"})[["time", "open", "high", "low", "close", "volume"]]
        if range in ("1D", "5D"):
            bars = bars.tail(5)
        status, source = "sample", "EquityPilot sample dataset (fictional)"
    else:
        try:
            bars = M.provider().bars(symbol, range)
        except Exception as exc:
            log.warning("bars failed %s: %s", symbol, exc)
            bars = pd.DataFrame()
        if bars.empty:   # fall back to stored daily history
            px = repo.get_prices(symbol, auto_refresh=False)
            bars = px.rename(columns={"date": "time"})[["time", "open", "high", "low", "close", "volume"]] if not px.empty else px
            status, source = "historical", "EquityPilot cache (end-of-day)"
        else:
            status = "delayed" if range in ("1D", "5D") else "historical"
            source = M.provider().name
    out = {"symbol": symbol, "range": range, "status": status, "source": source, "bars": [], "indicators": {}}
    if bars is None or bars.empty:
        return out
    bars = bars.reset_index(drop=True)
    out["bars"] = clean(bars.to_dict("records"))
    if indicators and len(bars) > 30:
        c = bars["close"]
        ind = {"sma20": T.sma(c, 20), "sma50": T.sma(c, 50), "sma200": T.sma(c, 200), "ema20": T.ema(c, 20),
               "rsi14": T.rsi(c, 14)}
        m = T.macd(c)
        bb = T.bollinger(c)
        ind.update(macd=m["MACD"], macd_signal=m["Signal"], macd_hist=m["Histogram"], bb_upper=bb["Upper"], bb_lower=bb["Lower"])
        out["indicators"] = {k: clean(v.tolist()) for k, v in ind.items()}
        r = c.pct_change().dropna()
        out["stats"] = clean({"return": float(c.iloc[-1] / c.iloc[0] - 1), "high": float(bars["high"].max()),
                              "low": float(bars["low"].min()), "max_drawdown": T.max_drawdown(c),
                              "volatility": float(r.std() * (252 ** 0.5)) if range not in ("1D", "5D", "1M") else None})
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
