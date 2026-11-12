"""Profile & auth, preferences, watchlists, price alerts, notifications, recent activity, portfolio, data export."""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from equitypilot import db, users
from equitypilot.analytics import portfolio as PF
from equitypilot.data import marketdata as M
from equitypilot.data import repository as repo

from .core import LIMITER, clean, current_user, not_found

router = APIRouter(prefix="/api", tags=["user"])


# ------------------------------------------------------------------ profile & auth
@router.get("/me")
def me(request: Request):
    uid = current_user(request)
    users.touch(uid)
    return clean({"user": users.get_user(uid), "prefs": users.all_prefs(uid), "unread": _unread(uid)})


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=40)


@router.post("/auth/register")
def register(body: Credentials, request: Request):
    LIMITER.check(request, "auth", 10, 300)
    uid = current_user(request)
    try:
        return clean({"user": users.register(uid, body.username, body.password, body.display_name)})
    except users.AuthError as exc:
        raise HTTPException(400, str(exc))


@router.post("/auth/login")
def login(body: Credentials, request: Request):
    LIMITER.check(request, "auth", 10, 300)
    try:
        uid = users.login(body.username, body.password)
    except users.AuthError as exc:
        raise HTTPException(401, str(exc))
    request.session["uid"] = uid
    return clean({"user": users.get_user(uid)})


@router.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


class Profile(BaseModel):
    display_name: str | None = Field(None, max_length=40)
    show_on_leaderboard: bool | None = None


@router.patch("/me")
def update_me(body: Profile, request: Request):
    uid = current_user(request)
    try:
        return clean({"user": users.update_profile(uid, body.display_name, body.show_on_leaderboard)})
    except users.AuthError as exc:
        raise HTTPException(400, str(exc))


class Pref(BaseModel):
    key: str = Field(pattern=r"^[a-z_]{2,40}$")
    value: object


@router.put("/prefs")
def set_pref(body: Pref, request: Request):
    uid = current_user(request)
    users.set_pref(uid, body.key, body.value)
    return {"ok": True}


@router.get("/me/export")
def export(request: Request):
    return clean(users.export_user_data(current_user(request)))


# ------------------------------------------------------------------ watchlists
def _own_watchlist(uid: int, wid: int) -> None:
    ok = db.read_df(db.select(db.watchlists.c.id).where(db.watchlists.c.id == wid).where(db.watchlists.c.user_id == uid))
    if ok.empty:
        raise not_found("Watchlist")


@router.get("/watchlists")
def watchlists(request: Request):
    uid = current_user(request)
    users.ensure_defaults(uid)
    wls = db.read_df(db.select(db.watchlists).where(db.watchlists.c.user_id == uid).order_by(db.watchlists.c.id))
    items = db.read_df(db.select(db.watchlist_items).where(db.watchlist_items.c.watchlist_id.in_(wls["id"].tolist() or [-1])))
    syms = sorted(set(items["symbol"])) if not items.empty else []
    quotes = M.QUOTES.get(syms) if syms else {}
    names = {s: (repo.get_company(s) or {}).get("name", s) for s in syms}
    out = []
    for _, w in wls.iterrows():
        its = items[items["watchlist_id"] == w["id"]] if not items.empty else items
        rows = []
        for _, it in its.iterrows():
            q = quotes.get(it["symbol"], {})
            rows.append({"symbol": it["symbol"], "name": names.get(it["symbol"]), "note": it["note"], "added_at": it["added_at"],
                         **{k: q.get(k) for k in ("price", "change", "change_pct", "time", "status")}})
        out.append({"id": int(w["id"]), "name": w["name"], "items": rows})
    return clean(out)


class WatchlistBody(BaseModel):
    name: str = Field(min_length=1, max_length=40)


@router.post("/watchlists")
def create_watchlist(body: WatchlistBody, request: Request):
    uid = current_user(request)
    n = db.read_df(db.select(db.watchlists.c.id).where(db.watchlists.c.user_id == uid))
    if len(n) >= 20:
        raise HTTPException(400, "You can have up to 20 watchlists.")
    res = db.execute(db.insert(db.watchlists).values(user_id=uid, name=body.name.strip(), created_at=db.utcnow()))
    return {"id": int(res.inserted_primary_key[0])}


@router.patch("/watchlists/{wid}")
def rename_watchlist(wid: int, body: WatchlistBody, request: Request):
    uid = current_user(request)
    _own_watchlist(uid, wid)
    db.execute(db.update(db.watchlists).where(db.watchlists.c.id == wid).values(name=body.name.strip()))
    return {"ok": True}


@router.delete("/watchlists/{wid}")
def delete_watchlist(wid: int, request: Request):
    uid = current_user(request)
    _own_watchlist(uid, wid)
    db.execute(db.delete(db.watchlist_items).where(db.watchlist_items.c.watchlist_id == wid))
    db.execute(db.delete(db.watchlists).where(db.watchlists.c.id == wid))
    users.ensure_defaults(uid)
    return {"ok": True}


class ItemBody(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    note: str | None = Field(None, max_length=1000)


@router.post("/watchlists/{wid}/items")
def add_item(wid: int, body: ItemBody, request: Request):
    uid = current_user(request)
    _own_watchlist(uid, wid)
    if not repo.get_company(body.symbol):
        raise HTTPException(400, "Open the company page first so EquityPilot can track it.")
    db.upsert(db.watchlist_items, [{"watchlist_id": wid, "symbol": body.symbol, "note": body.note, "added_at": db.utcnow()}],
              ["watchlist_id", "symbol"])
    return {"ok": True}


@router.patch("/watchlists/{wid}/items/{symbol}")
def update_item(wid: int, symbol: str, body: ItemBody, request: Request):
    uid = current_user(request)
    _own_watchlist(uid, wid)
    db.execute(db.update(db.watchlist_items).where(db.watchlist_items.c.watchlist_id == wid)
               .where(db.watchlist_items.c.symbol == symbol).values(note=body.note))
    return {"ok": True}


@router.delete("/watchlists/{wid}/items/{symbol}")
def remove_item(wid: int, symbol: str, request: Request):
    uid = current_user(request)
    _own_watchlist(uid, wid)
    db.execute(db.delete(db.watchlist_items).where(db.watchlist_items.c.watchlist_id == wid).where(db.watchlist_items.c.symbol == symbol))
    return {"ok": True}


# ------------------------------------------------------------------ alerts & notifications
class AlertBody(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    direction: str = Field(pattern="^(above|below)$")
    price: float = Field(gt=0)
    note: str | None = Field(None, max_length=200)


@router.get("/alerts")
def alerts(request: Request):
    uid = current_user(request)
    check_alerts(uid)
    return clean(db.read_df(db.select(db.alerts).where(db.alerts.c.user_id == uid).order_by(db.alerts.c.id.desc())).to_dict("records"))


@router.post("/alerts")
def create_alert(body: AlertBody, request: Request):
    uid = current_user(request)
    if not repo.get_company(body.symbol):
        raise HTTPException(400, "Unknown company.")
    n = db.read_df(db.select(db.alerts.c.id).where(db.alerts.c.user_id == uid).where(db.alerts.c.active == True))  # noqa: E712
    if len(n) >= 50:
        raise HTTPException(400, "You can have up to 50 active alerts.")
    res = db.execute(db.insert(db.alerts).values(user_id=uid, symbol=body.symbol, direction=body.direction, price=body.price,
                                                 note=body.note, active=True, created_at=db.utcnow()))
    return {"id": int(res.inserted_primary_key[0])}


@router.delete("/alerts/{aid}")
def delete_alert(aid: int, request: Request):
    uid = current_user(request)
    db.execute(db.delete(db.alerts).where(db.alerts.c.id == aid).where(db.alerts.c.user_id == uid))
    return {"ok": True}


def check_alerts(uid: int) -> int:
    """Trigger alerts whose condition is met by the latest (delayed) quote; creates in-app notifications."""
    act = db.read_df(db.select(db.alerts).where(db.alerts.c.user_id == uid).where(db.alerts.c.active == True))  # noqa: E712
    if act.empty:
        return 0
    quotes = M.QUOTES.get(act["symbol"].unique().tolist())
    fired = 0
    for _, a in act.iterrows():
        q = quotes.get(a["symbol"], {})
        p = q.get("price")
        if p is None:
            continue
        if (a["direction"] == "above" and p >= a["price"]) or (a["direction"] == "below" and p <= a["price"]):
            db.execute(db.update(db.alerts).where(db.alerts.c.id == int(a["id"])).values(active=False, triggered_at=db.utcnow(),
                                                                                        triggered_price=p))
            db.execute(db.insert(db.notifications).values(
                user_id=uid, ts=db.utcnow(), kind="alert", read=False, link=f"/company/{a['symbol']}",
                title=f"{a['symbol']} is {a['direction']} ₹{a['price']:,.2f}",
                body=f"Latest price ₹{p:,.2f} ({q.get('status')} quote from {q.get('source')})."))
            fired += 1
    return fired


def _unread(uid: int) -> int:
    return int(db.read_df(db.select(db.notifications.c.id).where(db.notifications.c.user_id == uid)
                          .where(db.notifications.c.read == False)).shape[0])  # noqa: E712


@router.get("/notifications")
def notifications(request: Request):
    uid = current_user(request)
    check_alerts(uid)
    rows = db.read_df(db.select(db.notifications).where(db.notifications.c.user_id == uid).order_by(db.notifications.c.id.desc()).limit(50))
    return clean({"items": rows.to_dict("records"), "unread": _unread(uid)})


@router.post("/notifications/read")
def mark_read(request: Request):
    uid = current_user(request)
    db.execute(db.update(db.notifications).where(db.notifications.c.user_id == uid).values(read=True))
    return {"ok": True}


# ------------------------------------------------------------------ recent activity
@router.get("/recent")
def recent(request: Request):
    uid = current_user(request)
    v = db.read_df(db.select(db.recent_views).where(db.recent_views.c.user_id == uid).order_by(db.recent_views.c.ts.desc()).limit(12))
    s = db.read_df(db.select(db.recent_searches).where(db.recent_searches.c.user_id == uid).order_by(db.recent_searches.c.ts.desc()).limit(8))
    syms = v["symbol"].tolist() if not v.empty else []
    q = M.QUOTES.get(syms) if syms else {}
    views = [{"symbol": s_, "name": (repo.get_company(s_) or {}).get("name", s_), **{k: q.get(s_, {}).get(k) for k in ("price", "change_pct", "status")}}
             for s_ in syms]
    return clean({"views": views, "searches": s["query"].tolist() if not s.empty else []})


# ------------------------------------------------------------------ manual portfolio
def _holdings(uid: int) -> pd.DataFrame:
    return db.read_df(db.select(db.holdings).where(db.holdings.c.user_id == uid).order_by(db.holdings.c.id))


@router.get("/portfolio")
def portfolio(request: Request, rf: float = 0.065):
    uid = current_user(request)
    h = _holdings(uid)
    if h.empty:
        return {"empty": True, "lots": []}
    syms = h["symbol"].unique().tolist()
    M.QUOTES.get(syms)                       # refresh cached prices into the DB first
    v = PF.value_holdings(h)
    invested, value = float(v["invested"].sum()), float(v["value"].sum(skipna=True))
    agg = v.groupby(["symbol", "name", "sector"], as_index=False).agg(quantity=("quantity", "sum"), invested=("invested", "sum"),
                                                                      value=("value", "sum"), price=("price", "first"))
    agg["weight"] = agg["value"] / agg["value"].sum() if agg["value"].sum() else None
    bench = repo.get_prices("^NSEI", auto_refresh=False)
    rm = PF.risk_metrics(v, rf, bench.set_index("date")["close"] if not bench.empty else None)
    series = rm.pop("series", None) if rm else None
    risk_contrib = rm.pop("risk_contribution", None) if rm else None
    corr = rm.pop("correlation", None) if rm else None
    return clean({
        "lots": h.to_dict("records"), "holdings": agg.to_dict("records"), "invested": invested, "value": value,
        "pnl": value - invested, "return": value / invested - 1 if invested else None, "xirr": PF.portfolio_xirr(v),
        "concentration": PF.concentration(agg.set_index("symbol")["weight"]) if agg["value"].sum() else {},
        "sectors": agg.groupby("sector")["value"].sum().sort_values(ascending=False).to_dict(),
        "risk": rm or {}, "risk_contribution": risk_contrib.to_dict() if risk_contrib is not None else {},
        "correlation": {"symbols": list(corr.columns), "values": corr.values.tolist()} if corr is not None else None,
        "growth": [{"date": str(d.date()), "value": float(x)} for d, x in series.items()] if series is not None else [],
    })


class Lot(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    quantity: float = Field(gt=0)
    avg_cost: float = Field(gt=0)
    buy_date: date | None = None
    notes: str | None = Field(None, max_length=200)


@router.post("/portfolio/lots")
def add_lot(body: Lot, request: Request):
    uid = current_user(request)
    if not repo.get_company(body.symbol):
        raise HTTPException(400, "Unknown company - open its page first.")
    if body.buy_date and body.buy_date > date.today():
        raise HTTPException(400, "Buy date cannot be in the future.")
    res = db.execute(db.insert(db.holdings).values(user_id=uid, **body.model_dump()))
    return {"id": int(res.inserted_primary_key[0])}


@router.delete("/portfolio/lots/{lid}")
def delete_lot(lid: int, request: Request):
    uid = current_user(request)
    db.execute(db.delete(db.holdings).where(db.holdings.c.id == lid).where(db.holdings.c.user_id == uid))
    return {"ok": True}
