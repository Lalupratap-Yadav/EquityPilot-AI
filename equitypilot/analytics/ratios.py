"""Financial ratios with transparent formulas.

Conventions (shown to the user in the UI):
* Returns use the AVERAGE of opening and closing balances when the prior year exists,
  otherwise the closing balance (flagged in the formula text).
* A ratio is left missing (NaN) when any input is missing or the denominator is <= 0 -
  we never substitute zeros for missing data.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.repository import FinancialData


@dataclass(frozen=True)
class RatioDef:
    label: str
    category: str
    formula: str
    kind: str              # pct | x | days | num | inr
    higher_better: bool | None
    help: str


RATIOS: dict[str, RatioDef] = {
    # growth
    "revenue_growth": RatioDef("Revenue growth (YoY)", "Growth", "Revenue_t / Revenue_t-1 - 1", "pct", True,
                               "How fast sales grew versus the previous year."),
    "ebitda_growth": RatioDef("EBITDA growth (YoY)", "Growth", "EBITDA_t / EBITDA_t-1 - 1", "pct", True,
                              "Growth in operating profit before depreciation."),
    "net_income_growth": RatioDef("Net profit growth (YoY)", "Growth", "Net profit_t / Net profit_t-1 - 1", "pct", True,
                                  "Growth in profit attributable to shareholders."),
    "eps_growth": RatioDef("EPS growth (YoY)", "Growth", "Diluted EPS_t / Diluted EPS_t-1 - 1", "pct", True,
                           "Per-share profit growth - captures dilution from new shares."),
    # profitability
    "gross_margin": RatioDef("Gross margin", "Profitability", "Gross profit / Revenue", "pct", True,
                             "Share of revenue left after direct costs."),
    "ebitda_margin": RatioDef("EBITDA margin", "Profitability", "EBITDA / Revenue", "pct", True,
                              "Operating profitability before depreciation, interest and tax."),
    "ebit_margin": RatioDef("EBIT (operating) margin", "Profitability", "EBIT / Revenue", "pct", True,
                            "Operating profit after depreciation as a share of revenue."),
    "net_margin": RatioDef("Net profit margin", "Profitability", "Net profit / Revenue", "pct", True,
                           "Bottom-line profit per rupee of revenue."),
    # returns
    "roe": RatioDef("Return on equity (ROE)", "Returns", "Net profit / Average shareholders' equity", "pct", True,
                    "Profit generated on shareholders' capital."),
    "roce": RatioDef("Return on capital employed (ROCE)", "Returns",
                     "EBIT / Average capital employed, where capital employed = Total assets - Current liabilities "
                     "(fallback: Equity + Borrowings)", "pct", True,
                     "Pre-tax operating return on all long-term capital (equity + debt)."),
    "roa": RatioDef("Return on assets (ROA)", "Returns", "Net profit / Average total assets", "pct", True,
                    "Profit generated per rupee of assets."),
    # leverage & solvency
    "debt_to_equity": RatioDef("Debt / Equity", "Leverage", "Total borrowings / Shareholders' equity", "x", False,
                               "Financial leverage. Above ~1x deserves a closer look (sector-dependent)."),
    "net_debt_to_ebitda": RatioDef("Net debt / EBITDA", "Leverage", "(Borrowings - Cash) / EBITDA", "x", False,
                                   "Years of EBITDA needed to repay net debt. Negative = net cash."),
    "interest_coverage": RatioDef("Interest coverage", "Leverage", "EBIT / Finance costs", "x", True,
                                  "How many times operating profit covers interest. Below ~3x is weak."),
    # liquidity
    "current_ratio": RatioDef("Current ratio", "Liquidity", "Current assets / Current liabilities", "x", True,
                              "Short-term assets available to meet short-term obligations."),
    "quick_ratio": RatioDef("Quick ratio", "Liquidity", "(Current assets - Inventories) / Current liabilities", "x", True,
                            "Liquidity excluding inventory, which may be slow to convert to cash."),
    # efficiency
    "asset_turnover": RatioDef("Asset turnover", "Efficiency", "Revenue / Average total assets", "x", True,
                               "Revenue generated per rupee of assets."),
    "receivable_days": RatioDef("Receivable days", "Efficiency", "Trade receivables / Revenue × 365", "days", False,
                                "Average days taken to collect from customers."),
    "inventory_days": RatioDef("Inventory days", "Efficiency", "Inventories / Cost of revenue × 365", "days", False,
                               "Average days inventory is held."),
    # cash flow quality
    "cfo_to_net_income": RatioDef("CFO / Net profit", "Cash flow", "Cash flow from operations / Net profit", "x", True,
                                  "Earnings quality: below ~0.8x persistently means profits are not turning into cash."),
    "fcf_margin": RatioDef("FCF margin", "Cash flow", "Free cash flow / Revenue, FCF = CFO - Capex", "pct", True,
                           "Cash left after reinvestment, per rupee of revenue."),
    "capex_to_revenue": RatioDef("Capex / Revenue", "Cash flow", "|Capital expenditure| / Revenue", "pct", None,
                                 "Reinvestment intensity."),
    "dividend_payout": RatioDef("Dividend payout", "Cash flow", "|Dividends paid| / Net profit", "pct", None,
                                "Share of profit distributed as dividends."),
    # per share
    "eps": RatioDef("EPS (diluted, ₹)", "Per share", "Reported diluted EPS (fallback: Net profit / Diluted shares)", "inr", True,
                    "Profit per share."),
    "bvps": RatioDef("Book value per share (₹)", "Per share", "Shareholders' equity / Shares outstanding", "inr", True,
                     "Accounting net worth per share."),
}

CATEGORIES = ["Growth", "Profitability", "Returns", "Leverage", "Liquidity", "Efficiency", "Cash flow", "Per share"]


def _div(a: pd.Series, b: pd.Series, positive_denominator: bool = True) -> pd.Series:
    a, b = a.astype(float), b.astype(float)
    if positive_denominator:
        b = b.where(b > 0)
    else:
        b = b.where(b != 0)
    return a / b


def _avg(s: pd.Series) -> pd.Series:
    """Average of opening and closing balance; first period falls back to closing balance."""
    s = s.astype(float)
    avg = (s + s.shift(1)) / 2
    return avg.fillna(s)


def _yoy(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    prev = s.shift(1)
    # growth from a negative or zero base is not meaningful
    return (s / prev.where(prev > 0) - 1)


def compute_ratios(fd: FinancialData) -> pd.DataFrame:
    """Ratio table: index = ratio key, columns = period_end (same as fd.wide)."""
    if fd.empty:
        return pd.DataFrame()
    g = fd.get
    rev, ni, ebit, ebitda = g("revenue"), g("net_income"), g("ebit"), g("ebitda")
    equity, assets, debt, cash = g("total_equity"), g("total_assets"), g("total_debt"), g("cash")
    ca, cl, inv, rec = g("current_assets"), g("current_liabilities"), g("inventory"), g("receivables")
    cfo, capex = g("cfo"), g("capex")
    fcf = g("fcf").fillna(cfo + capex.where(capex <= 0, -capex))  # capex stored negative by convention
    gross = g("gross_profit").fillna(rev - g("cogs"))
    eps = g("eps_diluted").fillna(_div(ni, g("shares_diluted")))
    cap_employed = (assets - cl).fillna(equity + debt.fillna(0))
    out = {
        "revenue_growth": _yoy(rev), "ebitda_growth": _yoy(ebitda), "net_income_growth": _yoy(ni),
        "eps_growth": _yoy(eps),
        "gross_margin": _div(gross, rev), "ebitda_margin": _div(ebitda, rev), "ebit_margin": _div(ebit, rev),
        "net_margin": _div(ni, rev),
        "roe": _div(ni, _avg(equity)), "roce": _div(ebit, _avg(cap_employed)), "roa": _div(ni, _avg(assets)),
        "debt_to_equity": _div(debt, equity), "net_debt_to_ebitda": _div(debt - cash, ebitda),
        "interest_coverage": _div(ebit, g("interest_expense").abs()),
        "current_ratio": _div(ca, cl), "quick_ratio": _div(ca - inv.fillna(0), cl),
        "asset_turnover": _div(rev, _avg(assets)), "receivable_days": _div(rec, rev) * 365,
        "inventory_days": _div(inv, g("cogs")) * 365,
        "cfo_to_net_income": _div(cfo, ni), "fcf_margin": _div(fcf, rev),
        "capex_to_revenue": _div(capex.abs(), rev), "dividend_payout": _div(g("dividends_paid").abs(), ni),
        "eps": eps, "bvps": _div(equity, g("shares_outstanding")),
    }
    df = pd.DataFrame(out).T
    df.columns = fd.wide.columns
    return df.replace([np.inf, -np.inf], np.nan)


def cagr(series: pd.Series, years: int | None = None) -> float | None:
    """Compound annual growth between the first and last valid values (both must be positive)."""
    s = series.dropna().astype(float)
    if years is not None:
        s = s.iloc[-(years + 1):]
    if len(s) < 2 or s.iloc[0] <= 0 or s.iloc[-1] <= 0:
        return None
    n = (pd.Timestamp(s.index[-1]) - pd.Timestamp(s.index[0])).days / 365.25 if isinstance(s.index[0], pd.Timestamp) else len(s) - 1
    n = round(n) if n else len(s) - 1
    return float((s.iloc[-1] / s.iloc[0]) ** (1 / n) - 1) if n > 0 else None


def ttm(fq: FinancialData, key: str) -> tuple[float | None, str | None]:
    """Trailing-twelve-month sum of the last four consecutive quarters (flow items only)."""
    if fq.empty:
        return None, None
    s = fq.get(key).dropna()
    if len(s) < 4:
        return None, None
    last4 = s.iloc[-4:]
    gaps = np.diff([pd.Timestamp(d).to_period("M").ordinal for d in last4.index])
    if not all(2 <= g <= 4 for g in gaps):  # must be consecutive quarters
        return None, None
    return float(last4.sum()), f"TTM to {pd.Timestamp(last4.index[-1]).strftime('%b %Y')}"


def piotroski_f_score(fd: FinancialData) -> tuple[int | None, list[tuple[str, bool | None]]]:
    """Piotroski F-score (0-9) for the latest year vs the prior year. Needs two years of data."""
    if fd.empty or len(fd.periods) < 2:
        return None, []
    g = fd.get

    def last2(key):
        s = g(key)
        return s.iloc[-1], s.iloc[-2]

    ni, ni0 = last2("net_income")
    assets, assets0 = last2("total_assets")
    cfo, _ = last2("cfo")
    debt, debt0 = last2("total_debt")
    ca, ca0 = last2("current_assets")
    cl, cl0 = last2("current_liabilities")
    sh, sh0 = last2("shares_outstanding")
    gp, gp0 = last2("gross_profit")
    rev, rev0 = last2("revenue")

    def ok(cond):
        try:
            return None if pd.isna(cond) else bool(cond)
        except (TypeError, ValueError):
            return None

    roa, roa0 = ni / assets if assets else np.nan, ni0 / assets0 if assets0 else np.nan
    tests = [
        ("Positive net profit", ok(ni > 0)),
        ("Positive operating cash flow", ok(cfo > 0)),
        ("ROA improved", ok(roa > roa0)),
        ("Cash flow exceeds profit (accrual quality)", ok(cfo > ni)),
        ("Leverage (debt/assets) fell", ok((debt / assets) < (debt0 / assets0)) if assets and assets0 else None),
        ("Current ratio improved", ok((ca / cl) > (ca0 / cl0)) if cl and cl0 else None),
        ("No new shares issued", ok(sh <= sh0 * 1.001)),
        ("Gross margin improved", ok((gp / rev) > (gp0 / rev0)) if rev and rev0 else None),
        ("Asset turnover improved", ok((rev / assets) > (rev0 / assets0)) if assets and assets0 else None),
    ]
    known = [t for t in tests if t[1] is not None]
    if len(known) < 6:
        return None, tests
    return sum(1 for _, v in known if v), tests


def is_financial(company: dict | None) -> bool:
    """Banks/NBFCs/insurers: EBITDA, current ratio, EV and FCF-based DCF are not meaningful."""
    if not company:
        return False
    text = f"{company.get('sector') or ''} {company.get('industry') or ''}".lower()
    return any(k in text for k in ("financial services", "bank", "insurance", "credit services", "capital markets",
                                   "asset management", "nbfc"))


def dupont(fd: FinancialData) -> pd.DataFrame:
    """3-step DuPont: ROE = Net margin × Asset turnover × Equity multiplier (average balances)."""
    if fd.empty:
        return pd.DataFrame()
    g = fd.get
    nm = _div(g("net_income"), g("revenue"))
    at = _div(g("revenue"), _avg(g("total_assets")))
    em = _div(_avg(g("total_assets")), _avg(g("total_equity")))
    df = pd.DataFrame({"Net margin": nm, "Asset turnover": at, "Equity multiplier": em, "ROE (product)": nm * at * em}).T
    df.columns = fd.wide.columns
    return df


def quality_checks(fd: FinancialData) -> list[dict]:
    """Consistency and completeness checks. Returns list of {level, check, detail}."""
    issues: list[dict] = []
    if fd.empty:
        return [{"level": "critical", "check": "No data", "detail": "No statements available for this company."}]
    g = fd.get
    for p in fd.periods:
        lbl = pd.Timestamp(p).strftime("%b %Y")
        a, l, e, mi = g("total_assets")[p], g("total_liabilities")[p], g("total_equity")[p], g("minority_interest")[p]
        if pd.notna(a) and pd.notna(l) and pd.notna(e):
            gap = a - (l + e + (0 if pd.isna(mi) else mi))
            if abs(gap) > 0.02 * abs(a):
                issues.append({"level": "warning", "check": f"Balance sheet does not balance ({lbl})",
                               "detail": f"Assets differ from liabilities + equity (+ minority interest) by {gap / abs(a):.1%}. "
                                         "This can arise from provider line-item mapping; verify with the filing."})
        r, gp, cogs = g("revenue")[p], g("gross_profit")[p], g("cogs")[p]
        if pd.notna(r) and pd.notna(gp) and pd.notna(cogs) and abs(r - cogs - gp) > 0.02 * abs(r):
            issues.append({"level": "info", "check": f"Gross profit ≠ revenue - cost of revenue ({lbl})",
                           "detail": "The provider's gross profit definition may differ from a simple subtraction."})
    key_items = ["revenue", "net_income", "total_assets", "total_equity", "cfo", "total_debt", "cash", "ebit"]
    missing = [k for k in key_items if g(k).isna().all()]
    if missing:
        issues.append({"level": "warning", "check": "Key line items missing",
                       "detail": "Not reported by the source: " + ", ".join(missing) +
                                 ". Ratios depending on them are left blank rather than estimated."})
    partial = [k for k in key_items if k not in missing and g(k).isna().any()]
    if partial:
        issues.append({"level": "info", "check": "Gaps in some years",
                       "detail": "Missing for at least one period: " + ", ".join(partial) + "."})
    if len(fd.periods) < 3:
        issues.append({"level": "info", "check": "Short history",
                       "detail": f"Only {len(fd.periods)} period(s) available - growth rates and averages are less reliable."})
    return issues
