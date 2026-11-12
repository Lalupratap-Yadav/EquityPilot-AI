"""EquityPilot Virtual Invest (paper trading) API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from equitypilot import db
from equitypilot.analytics import paper as P
from equitypilot.analytics import portfolio as PF
from equitypilot.data import repository as repo

from .core import LIMITER, clean, current_user

router = APIRouter(prefix="/api/invest", tags=["virtual invest"])


@router.get("/summary")
def summary(request: Request):
    uid = current_user(request)
    s = P.summary(uid)
    sectors: dict[str, float] = {}
    for h in s["holdings"]:
        sectors[h["sector"]] = sectors.get(h["sector"], 0) + (h["value"] or 0)
    weights = {h["symbol"]: h["weight"] for h in s["holdings"] if h["weight"]}
    import pandas as pd
    risk = {}
    if len(s["holdings"]) >= 1:
        v = pd.DataFrame([{"symbol": h["symbol"], "value": h["value"] or 0} for h in s["holdings"]])
        bench = repo.get_prices("^NSEI", auto_refresh=False)
        rm = PF.risk_metrics(v, 0.065, bench.set_index("date")["close"] if not bench.empty else None)
        if rm:
            risk = {k: rm.get(k) for k in ("volatility", "max_drawdown", "beta", "diversification_ratio", "observations")}
    return clean({**s, "sectors": sectors, "concentration": PF.concentration(pd.Series(weights)) if weights else {},
                  "risk": risk, "achievements": P.achievements(uid, s), "tips": P.tips(s),
                  "disclaimer": "Virtual money only - no real orders are placed. Prices are delayed (or fictional for SAMPLE "
                                "companies). Brokerage, taxes and charges are not simulated."})


class Order(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    side: str = Field(pattern="^(BUY|SELL|buy|sell)$")
    qty: int = Field(gt=0, le=1_000_000)


@router.post("/orders")
def order(body: Order, request: Request):
    LIMITER.check(request, "orders", 30, 60)
    uid = current_user(request)
    try:
        res = P.place_order(uid, body.symbol, body.side, body.qty)
    except P.TradeError as exc:
        raise HTTPException(400, str(exc))
    db.log_activity("Virtual trade", f"user {uid}: {body.side.upper()} {body.qty} {body.symbol}")
    return clean(res)


@router.get("/trades")
def trades(request: Request):
    uid = current_user(request)
    df = P.trades(uid)
    names = {s: (repo.get_company(s) or {}).get("name", s) for s in df["symbol"].unique()} if not df.empty else {}
    if not df.empty:
        df["name"] = df["symbol"].map(names)
    return clean(df.sort_values("ts", ascending=False).to_dict("records") if not df.empty else [])


@router.get("/performance")
def performance(request: Request):
    uid = current_user(request)
    perf = P.performance(uid)
    return clean({"series": perf.to_dict("records") if not perf.empty else [],
                  "note": "Daily value at closing prices (delayed/historical), rebased to 100 at the start; NIFTY 50 price index for comparison."})


@router.get("/leaderboard")
def leaderboard(request: Request):
    current_user(request)
    return clean({"rows": P.leaderboard(), "note": "Only users who opted in (Settings → Show me on the leaderboard) appear."})


@router.post("/reset")
def reset(request: Request):
    uid = current_user(request)
    P.reset(uid)
    return clean(P.summary(uid, with_quotes=False))
