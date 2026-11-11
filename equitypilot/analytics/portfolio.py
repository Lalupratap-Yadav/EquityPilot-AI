"""Portfolio analytics: valuation, returns (absolute & XIRR), allocation, concentration and risk."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from ..data import repository as repo
from . import technicals as T


def value_holdings(h: pd.DataFrame) -> pd.DataFrame:
    """Add price, value, P&L, weight, sector and data label to each holding (one row per lot)."""
    if h.empty:
        return h
    rows = []
    for _, r in h.iterrows():
        q = repo.get_quote(r["symbol"]) or {}
        c = repo.get_company(r["symbol"]) or {}
        price = q.get("price")
        invested = r["quantity"] * r["avg_cost"]
        value = r["quantity"] * price if price else np.nan
        rows.append({**r.to_dict(), "name": c.get("name", r["symbol"]), "sector": c.get("sector") or "Unclassified",
                     "price": price, "invested": invested, "value": value, "pnl": value - invested,
                     "return": value / invested - 1 if invested and price else np.nan,
                     "price_time": q.get("as_of") or q.get("fetched_at"),
                     "data_type": "sample" if c.get("is_sample") else ("delayed" if q else "missing")})
    df = pd.DataFrame(rows)
    total = df["value"].sum(skipna=True)
    df["weight"] = df["value"] / total if total else np.nan
    return df


def xirr(cashflows: list[tuple[date, float]], lo: float = -0.99, hi: float = 10.0) -> float | None:
    """Annualised internal rate of return for dated cash flows (negative = investment). Bisection on NPV."""
    if len(cashflows) < 2 or all(cf >= 0 for _, cf in cashflows) or all(cf <= 0 for _, cf in cashflows):
        return None
    t0 = min(d for d, _ in cashflows)

    def npv(rate):
        return sum(cf / (1 + rate) ** ((d - t0).days / 365.0) for d, cf in cashflows)

    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-6:
            break
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def portfolio_xirr(v: pd.DataFrame, today: date | None = None) -> float | None:
    today = today or date.today()
    v = v.dropna(subset=["value"])
    if v.empty or v["buy_date"].isna().any():
        return None
    flows = [(pd.Timestamp(r["buy_date"]).date(), -r["invested"]) for _, r in v.iterrows()]
    flows.append((today, float(v["value"].sum())))
    return xirr(flows)


def concentration(weights: pd.Series) -> dict:
    w = weights.dropna()
    w = w[w > 0]
    if w.empty:
        return {"hhi": None, "effective_n": None, "top_weight": None}
    hhi = float((w ** 2).sum())
    return {"hhi": hhi, "effective_n": 1 / hhi, "top_weight": float(w.max())}


def price_matrix(symbols: list[str], days: int = 365) -> pd.DataFrame:
    frames = {}
    for s in symbols:
        p = repo.get_prices(s, auto_refresh=False)
        if not p.empty:
            p = p[p["date"] >= p["date"].max() - pd.Timedelta(days=days)]
            frames[s] = p.set_index("date")["close"]
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).sort_index().ffill().dropna(how="any")


def risk_metrics(v: pd.DataFrame, rf: float = 0.065, benchmark: pd.Series | None = None) -> dict:
    """Risk of the CURRENT weights applied to the last year's daily returns (a standard ex-post approximation)."""
    w = v.groupby("symbol")["value"].sum()
    w = w / w.sum()
    px = price_matrix(list(w.index))
    if px.empty or len(px) < 40:
        return {}
    rets = px.pct_change().dropna()
    w = w.reindex(rets.columns).fillna(0)
    port = rets @ w
    vol = float(port.std() * np.sqrt(T.TRADING_DAYS))
    ann_ret = float((1 + port).prod() ** (T.TRADING_DAYS / len(port)) - 1)
    cov = rets.cov() * T.TRADING_DAYS
    port_var = float(w @ cov @ w)
    contrib = (w * (cov @ w)) / port_var if port_var else w * np.nan
    asset_vol = np.sqrt(np.diag(cov))
    out = {
        "volatility": vol, "annual_return": ann_ret,
        "sharpe": (ann_ret - rf) / vol if vol else None,
        "max_drawdown": T.max_drawdown((1 + port).cumprod()),
        "diversification_ratio": float((w.values * asset_vol).sum() / np.sqrt(port_var)) if port_var else None,
        "risk_contribution": contrib, "correlation": rets.corr(), "observations": len(rets),
        "start": rets.index.min(), "end": rets.index.max(), "series": (1 + port).cumprod() * 100,
    }
    if benchmark is not None and not benchmark.empty:
        b, corr, n = T.beta((1 + port).cumprod(), benchmark)
        out.update(beta=b, benchmark_corr=corr)
    return out
