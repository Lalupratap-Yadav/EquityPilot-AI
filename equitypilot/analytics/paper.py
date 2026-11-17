"""EquityPilot Virtual Invest - paper-trading engine.

* Every user starts with ₹10,00,000 of VIRTUAL money. No real orders are ever placed.
* Orders fill at the latest available quote (DELAYED from Yahoo, or SAMPLE for fictional
  companies) and the quote's status and timestamp are stored with the trade.
* Buys cannot exceed available virtual cash; sells cannot exceed the quantity held.
* Corporate actions (dividends, splits from the provider) are applied to positions held
  before the ex-date, so P&L stays correct. The provider restates history for every later split (bonus issues
  appear as splits): its past closes and dividend amounts are divided by the split factor. Both are converted back
  to the amounts that applied on the day, so a split is never counted twice and dividends are not under-credited.
* No brokerage, STT, stamp duty, GST or DP charges are simulated (stated in the UI).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .. import db
from ..data import marketdata as M
from ..data import repository as repo

INITIAL_CASH = 10_00_000.0


class TradeError(ValueError):
    pass


def account(uid: int) -> dict:
    df = db.read_df(db.select(db.paper_accounts).where(db.paper_accounts.c.user_id == uid))
    if df.empty:   # idempotent: parallel first requests must not collide on the primary key
        db.upsert(db.paper_accounts, [{"user_id": uid, "cash": INITIAL_CASH, "initial": INITIAL_CASH,
                                       "started_at": db.utcnow(), "resets": 0}], ["user_id"], update=False)
        df = db.read_df(db.select(db.paper_accounts).where(db.paper_accounts.c.user_id == uid))
    return df.iloc[0].to_dict()


def trades(uid: int) -> pd.DataFrame:
    return db.read_df(db.select(db.paper_trades).where(db.paper_trades.c.user_id == uid)
                      .order_by(db.paper_trades.c.ts, db.paper_trades.c.id))


def _replay(rows: pd.DataFrame) -> dict[str, dict]:
    """Positions from the trade log: qty, cost basis, realised P&L, dividends, first buy date."""
    pos: dict[str, dict] = defaultdict(lambda: {"qty": 0.0, "cost": 0.0, "realised": 0.0, "dividends": 0.0, "first_buy": None})
    for _, r in rows.iterrows():
        p = pos[r["symbol"]]
        if r["kind"] == "BUY":
            p["qty"] += r["qty"]
            p["cost"] += r["qty"] * r["price"]
            p["first_buy"] = p["first_buy"] or r["ts"]
        elif r["kind"] == "SELL":
            avg = p["cost"] / p["qty"] if p["qty"] else 0
            p["realised"] += (r["price"] - avg) * r["qty"]
            p["cost"] -= avg * r["qty"]
            p["qty"] -= r["qty"]
            if p["qty"] < 1e-9:
                p["qty"], p["cost"], p["first_buy"] = 0.0, 0.0, None
        elif r["kind"] == "SPLIT":
            p["qty"] += r["qty"]          # extra shares; cost basis unchanged so average price falls
        elif r["kind"] == "DIVIDEND":
            p["dividends"] += r["amount"]
    return dict(pos)


def _qty_before(rows: pd.DataFrame, symbol: str, when: datetime) -> float:
    sub = rows[(rows["symbol"] == symbol) & (pd.to_datetime(rows["ts"]) < when)]
    q = 0.0
    for _, r in sub.iterrows():
        q += r["qty"] if r["kind"] in ("BUY", "SPLIT") else -r["qty"] if r["kind"] == "SELL" else 0
    return q


def split_factor_after(splits: pd.DataFrame, when) -> float:
    """Product of split factors with an ex-date after `when` (1.0 when none). Multiplying a provider value for date
    `when` by this factor gives the amount as it was on that date (before later splits were applied to history)."""
    if splits is None or splits.empty:
        return 1.0
    d = pd.Timestamp(when).date()
    f = 1.0
    for _, s in splits.iterrows():
        if pd.Timestamp(s["date"]).date() > d and s["value"] and float(s["value"]) > 0:
            f *= float(s["value"])
    return f


def apply_corporate_actions(uid: int) -> int:
    """Credit dividends and apply splits for positions held before each ex-date. Idempotent."""
    rows = trades(uid)
    if rows.empty:
        return 0
    applied = 0
    acct = account(uid)
    cash = float(acct["cash"])
    for sym in rows.loc[rows["kind"] == "BUY", "symbol"].unique():
        first = pd.to_datetime(rows.loc[(rows["symbol"] == sym) & (rows["kind"] == "BUY"), "ts"]).min()
        last_ref = db.get_setting(f"actions_refreshed:{sym}")
        if not last_ref or db.utcnow() - datetime.fromisoformat(last_ref) > timedelta(days=1):
            M.refresh_actions(sym)
        acts = M.get_actions(sym, since=first.date())
        splits = acts[acts["type"] == "split"] if not acts.empty else acts
        for _, a in acts.iterrows():
            ex = datetime.combine(pd.Timestamp(a["date"]).date(), datetime.min.time()) - timedelta(hours=5, minutes=30)  # ex-date 00:00 IST in UTC
            tag = f"{a['type']} ex-date {pd.Timestamp(a['date']).date()}"
            done = rows[(rows["symbol"] == sym) & (rows["note"] == tag)]
            if not done.empty or ex <= first:
                continue
            held = _qty_before(rows, sym, ex)
            if held <= 0:
                continue
            if a["type"] == "dividend":
                per_share = float(a["value"]) * split_factor_after(splits, pd.Timestamp(a["date"]).date())
                amt = held * per_share
                cash += amt
                rec = {"kind": "DIVIDEND", "qty": held, "price": per_share, "amount": amt}
            else:
                extra = held * (float(a["value"]) - 1)
                rec = {"kind": "SPLIT", "qty": extra, "price": None, "amount": 0.0}
            db.execute(db.insert(db.paper_trades).values(user_id=uid, ts=ex, symbol=sym, cash_after=cash, price_time=ex,
                                                         price_type="corporate action", note=tag, **rec))
            rows = trades(uid)
            applied += 1
    if applied:
        db.execute(db.update(db.paper_accounts).where(db.paper_accounts.c.user_id == uid).values(cash=cash))
    return applied


def place_order(uid: int, symbol: str, side: str, qty: float) -> dict:
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise TradeError("Side must be BUY or SELL.")
    if qty is None or qty <= 0 or float(qty) != int(qty):
        raise TradeError("Quantity must be a whole number of shares greater than zero.")
    qty = float(int(qty))
    if not repo.get_company(symbol):
        raise TradeError("Add the company to EquityPilot before trading it (open its company page).")
    q = M.QUOTES.get([symbol])[symbol]
    price = q.get("price")
    if not price or q.get("status") == "unavailable":
        raise TradeError("No price is available for this stock right now, so the virtual order cannot be filled.")
    apply_corporate_actions(uid)
    acct = account(uid)
    cash = float(acct["cash"])
    value = qty * price
    if side == "BUY" and value > cash + 1e-6:
        raise TradeError(f"Insufficient virtual funds: order value ₹{value:,.2f} exceeds available cash ₹{cash:,.2f}.")
    if side == "SELL":
        held = _replay(trades(uid)).get(symbol, {}).get("qty", 0.0)
        if qty > held + 1e-9:
            raise TradeError(f"You hold {held:,.0f} shares of {symbol}; you cannot sell {qty:,.0f}.")
    cash = cash - value if side == "BUY" else cash + value
    ts = db.utcnow()
    price_time = datetime.fromisoformat(q["time"]) if q.get("time") else ts
    db.execute(db.insert(db.paper_trades).values(user_id=uid, ts=ts, kind=side, symbol=symbol, qty=qty, price=price,
                                                 amount=-value if side == "BUY" else value, cash_after=cash,
                                                 price_time=price_time, price_type=q.get("status"),
                                                 note=f"Filled at {q.get('status')} price from {q.get('source')}"))
    db.execute(db.update(db.paper_accounts).where(db.paper_accounts.c.user_id == uid).values(cash=cash))
    return {"symbol": symbol, "side": side, "qty": qty, "price": price, "value": value, "cash_after": cash,
            "price_status": q.get("status"), "price_time": q.get("time"), "source": q.get("source")}


def reset(uid: int) -> None:
    db.execute(db.delete(db.paper_trades).where(db.paper_trades.c.user_id == uid))
    acct = account(uid)
    db.execute(db.update(db.paper_accounts).where(db.paper_accounts.c.user_id == uid).values(
        cash=INITIAL_CASH, initial=INITIAL_CASH, started_at=db.utcnow(), resets=int(acct["resets"] or 0) + 1))


def summary(uid: int, with_quotes: bool = True) -> dict:
    apply_corporate_actions(uid)
    acct = account(uid)
    rows = trades(uid)
    pos = _replay(rows)
    held = {s: p for s, p in pos.items() if p["qty"] > 0}
    quotes = M.QUOTES.get(list(held)) if (held and with_quotes) else {}
    holdings, invested, value = [], 0.0, 0.0
    for s, p in held.items():
        c = repo.get_company(s) or {}
        qt = quotes.get(s, {})
        price = qt.get("price")
        mv = p["qty"] * price if price else None
        invested += p["cost"]
        value += mv or 0
        holdings.append({"symbol": s, "name": c.get("name", s), "sector": c.get("sector") or "Unclassified",
                         "qty": p["qty"], "avg_price": p["cost"] / p["qty"], "invested": p["cost"], "price": price,
                         "value": mv, "pnl": (mv - p["cost"]) if mv is not None else None,
                         "pnl_pct": (mv / p["cost"] - 1) if mv and p["cost"] else None,
                         "day_change_pct": qt.get("change_pct"), "price_status": qt.get("status"),
                         "price_time": qt.get("time"), "first_buy": str(p["first_buy"]) if p["first_buy"] else None,
                         "dividends": p["dividends"]})
    for h in holdings:
        h["weight"] = (h["value"] or 0) / value if value else None
    realised = sum(p["realised"] for p in pos.values())
    dividends = sum(p["dividends"] for p in pos.values())
    cash = float(acct["cash"])
    total = cash + value
    return {"cash": cash, "initial": float(acct["initial"]), "invested": invested, "holdings_value": value,
            "total_value": total, "total_return": total / float(acct["initial"]) - 1, "unrealised": value - invested,
            "realised": realised, "dividends": dividends, "started_at": str(acct["started_at"]), "resets": int(acct["resets"] or 0),
            "holdings": sorted(holdings, key=lambda h: -(h["value"] or 0)), "trade_count": int((rows["kind"].isin(["BUY", "SELL"])).sum()) if not rows.empty else 0}


def performance(uid: int) -> pd.DataFrame:
    """Daily portfolio value vs NIFTY 50 (both rebased to 100) from the account start."""
    acct = account(uid)
    rows = trades(uid)
    start = pd.Timestamp(acct["started_at"]).normalize()
    days = pd.bdate_range(start, pd.Timestamp.now('UTC').tz_localize(None).normalize())
    if len(days) < 2:
        return pd.DataFrame()
    symbols = rows["symbol"].unique().tolist() if not rows.empty else []
    closes, splits_by = {}, {}
    for s in symbols:
        p = repo.get_prices(s, auto_refresh=False)
        if not p.empty:
            closes[s] = p.set_index("date")["close"].sort_index().astype(float)
            acts = M.get_actions(s)
            splits_by[s] = acts[acts["type"] == "split"] if not acts.empty else acts
    bench = repo.get_prices("^NSEI", auto_refresh=False)
    nav = []
    for d in days:
        eod = d + pd.Timedelta(hours=10)    # 15:30 IST close in UTC
        upto = rows[pd.to_datetime(rows["ts"]) <= eod] if not rows.empty else rows
        cash = float(upto["cash_after"].iloc[-1]) if len(upto) else float(acct["initial"])
        pos = _replay(upto) if len(upto) else {}
        mv = 0.0
        for s, p in pos.items():
            if p["qty"] > 0 and s in closes:
                c = closes[s][closes[s].index <= d]
                if len(c):
                    # the provider's closes are in today's share units (adjusted for every split since); convert the latest
                    # close on or before day d into day-d share units so it matches the quantity held that day - also when
                    # the price history has not caught up with a split yet
                    mv += p["qty"] * float(c.iloc[-1]) * split_factor_after(splits_by.get(s), pd.Timestamp(d).date())
        nav.append(cash + mv)
    out = pd.DataFrame({"date": days, "portfolio": np.array(nav) / float(acct["initial"]) * 100})
    if not bench.empty:
        b = bench.set_index("date")["close"].sort_index()
        bvals = [float(b[b.index <= d].iloc[-1]) if len(b[b.index <= d]) else np.nan for d in days]
        base = next((v for v in bvals if not np.isnan(v)), None)
        out["nifty50"] = [v / base * 100 if base and not np.isnan(v) else None for v in bvals]
    return out


ACHIEVEMENTS = [
    ("first_trade", "First step", "Placed your first virtual trade."),
    ("five_stocks", "Diversifier", "Held 5 or more different companies at once."),
    ("four_sectors", "Sector spread", "Held companies from 4 or more sectors."),
    ("no_overweight", "Disciplined sizing", "5+ holdings and no single stock above 25% of invested value."),
    ("thirty_days", "Patient investor", "Held a position for 30 days or more."),
    ("dividend", "Income earner", "Received a (virtual) dividend."),
    ("researcher", "Researcher", "Viewed 10 or more company research pages."),
]


def achievements(uid: int, s: dict | None = None) -> list[dict]:
    s = s or summary(uid, with_quotes=False)
    h = s["holdings"]
    invested = sum(x["invested"] for x in h) or 0
    views = db.read_df(db.select(db.recent_views.c.symbol).where(db.recent_views.c.user_id == uid))
    oldest = min((pd.Timestamp(x["first_buy"]) for x in h if x["first_buy"]), default=None)
    got = {
        "first_trade": s["trade_count"] > 0,
        "five_stocks": len(h) >= 5,
        "four_sectors": len({x["sector"] for x in h}) >= 4,
        "no_overweight": len(h) >= 5 and invested > 0 and max(x["invested"] for x in h) / invested <= 0.25,
        "thirty_days": oldest is not None and (pd.Timestamp.now('UTC').tz_localize(None) - oldest).days >= 30,
        "dividend": s["dividends"] > 0,
        "researcher": len(views) >= 10,
    }
    return [{"id": k, "title": t, "description": d, "earned": bool(got.get(k))} for k, t, d in ACHIEVEMENTS]


def tips(s: dict) -> list[str]:
    """Educational observations about the virtual portfolio (not investment advice)."""
    out = []
    h = s["holdings"]
    if not h:
        return ["Start by researching a company: read its financials, valuation and risk pages before placing a virtual trade.",
                "Try building a portfolio across several sectors to see how diversification changes overall risk."]
    if s["cash"] / s["total_value"] > 0.8:
        out.append("Most of your virtual money is still in cash. Cash has no market risk but also earns nothing in this simulator.")
    top = max(h, key=lambda x: x["weight"] or 0)
    if (top["weight"] or 0) > 0.30:
        out.append(f"{top['name']} is {top['weight']:.0%} of your holdings. A large single position means one company's results "
                   "can move your whole portfolio - compare this with the diversification ideas in the Learning Centre.")
    sectors = {x["sector"] for x in h}
    if len(h) >= 3 and len(sectors) == 1:
        out.append("All your holdings are in one sector, so they are likely to move together. Sector concentration is a key "
                   "idea in portfolio risk.")
    losers = [x for x in h if (x["pnl_pct"] or 0) < -0.15]
    if losers:
        out.append("Some positions are down more than 15%. Check what has changed in the company's results or filings, "
                   "not only in the price.")
    out.append("Virtual results exclude brokerage, taxes and other charges, which reduce real-world returns.")
    return out


def leaderboard(limit: int = 20) -> list[dict]:
    users = db.read_df(db.select(db.users.c.id, db.users.c.display_name).where(db.users.c.show_on_leaderboard == True))  # noqa: E712
    out = []
    for _, u in users.iterrows():
        accts = db.read_df(db.select(db.paper_accounts).where(db.paper_accounts.c.user_id == int(u["id"])))
        if accts.empty:
            continue
        s = summary(int(u["id"]))
        # only the display name the user chose and the overall return - never holdings, trades or position counts
        out.append({"display_name": u["display_name"], "total_return": s["total_return"], "since": s["started_at"]})
    return sorted(out, key=lambda x: -x["total_return"])[:limit]
