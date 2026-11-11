"""Fictional SAMPLE dataset.

These companies DO NOT EXIST. They are generated deterministically so that the application,
its tutorials and its automated tests work without internet access. Every row is stored with
data_type='sample' and every screen showing them displays a SAMPLE badge.
"""
from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd

from .. import db
from ..config import SAMPLE_SOURCE
from .schema import LINE_ITEMS

SAMPLE_COMPANIES = [
    # symbol, name, sector, industry, base revenue (₹ Cr), growth, ebitda margin, d/e target, beta
    ("SAMPLE-ALPHA", "Alpha Consumer Products Ltd (Sample)", "Consumer Defensive", "Packaged Foods & Personal Care", 9000, 0.10, 0.22, 0.05, 0.7),
    ("SAMPLE-BETA", "Beta Infotech Ltd (Sample)", "Technology", "IT Services & Consulting", 15000, 0.12, 0.25, 0.0, 0.9),
    ("SAMPLE-GAMMA", "Gamma Steel & Infra Ltd (Sample)", "Basic Materials", "Steel", 40000, 0.06, 0.15, 1.2, 1.4),
    ("SAMPLE-DELTA", "Delta Pharma Ltd (Sample)", "Healthcare", "Pharmaceuticals", 7000, 0.09, 0.20, 0.3, 0.8),
]
DESCRIPTIONS = {
    "SAMPLE-ALPHA": "FICTIONAL demonstration company. Models a branded consumer goods business with a "
                    "nationwide distribution network, low debt and steady cash generation.",
    "SAMPLE-BETA": "FICTIONAL demonstration company. Models an IT services exporter with a debt-free "
                   "balance sheet and revenue billed mainly to overseas clients.",
    "SAMPLE-GAMMA": "FICTIONAL demonstration company. Models a capital-intensive, cyclical steel producer "
                    "with significant borrowings - useful for studying leverage and risk metrics.",
    "SAMPLE-DELTA": "FICTIONAL demonstration company. Models a generic-pharmaceutical manufacturer with "
                    "domestic formulations and export businesses.",
}
SEGMENTS = {
    "SAMPLE-ALPHA": [("Foods", 0.55), ("Personal care", 0.35), ("Exports", 0.10)],
    "SAMPLE-BETA": [("North America", 0.62), ("Europe", 0.27), ("India & RoW", 0.11)],
    "SAMPLE-GAMMA": [("Flat steel", 0.70), ("Long steel", 0.22), ("Infrastructure services", 0.08)],
    "SAMPLE-DELTA": [("India formulations", 0.45), ("US generics", 0.40), ("API", 0.15)],
}
SHAREHOLDING = {
    "SAMPLE-ALPHA": {"Promoter & Promoter Group": 61.0, "FII/FPI": 14.5, "DII": 12.0, "Public & Others": 12.5},
    "SAMPLE-BETA": {"Promoter & Promoter Group": 52.0, "FII/FPI": 21.0, "DII": 15.0, "Public & Others": 12.0},
    "SAMPLE-GAMMA": {"Promoter & Promoter Group": 44.0, "FII/FPI": 18.0, "DII": 16.0, "Public & Others": 22.0},
    "SAMPLE-DELTA": {"Promoter & Promoter Group": 55.0, "FII/FPI": 17.0, "DII": 13.0, "Public & Others": 15.0},
}
PLEDGE = {"SAMPLE-GAMMA": 12.0}
CR = 1e7
YEARS = [2022, 2023, 2024, 2025, 2026]


def _company_financials(seed: int, base_rev: float, growth: float, margin: float, de: float,
                        shares: float) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    rev = base_rev * CR
    equity = rev * 0.6
    debt = equity * de
    ppe = rev * (0.9 if de > 1 else 0.35)
    for i, fy in enumerate(YEARS):
        if i:
            rev *= 1 + growth + rng.normal(0, 0.03)
        m = margin + rng.normal(0, 0.012)
        ebitda = rev * m
        dep = ppe * 0.07
        ebit = ebitda - dep
        interest = debt * 0.085
        pbt = ebit - interest + rev * 0.01           # other income
        tax = max(pbt, 0) * 0.25
        ni = pbt - tax
        cogs = rev * (0.55 if de > 1 else 0.45)
        capex = dep * (1.6 if de > 1 else 1.3)
        ppe = ppe + capex - dep
        receivables, inventory = rev * 0.12, rev * (0.15 if de > 1 else 0.08)
        nwc_change = (receivables + inventory) * (growth / (1 + growth))
        cfo = ni + dep - nwc_change
        dividends = max(ni, 0) * 0.35
        equity += ni - dividends
        debt = max(debt * (1 + rng.normal(0.02, 0.05)), 0)
        cash = rev * 0.08
        current_assets = receivables + inventory + cash + rev * 0.03
        current_liabilities = rev * 0.14
        total_liabilities = debt + current_liabilities + rev * 0.04
        total_assets = equity + total_liabilities
        vals = {
            "revenue": rev, "cogs": cogs, "gross_profit": rev - cogs, "opex": rev - cogs - ebit,
            "ebitda": ebitda, "depreciation": dep, "ebit": ebit, "interest_expense": interest,
            "pretax_income": pbt, "tax": tax, "net_income": ni, "eps_basic": ni / shares,
            "eps_diluted": ni / shares, "shares_diluted": shares,
            "total_assets": total_assets, "current_assets": current_assets, "cash": cash,
            "receivables": receivables, "inventory": inventory, "net_ppe": ppe,
            "total_liabilities": total_liabilities, "current_liabilities": current_liabilities,
            "total_debt": debt, "total_equity": equity, "shares_outstanding": shares,
            "cfo": cfo, "capex": -capex, "fcf": cfo - capex, "cfi": -capex * 1.05,
            "cff": -dividends - interest, "dividends_paid": -dividends,
        }
        for key, value in vals.items():
            rows.append({
                "statement": LINE_ITEMS[key][0], "period_end": date(fy, 3, 31),
                "period_type": "annual", "basis": "consolidated", "line_item": key,
                "value": float(value),
            })
    return rows


def _price_series(seed: int, last_eps: float, pe: float, beta: float, days: int = 760) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 100)
    end = pd.Timestamp("2026-10-30")
    dates = pd.bdate_range(end=end, periods=days)
    vol = 0.014 * (0.7 + beta * 0.4)
    rets = rng.normal(0.0004, vol, days)
    path = np.exp(np.cumsum(rets))
    close = last_eps * pe * path / path[-1]
    high = close * (1 + np.abs(rng.normal(0, 0.008, days)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, days)))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.004, days))
    volume = rng.integers(200_000, 2_000_000, days).astype(float)
    return pd.DataFrame({"date": dates.date, "open": open_, "high": np.maximum.reduce([high, open_, close]),
                         "low": np.minimum.reduce([low, open_, close]), "close": close, "volume": volume})


def load_sample_data(force: bool = False) -> int:
    """Insert the sample companies (idempotent). Returns number of companies inserted/refreshed."""
    existing = db.read_df(db.select(db.companies.c.symbol).where(db.companies.c.is_sample == True))  # noqa: E712
    if not force and len(existing) == len(SAMPLE_COMPANIES):
        return 0
    now = db.utcnow()
    base = {"source": SAMPLE_SOURCE, "source_url": None, "data_type": "sample", "fetched_at": now}
    pes = {"SAMPLE-ALPHA": 48, "SAMPLE-BETA": 27, "SAMPLE-GAMMA": 9, "SAMPLE-DELTA": 26}
    shares_map = {"SAMPLE-ALPHA": 9.6e8, "SAMPLE-BETA": 4.1e8, "SAMPLE-GAMMA": 1.2e9, "SAMPLE-DELTA": 1.66e8}
    for idx, (sym, name, sector, industry, rev, g, m, de, beta) in enumerate(SAMPLE_COMPANIES):
        db.upsert(db.companies, [{
            "symbol": sym, "name": name, "exchange": "SAMPLE", "isin": None, "sector": sector,
            "industry": industry, "description": DESCRIPTIONS[sym], "website": None, "employees": None,
            "is_sample": True, "in_universe": True, **base}], ["symbol"])
        shares = shares_map[sym]
        fin = _company_financials(idx + 1, rev, g, m, de, shares)
        db.upsert(db.financials, [{"symbol": sym, "currency": "INR", **r, **base} for r in fin],
                  ["symbol", "statement", "period_end", "period_type", "basis", "line_item"])
        last_eps = [r["value"] for r in fin if r["line_item"] == "eps_diluted"][-1]
        px = _price_series(idx + 1, last_eps, pes[sym], beta)
        db.upsert(db.prices, [{"symbol": sym, **r, "source": SAMPLE_SOURCE, "data_type": "sample",
                               "fetched_at": now} for r in px.to_dict("records")], ["symbol", "date"])
        last, prev = float(px["close"].iloc[-1]), float(px["close"].iloc[-2])
        tail = px.tail(250)
        db.upsert(db.quotes, [{
            "symbol": sym, "price": last, "prev_close": prev, "market_cap": last * shares,
            "shares_outstanding": shares, "beta": beta, "week52_high": float(tail["high"].max()),
            "week52_low": float(tail["low"].min()), "dividend_rate": None, "currency": "INR",
            "as_of": datetime(2026, 10, 30, 10, 0), **base}], ["symbol"])
        last_rev = [r["value"] for r in fin if r["line_item"] == "revenue"][-1]
        db.execute(db.delete(db.segments).where(db.segments.c.symbol == sym))
        db.execute(db.insert(db.segments), [{
            "symbol": sym, "period": "FY2026", "segment": s, "revenue": last_rev * w,
            "ebit": None, "basis": "consolidated", **base} for s, w in SEGMENTS[sym]])
        db.execute(db.delete(db.shareholding).where(db.shareholding.c.symbol == sym))
        db.execute(db.insert(db.shareholding), [{
            "symbol": sym, "period": "2026-09-30", "category": c, "pct": p,
            "pledged_pct": PLEDGE.get(sym) if c.startswith("Promoter") else None, **base}
            for c, p in SHAREHOLDING[sym].items()])
        db.execute(db.delete(db.disclosures).where(db.disclosures.c.symbol == sym))
        db.execute(db.insert(db.disclosures), [
            {"symbol": sym, "date": datetime(2026, 10, 20), "title": f"[SAMPLE] {name}: Q2 FY2027 results (fictional)",
             "category": "Results", "publisher": "Sample dataset", "url": None, **base},
            {"symbol": sym, "date": datetime(2026, 8, 5), "title": f"[SAMPLE] {name}: board meeting outcome (fictional)",
             "category": "Board Meeting", "publisher": "Sample dataset", "url": None, **base},
        ])
    peers = [s[0] for s in SAMPLE_COMPANIES]
    db.upsert(db.competitors, [{"symbol": a, "peer_symbol": b, "note": "Sample peer"}
                               for a in peers for b in peers if a != b], ["symbol", "peer_symbol"])
    return len(SAMPLE_COMPANIES)


SAMPLE_PORTFOLIO = [
    # symbol, quantity, buy date (cost = sample closing price on that date)
    ("SAMPLE-ALPHA", 40, date(2025, 11, 3)),
    ("SAMPLE-BETA", 60, date(2025, 6, 2)),
    ("SAMPLE-GAMMA", 400, date(2026, 1, 12)),
    ("SAMPLE-DELTA", 25, date(2025, 3, 3)),
]


def load_sample_portfolio() -> int:
    """Add a sample portfolio using closing prices on the buy dates as cost."""
    load_sample_data()
    rows = []
    for sym, qty, d in SAMPLE_PORTFOLIO:
        px = db.read_df(db.select(db.prices.c.close).where(db.prices.c.symbol == sym)
                        .where(db.prices.c.date <= d).order_by(db.prices.c.date.desc()).limit(1))
        cost = float(px["close"].iloc[0]) if len(px) else 100.0
        rows.append({"symbol": sym, "quantity": qty, "avg_cost": round(cost, 2), "buy_date": d,
                     "notes": "Sample holding (fictional)"})
    db.execute(db.insert(db.holdings), rows)
    return len(rows)
