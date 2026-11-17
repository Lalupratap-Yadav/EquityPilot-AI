"""Financial Health dashboard - a transparent, rule-based view of seven areas of a company's finances.

How it works (shown to the user next to every result)
* Each area lists the underlying metrics with their value, the formula and the period they come from.
* A metric is rated only where a documented rule of thumb exists (content/metrics_guide.py for companies,
  analytics/bank.py for banks); otherwise it is shown without a rating.
* Rating points: strong / low risk = 2, moderate = 1, weak / elevated or high risk = 0.
  Area result = average points of its rated metrics: >= 1.5 "Strong", below 0.5 "Weak", otherwise "Adequate".
* An area with no rated metric that has data is "Insufficient data" - missing values are never treated as zero.
* Banks and NBFCs use bank-specific metrics (asset quality, capital, funding); debt, liquidity and cash-flow ratios
  of ordinary companies are "Not applicable" to them.
* Valuation is context, not health: today's multiple is compared with the company's own history and never rated.
* There is deliberately no single overall score: the general benchmarks are not industry-specific, so one number
  would suggest more precision than the data supports.
"""
from __future__ import annotations

import math

import pandas as pd

from .. import formatting as F
from ..content import metrics_guide as MG
from ..data import repository as repo
from . import bank as B
from . import ratios as R
from . import valuation as V

POINTS = {"strong": 2, "moderate": 1, "weak": 0, "good": 2, "warning": 1, "serious": 0, "critical": 0}
RULES = {"strong": "Strong", "moderate": "Moderate", "weak": "Weak", "good": "Low risk", "warning": "Moderate risk",
         "serious": "Elevated risk", "critical": "High risk"}
FORMULAS = {
    "revenue_growth": "Revenue this year / revenue last year - 1",
    "net_income_growth": "Net profit this year / net profit last year - 1",
    "revenue_cagr_3y": "(Revenue now / revenue 3 years ago)^(1/3) - 1",
    "ebitda_margin": "EBITDA / revenue",
    "net_margin": "Net profit / revenue",
    "roe": "Net profit / average shareholders' equity",
    "roa": "Net profit / average total assets",
    "roce": "EBIT / average capital employed (total assets - current liabilities)",
    "asset_turnover": "Revenue / average total assets",
    "debt_to_equity": "Total debt / shareholders' equity",
    "net_debt_to_ebitda": "(Total debt - cash) / EBITDA",
    "interest_coverage": "EBIT / interest expense",
    "current_ratio": "Current assets / current liabilities",
    "quick_ratio": "(Current assets - inventory) / current liabilities",
    "cfo_to_net_income": "Cash from operations / net profit",
    "fcf_margin": "Free cash flow (CFO - capex) / revenue",
    "fcf_positive_years": "Years with positive free cash flow among the last three",
    "pe": "Share price / earnings per share", "pb": "Share price / book value per share",
}
LABELS = {"revenue_growth": "Revenue growth", "net_income_growth": "Net profit growth", "revenue_cagr_3y": "Revenue CAGR (3 years)",
          "ebitda_margin": "EBITDA margin", "net_margin": "Net margin", "roe": "Return on equity (ROE)", "roa": "Return on assets (ROA)",
          "roce": "Return on capital employed (ROCE)", "asset_turnover": "Asset turnover", "debt_to_equity": "Debt to equity",
          "net_debt_to_ebitda": "Net debt / EBITDA", "interest_coverage": "Interest coverage", "current_ratio": "Current ratio",
          "quick_ratio": "Quick ratio", "cfo_to_net_income": "Cash conversion (CFO / net profit)", "fcf_margin": "Free-cash-flow margin",
          "fcf_positive_years": "Positive free cash flow", "pe": "P/E", "pb": "P/B"}
UNITS = {"revenue_growth": "pct", "net_income_growth": "pct", "revenue_cagr_3y": "pct", "ebitda_margin": "pct", "net_margin": "pct",
         "roe": "pct", "roa": "pct", "roce": "pct", "fcf_margin": "pct", "asset_turnover": "x", "debt_to_equity": "x",
         "net_debt_to_ebitda": "x", "interest_coverage": "x", "current_ratio": "x", "quick_ratio": "x", "cfo_to_net_income": "x",
         "fcf_positive_years": "count", "pe": "x", "pb": "x"}


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _metric(key: str, value, period: str | None, financial: bool, rate_as: str | None = None, note: str | None = None) -> dict:
    v = _num(value)
    a = MG.assess(rate_as or key, v, financial) if v is not None else None
    return {"key": key, "label": LABELS.get(key, key), "value": v, "unit": UNITS.get(key, "x"), "period": period,
            "formula": FORMULAS.get(key), "rating": a["level"] if a else None, "rating_label": RULES.get(a["level"]) if a else None,
            "rating_text": a["text"] if a else None, "rated": a is not None, "note": note,
            "missing": v is None}


def _area(key: str, title: str, question: str, metrics: list[dict], not_applicable: str | None = None) -> dict:
    if not_applicable:
        return {"key": key, "title": title, "question": question, "status": "not_applicable", "status_label": "Not applicable",
                "explain": not_applicable, "metrics": [], "rated_count": 0, "points": None}
    rated = [m for m in metrics if m["rated"]]
    if not rated:
        have = [m for m in metrics if not m["missing"]]
        return {"key": key, "title": title, "question": question, "status": "insufficient", "status_label": "Insufficient data",
                "explain": ("None of the rated metrics for this area is available for the latest period." if not have
                            else "The available metrics have no fair general benchmark, so this area is shown without a rating."),
                "metrics": metrics, "rated_count": 0, "points": None}
    pts = sum(POINTS[m["rating"]] for m in rated) / len(rated)
    status = "strong" if pts >= 1.5 else "weak" if pts < 0.5 else "adequate"
    return {"key": key, "title": title, "question": question, "status": status,
            "status_label": {"strong": "Strong", "adequate": "Adequate", "weak": "Weak"}[status],
            "explain": f"Average of {len(rated)} rated metric{'s' if len(rated) != 1 else ''}: {pts:.2f} points out of 2.",
            "metrics": metrics, "rated_count": len(rated), "points": round(pts, 2)}


def _latest(rt: pd.DataFrame, key: str) -> tuple[float | None, str | None]:
    """Value for the LATEST fiscal year only - an older year is never substituted silently."""
    if rt.empty or key not in rt.index:
        return None, None
    col = rt.columns[-1]
    return _num(rt.loc[key, col]), F.fiscal_label(col)


def _bank_metric(df: pd.DataFrame, key: str) -> dict:
    label, help_, _higher, cuts = B.BANK_METRICS[key]
    w = B.wide(df)
    if w.empty or key not in w.index or w.loc[key].dropna().empty:
        return {"key": key, "label": label.replace(" %", ""), "value": None, "unit": "pct_points", "period": None, "formula": help_,
                "rating": None, "rating_label": None, "rating_text": None, "rated": False, "missing": True,
                "note": "Not entered yet - add it from the bank's quarterly disclosure on the company's Bank metrics tab."}
    s = w.loc[key].dropna()
    v = float(s.iloc[-1])
    lvl = B._level(key, v)
    rated = lvl in POINTS
    return {"key": key, "label": label.replace(" %", ""), "value": v, "unit": "pct_points", "period": str(s.index[-1]),
            "formula": help_, "rating": lvl if rated else None, "rating_label": RULES.get(lvl) if rated else None,
            "rating_text": (f"Screening band: {'higher' if B.BANK_METRICS[key][2] else 'lower'} is better" if rated else None),
            "rated": rated, "missing": False, "note": "Entered from the bank's disclosure (user-entered, with source)."}


def health(symbol: str) -> dict:
    c = repo.get_company(symbol) or {}
    financial = R.is_financial(c)
    fd = repo.get_financials(symbol, auto_refresh=False)
    rt = R.compute_ratios(fd) if not fd.empty else pd.DataFrame()
    if not rt.empty:
        rt = rt.reindex(columns=sorted(rt.columns))
    latest_fy = F.fiscal_label(rt.columns[-1]) if not rt.empty else None

    def m(key, **kw):
        v, p = _latest(rt, key)
        return _metric(key, v, p, financial, **kw)
    rev = fd.get("revenue").sort_index() if not fd.empty else pd.Series(dtype=float)
    cagr3 = R.cagr(rev.dropna(), 3) if len(rev.dropna()) >= 4 else None
    growth = [m("revenue_growth"), m("net_income_growth"),
              _metric("revenue_cagr_3y", cagr3, f"{F.fiscal_label(rev.dropna().index[-4])}-{latest_fy}" if cagr3 is not None else None,
                      financial, rate_as="revenue_growth",
                      note="Rated with the same thresholds as one-year revenue growth.")]
    areas = [_area("growth", "Growth", "Are sales and profits growing?", growth)]
    if financial:
        bm = repo.get_bank_metrics(symbol) if hasattr(repo, "get_bank_metrics") else pd.DataFrame()
        areas.append(_area("profitability", "Profitability", "How much profit does it earn on its capital and assets?",
                           [m("roe"), m("roa"), m("net_margin")]))
        areas.append(_area("asset_quality", "Asset quality", "How much of the loan book is not being repaid?",
                           [_bank_metric(bm, k) for k in ("gnpa", "nnpa", "pcr", "credit_cost")]))
        areas.append(_area("capital", "Capital", "Is there enough capital to absorb losses?", [_bank_metric(bm, "crar")]))
        areas.append(_area("funding", "Funding & efficiency", "Are deposits low-cost and costs under control?",
                           [_bank_metric(bm, k) for k in ("casa", "cost_to_income", "nim")]))
        na = "For banks and NBFCs, borrowing and lending are the business, so ordinary debt, liquidity and cash-flow ratios do not measure their health. See Asset quality, Capital and Funding instead."
        areas.append(_area("debt", "Debt", "Is borrowing at a safe level?", [], not_applicable=na))
        areas.append(_area("cash_flow", "Cash flow", "Do profits turn into cash?", [], not_applicable=na))
    else:
        fcf = rt.loc["fcf_margin"].dropna() if not rt.empty and "fcf_margin" in rt.index else pd.Series(dtype=float)
        last3 = fcf.iloc[-3:] if len(fcf) else fcf
        pos = int((last3 > 0).sum()) if len(last3) == 3 else None
        fcf_rating = None if pos is None else ("strong" if pos == 3 else "moderate" if pos == 2 else "weak")
        fcf_metric = {"key": "fcf_positive_years", "label": LABELS["fcf_positive_years"], "value": pos, "unit": "count",
                      "period": f"{F.fiscal_label(last3.index[0])}-{F.fiscal_label(last3.index[-1])}" if pos is not None else None,
                      "formula": FORMULAS["fcf_positive_years"], "rating": fcf_rating, "rating_label": RULES.get(fcf_rating) if fcf_rating else None,
                      "rating_text": {"strong": "Positive free cash flow in each of the last three years.",
                                      "moderate": "Positive in two of the last three years.",
                                      "weak": "Negative in two or more of the last three years."}.get(fcf_rating or "", None),
                      "rated": fcf_rating is not None, "missing": pos is None,
                      "note": "Needs three years of cash-flow data." if pos is None else None}
        areas.append(_area("profitability", "Profitability", "How much of each rupee of sales becomes profit?",
                           [m("roe"), m("ebitda_margin"), m("net_margin")]))
        areas.append(_area("debt", "Debt", "Is borrowing at a safe level?", [m("debt_to_equity"), m("net_debt_to_ebitda"), m("interest_coverage")]))
        areas.append(_area("liquidity", "Liquidity", "Can it pay bills due within a year?", [m("current_ratio"), m("quick_ratio")]))
        areas.append(_area("cash_flow", "Cash flow", "Do profits turn into cash?", [m("cfo_to_net_income"), m("fcf_margin"), fcf_metric]))
        areas.append(_area("efficiency", "Capital efficiency", "How well does it use the money invested in the business?",
                           [m("roce"), m("asset_turnover")]))
    # valuation: context only, compared with the company's own history
    quote = repo.get_quote(symbol)
    fq = repo.get_financials(symbol, "quarterly", basis=fd.basis if not fd.empty else None, auto_refresh=False)
    snap = V.market_snapshot(quote, fd, fq) if not fd.empty else {}
    px = repo.get_prices(symbol, auto_refresh=False)
    bands = V.multiple_bands(V.multiple_history(fd, px), snap) if snap else {}
    val_metrics = []
    for k in ("pe", "pb"):
        b = bands.get(k) or {}
        cur = _num(snap.get(k)) if snap else None
        vs = _num(b.get("vs_median"))
        txt = None
        if cur is not None and vs is not None:
            txt = (f"{abs(vs) * 100:.0f}% {'above' if vs > 0 else 'below'} its own median of {b['median']:.1f}x "
                   f"across {b['n']} fiscal year-ends" if abs(vs) >= 0.05 else f"Close to its own median of {b['median']:.1f}x")
        val_metrics.append({"key": k, "label": LABELS[k], "value": cur, "unit": "x", "period": "Latest price",
                            "formula": FORMULAS[k], "rating": None, "rating_label": None, "rated": False, "missing": cur is None,
                            "rating_text": txt, "note": None if cur is not None else "Needs positive earnings (P/E) or book value (P/B)."})
    areas.append({"key": "valuation", "title": "Valuation (context)", "question": "Is the share expensive compared with its own history?",
                  "status": "context" if any(not v["missing"] for v in val_metrics) else "insufficient",
                  "status_label": "Context only" if any(not v["missing"] for v in val_metrics) else "Insufficient data",
                  "explain": "Shown for context and never rated: a higher multiple can be justified by better growth or quality.",
                  "metrics": val_metrics, "rated_count": 0, "points": None})
    have = sum(1 for a in areas if a["status"] in ("strong", "adequate", "weak"))
    rateable = sum(1 for a in areas if a["status"] not in ("not_applicable", "context") and a["key"] != "valuation")
    return {"symbol": symbol, "is_financial": financial, "latest_fy": latest_fy, "basis": fd.basis if not fd.empty else None,
            "currency": fd.currency if not fd.empty else "INR", "sources": fd.sources if not fd.empty else [],
            "fetched_at": fd.fetched_at, "areas": areas, "areas_with_data": have, "areas_rateable": rateable,
            "method": [
                "Each metric uses the latest fiscal year only; an older year is never substituted for a missing value.",
                "Ratings use documented general rules of thumb (companies) or EquityPilot's bank screening bands (banks); "
                "they are not industry-specific targets.",
                "Points: strong / low risk = 2, moderate = 1, weak or elevated risk = 0. Area = average of rated metrics "
                "(1.5 or more Strong, below 0.5 Weak, otherwise Adequate).",
                "Areas without a rated metric show 'Insufficient data'. There is no overall company score.",
                "Educational analysis, not investment advice."],
            "benchmark_note": MG.BENCHMARK_NOTE}
