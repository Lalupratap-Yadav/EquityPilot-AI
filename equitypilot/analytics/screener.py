"""Per-company metric snapshot used by the screener, comparison, watchlist and peer tables."""
from __future__ import annotations

import pandas as pd

from ..data import repository as repo
from . import ratios as R
from . import valuation as V

METRIC_COLUMNS = {
    # key: (label, kind)  kind: pct | x | inr | cr | num
    "price": ("Price (₹)", "inr"),
    "day_change": ("Day change", "pct"),
    "market_cap": ("Market cap", "cr"),
    "pe": ("P/E", "x"),
    "pb": ("P/B", "x"),
    "ev_ebitda": ("EV/EBITDA", "x"),
    "dividend_yield": ("Dividend yield", "pct"),
    "revenue": ("Revenue (latest FY)", "cr"),
    "net_income": ("Net profit (latest FY)", "cr"),
    "revenue_growth": ("Revenue growth (YoY)", "pct"),
    "net_income_growth": ("Profit growth (YoY)", "pct"),
    "revenue_cagr_3y": ("Revenue CAGR (3Y)", "pct"),
    "profit_cagr_3y": ("Profit CAGR (3Y)", "pct"),
    "ebitda_margin": ("EBITDA margin", "pct"),
    "net_margin": ("Net margin", "pct"),
    "roe": ("ROE", "pct"),
    "roce": ("ROCE", "pct"),
    "debt_to_equity": ("Debt/Equity", "x"),
    "interest_coverage": ("Interest coverage", "x"),
    "current_ratio": ("Current ratio", "x"),
    "cfo_to_net_income": ("CFO/Net profit", "x"),
    "fcf_margin": ("FCF margin", "pct"),
    "piotroski": ("Piotroski F-score", "num"),
}


_NO_ROW = object()
# Statement-based metrics per company, reused until its statements change (prices feed only the valuation fields).
_FUNDAMENTALS: dict[tuple, dict] = {}


def _fundamentals(fd, is_fin: bool) -> dict:
    key = (fd.signature, is_fin)
    if fd.signature is not None and key in _FUNDAMENTALS:
        return dict(_FUNDAMENTALS[key])
    rt = R.compute_ratios(fd)
    latest = rt.iloc[:, -1]
    row = {k: latest.get(k) for k in ("revenue_growth", "net_income_growth", "ebitda_margin", "net_margin", "roe", "roce",
                                      "debt_to_equity", "interest_coverage", "current_ratio", "cfo_to_net_income", "fcf_margin")}
    row["revenue"] = fd.latest("revenue")
    row["net_income"] = fd.latest("net_income")
    row["revenue_cagr_3y"] = R.cagr(fd.get("revenue"), 3)
    row["profit_cagr_3y"] = R.cagr(fd.get("net_income"), 3)
    row["piotroski"] = None if is_fin else R.piotroski_f_score(fd)[0]
    if fd.signature is not None:
        if len(_FUNDAMENTALS) > 3000:
            _FUNDAMENTALS.clear()
        _FUNDAMENTALS[key] = dict(row)
    return row


def company_metrics(symbol: str, auto_refresh: bool = False, company: dict | None | object = _NO_ROW,
                    quote: dict | None | object = _NO_ROW) -> dict:
    """Metric row for one company. `company` / `quote` may be passed in when the caller already loaded them in bulk."""
    company = (repo.get_company(symbol) if company is _NO_ROW else company) or {}
    quote = repo.get_quote(symbol) if quote is _NO_ROW else quote
    fd = repo.get_financials(symbol, "annual", auto_refresh=auto_refresh)
    fq = repo.get_financials(symbol, "quarterly", basis=fd.basis if not fd.empty else None, auto_refresh=False)
    snap = V.market_snapshot(quote, fd, fq)
    row = {
        "symbol": symbol, "name": company.get("name", symbol), "sector": company.get("sector"),
        "industry": company.get("industry"), "is_sample": bool(company.get("is_sample")),
        "is_financial": R.is_financial(company),
        "price": snap.get("price"), "market_cap": snap.get("market_cap"),
        "day_change": (quote["price"] / quote["prev_close"] - 1) if quote and quote.get("price") and quote.get("prev_close") else None,
        "pe": snap.get("pe"), "pb": snap.get("pb"), "ev_ebitda": snap.get("ev_ebitda"),
        "dividend_yield": snap.get("dividend_yield"),
        "latest_fy": fd.periods[-1] if not fd.empty else None, "basis": fd.basis,
        "data_type": "sample" if company.get("is_sample") else "third_party",
        "quote_time": (quote or {}).get("as_of") or (quote or {}).get("fetched_at"),
    }
    if not fd.empty:
        row.update(_fundamentals(fd, row["is_financial"]))
        row["currency"] = fd.currency
        if fd.currency != "INR":  # never show USD amounts under a rupee label
            row["revenue"] = row["net_income"] = None
        if row["is_financial"]:
            # EV/EBITDA, current ratio and D/E are not meaningful for lenders (debt is raw material).
            for k in ("ev_ebitda", "current_ratio", "debt_to_equity", "interest_coverage"):
                row[k] = None
    return row


def universe_metrics(symbols: list[str] | None = None) -> pd.DataFrame:
    if symbols is None:
        symbols = repo.list_companies(universe_only=True)["symbol"].tolist()
    comps, quotes = repo.get_companies(symbols), repo.get_quotes(symbols)
    rows = [company_metrics(s, company=comps.get(s), quote=quotes.get(s)) for s in symbols]
    df = pd.DataFrame(rows)
    for col in METRIC_COLUMNS:
        if col not in df:
            df[col] = None
    return df


def universe_frame() -> pd.DataFrame:
    """Universe metrics plus the industry and AMFI category of each company - what the screener, Explore and the
    Industry pages read. Kept free of web-framework imports so it can run in a worker process."""
    from ..content.industries import industry_of
    from ..data import securities as S
    df = universe_metrics()
    df["industry_id"] = [industry_of(s, sec, ind) for s, sec, ind in zip(df["symbol"], df["sector"], df["industry"])]
    cats = S.category_map()
    df["category"] = [cats.get(s.rsplit(".", 1)[0], (None, None))[0] if not s.startswith("SAMPLE-") else None for s in df["symbol"]]
    return df


def _worker_universe_frame() -> pd.DataFrame:            # entry point inside the worker process
    from .. import db
    db.get_engine()
    return universe_frame()


PRESETS = {
    "Quality compounders": {"roe": (0.15, None), "roce": (0.15, None), "debt_to_equity": (None, 0.5),
                            "revenue_cagr_3y": (0.08, None)},
    "Low-debt value": {"pe": (None, 20.0), "debt_to_equity": (None, 0.3), "roe": (0.10, None)},
    "High growth": {"revenue_growth": (0.15, None), "net_income_growth": (0.15, None)},
    "Cash generators": {"cfo_to_net_income": (0.9, None), "fcf_margin": (0.08, None)},
    "Dividend payers": {"dividend_yield": (0.02, None), "net_margin": (0.08, None)},
}


def apply_filters(df: pd.DataFrame, filters: dict[str, tuple[float | None, float | None]],
                  keep_missing: bool = False) -> pd.DataFrame:
    """Each filter is (min, max). Companies with a missing metric are excluded unless keep_missing."""
    mask = pd.Series(True, index=df.index)
    for col, (lo, hi) in filters.items():
        s = pd.to_numeric(df[col], errors="coerce")
        cond = pd.Series(True, index=df.index)
        if lo is not None:
            cond &= s >= lo
        if hi is not None:
            cond &= s <= hi
        if keep_missing:
            cond |= s.isna()
        else:
            cond &= s.notna()
        mask &= cond
    return df[mask]
