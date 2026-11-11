"""Rule-based risk assessment.

Every flag shows the metric, the threshold used and the reasoning, so the user can disagree
with a threshold rather than trust a black box. Sector considerations are GENERAL industry
risks (labelled as such) - they are not findings about the specific company.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.repository import FinancialData
from . import ratios as R
from . import technicals as T

LEVELS = ["good", "warning", "serious", "critical"]
LEVEL_LABEL = {"good": "LOW", "warning": "MODERATE", "serious": "ELEVATED", "critical": "HIGH", "na": "N/A"}

SECTOR_CONSIDERATIONS = {
    "Technology": ["Revenue largely in foreign currency - INR/USD movements affect reported growth and margins.",
                   "Client concentration in US/European BFSI and retail verticals; discretionary IT spend is cyclical.",
                   "Employee costs and attrition drive margins; visa/immigration policy changes in client countries."],
    "Financial Services": ["Asset quality (GNPA/NNPA) and credit costs through the cycle.",
                           "Interest-rate and liquidity risk; deposit franchise (CASA) and funding costs.",
                           "Extensive RBI regulation: capital adequacy, provisioning norms, priority-sector lending."],
    "Basic Materials": ["Commodity price cycles (steel, aluminium, cement, chemicals) and input-cost volatility (coal, iron ore).",
                        "High fixed costs and capex intensity amplify earnings swings (operating leverage).",
                        "Environmental clearances, emission norms and possible carbon-related regulation."],
    "Healthcare": ["USFDA inspection outcomes (warning letters / import alerts) for export-oriented plants.",
                   "Domestic price controls under the Drug Price Control Order (NPPA) on scheduled formulations.",
                   "Generic price erosion in the US and patent litigation."],
    "Consumer Defensive": ["Raw-material inflation (agri commodities, crude derivatives, packaging).",
                           "Rural demand sensitivity to monsoon and farm incomes.",
                           "Competition from D2C brands and quick-commerce channel shifts."],
    "Consumer Cyclical": ["Demand cyclicality tied to consumer sentiment, credit availability and interest rates.",
                          "Auto sector: emission norms, EV transition and commodity costs.",
                          "Discretionary spending is the first to be cut in downturns."],
    "Energy": ["Crude oil and gas price volatility; refining and marketing margins.",
               "Government pricing interventions and windfall taxes.",
               "Long-term energy-transition risk."],
    "Utilities": ["Tariffs set by electricity regulators (CERC/SERCs) cap returns.",
                  "Receivable risk from state distribution companies.",
                  "Fuel supply and renewable-capacity transition."],
    "Industrials": ["Order-book execution and working-capital intensity.",
                    "Dependence on government capex cycles and project approvals.",
                    "Commodity cost pass-through in fixed-price contracts."],
    "Communication Services": ["Telecom regulation (TRAI/DoT), spectrum auction costs and licence fees.",
                               "Pricing competition and capex for network upgrades.",
                               "High leverage common in the sector."],
    "Real Estate": ["RERA compliance, approval delays and project execution.",
                    "Interest-rate sensitivity of demand and funding.",
                    "Land-title and regulatory risks."],
}
GENERAL_REGULATORY = [
    "Listed-company obligations under SEBI (LODR) Regulations: timely disclosure, related-party transaction approvals, board independence.",
    "Changes in taxation (GST, corporate tax, tax on dividends/capital gains) can affect earnings or investor returns.",
    "Check the latest annual report's 'Risk management' and 'Contingent liabilities' notes for company-specific matters.",
]


def _flag(cat, title, level, value, rule, detail):
    return {"category": cat, "title": title, "level": level, "value": value, "rule": rule, "detail": detail}


def _band(v, good, warn, serious, higher_is_risk=True):
    """Map a value into a level using three cut-offs."""
    if v is None or pd.isna(v):
        return "na"
    if higher_is_risk:
        return "good" if v <= good else "warning" if v <= warn else "serious" if v <= serious else "critical"
    return "good" if v >= good else "warning" if v >= warn else "serious" if v >= serious else "critical"


def altman_z_double_prime(fd: FinancialData) -> tuple[float | None, str, dict]:
    """Altman Z'' (1995, non-manufacturers / emerging markets, no market-value term):
    Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4
    X1 = working capital / total assets, X2 = retained earnings / total assets,
    X3 = EBIT / total assets, X4 = book equity / total liabilities.
    Zones: > 2.60 safe, 1.10-2.60 grey, < 1.10 distress."""
    if fd.empty:
        return None, "n/a", {}
    ta, ca, cl = fd.latest("total_assets"), fd.latest("current_assets"), fd.latest("current_liabilities")
    re_, ebit, eq, tl = fd.latest("retained_earnings"), fd.latest("ebit"), fd.latest("total_equity"), fd.latest("total_liabilities")
    if not all(v is not None for v in (ta, ca, cl, re_, ebit, eq, tl)) or not ta or not tl:
        return None, "insufficient data", {}
    x = {"X1": (ca - cl) / ta, "X2": re_ / ta, "X3": ebit / ta, "X4": eq / tl}
    z = 6.56 * x["X1"] + 3.26 * x["X2"] + 6.72 * x["X3"] + 1.05 * x["X4"]
    zone = "safe" if z > 2.6 else "grey" if z >= 1.1 else "distress"
    return float(z), zone, x


def assess(company: dict, fd: FinancialData, prices: pd.DataFrame | None = None,
           shareholding: pd.DataFrame | None = None, segments: pd.DataFrame | None = None) -> list[dict]:
    flags: list[dict] = []
    fin = R.is_financial(company)
    rt = R.compute_ratios(fd) if not fd.empty else pd.DataFrame()
    last = rt.iloc[:, -1] if not rt.empty else pd.Series(dtype=float)

    def lv(key):
        return last.get(key) if key in last.index else None

    # ---- debt
    if fin:
        flags.append(_flag("Debt", "Leverage (financial company)", "na", "n.m.", "—",
                           "Debt/equity is structurally high for lenders; assess capital adequacy (CRAR) and asset quality instead."))
    else:
        de = lv("debt_to_equity")
        flags.append(_flag("Debt", "Debt to equity", _band(de, 0.5, 1.0, 2.0), f"{de:.2f}x" if de is not None and pd.notna(de) else "—",
                           "≤0.5x low · ≤1x moderate · ≤2x elevated · >2x high",
                           "Borrowings relative to shareholders' funds."))
        ic = lv("interest_coverage")
        flags.append(_flag("Debt", "Interest coverage", _band(ic, 6, 3, 1.5, higher_is_risk=False),
                           f"{ic:.1f}x" if ic is not None and pd.notna(ic) else "—",
                           "≥6x low · ≥3x moderate · ≥1.5x elevated · <1.5x high",
                           "Ability of operating profit (EBIT) to service interest."))
        nde = lv("net_debt_to_ebitda")
        flags.append(_flag("Debt", "Net debt / EBITDA", _band(nde, 1, 2.5, 4), f"{nde:.2f}x" if nde is not None and pd.notna(nde) else "—",
                           "≤1x low · ≤2.5x moderate · ≤4x elevated · >4x high (negative = net cash)",
                           "Years of operating profit needed to repay net debt."))
    # ---- liquidity
    if not fin:
        cr = lv("current_ratio")
        flags.append(_flag("Liquidity", "Current ratio", _band(cr, 1.5, 1.0, 0.8, higher_is_risk=False),
                           f"{cr:.2f}x" if cr is not None and pd.notna(cr) else "—",
                           "≥1.5x low · ≥1x moderate · ≥0.8x elevated · <0.8x high",
                           "Short-term assets vs short-term obligations. Some businesses (e.g. FMCG with negative working capital) run below 1x by design."))
    # ---- profitability
    roe = lv("roe")
    flags.append(_flag("Profitability", "Return on equity", _band(roe, 0.15, 0.10, 0.05, higher_is_risk=False),
                       f"{roe:.1%}" if roe is not None and pd.notna(roe) else "—",
                       "≥15% low · ≥10% moderate · ≥5% elevated · <5% high",
                       "Below the cost of equity (~12-14% in India) means value is not being created for shareholders."))
    if not rt.empty and "ebitda_margin" in rt.index:
        m = rt.loc["ebitda_margin"].dropna()
        if len(m) >= 3:
            change = m.iloc[-1] - m.iloc[-3]
            flags.append(_flag("Profitability", "EBITDA margin trend (2 yrs)",
                               _band(-change, 0.0, 0.02, 0.05), f"{change * 100:+.1f} pp",
                               "Improving low · ≤2pp fall moderate · ≤5pp elevated · >5pp high",
                               "Sustained margin compression can signal pricing pressure or cost inflation."))
    ni = fd.get("net_income").dropna() if not fd.empty else pd.Series(dtype=float)
    if len(ni):
        losses = int((ni < 0).sum())
        flags.append(_flag("Profitability", "Loss-making years", "good" if losses == 0 else "serious" if losses == 1 else "critical",
                           f"{losses} of {len(ni)}", "0 low · 1 elevated · ≥2 high", "Years with a net loss in the period shown."))
    # ---- cash flow
    if not fin and not rt.empty:
        conv = rt.loc["cfo_to_net_income"].dropna().iloc[-3:] if "cfo_to_net_income" in rt.index else pd.Series(dtype=float)
        if len(conv):
            avg = conv.mean()
            flags.append(_flag("Cash flow", "Cash conversion (CFO / net profit, 3-yr avg)",
                               _band(avg, 0.9, 0.7, 0.5, higher_is_risk=False), f"{avg:.2f}x",
                               "≥0.9x low · ≥0.7x moderate · ≥0.5x elevated · <0.5x high",
                               "Persistently low conversion can indicate aggressive revenue recognition or working-capital build-up."))
        fcf = (fd.get("fcf").fillna(fd.get("cfo") + fd.get("capex"))).dropna()
        if len(fcf):
            neg = int((fcf < 0).sum())
            flags.append(_flag("Cash flow", "Negative free cash flow years", "good" if neg == 0 else "warning" if neg == 1 else "serious",
                               f"{neg} of {len(fcf)}", "0 low · 1 moderate · ≥2 elevated",
                               "Repeated negative FCF means growth or dividends rely on external funding."))
    # ---- concentration
    if segments is not None and not segments.empty:
        latest = segments[segments["period"] == sorted(segments["period"].unique())[-1]]
        share = latest["revenue"] / latest["revenue"].sum()
        hhi = float((share ** 2).sum())
        top = float(share.max())
        flags.append(_flag("Concentration", "Largest revenue segment share", _band(top, 0.5, 0.7, 0.85), f"{top:.0%}",
                           "≤50% low · ≤70% moderate · ≤85% elevated · >85% high",
                           f"Herfindahl index of segment mix = {hhi:.2f} (1.0 = single segment)."))
    else:
        flags.append(_flag("Concentration", "Segment concentration", "na", "—", "—",
                           "No segment data entered (Company Research → Business & segments)."))
    if shareholding is not None and not shareholding.empty:
        latest = shareholding[shareholding["period"] == sorted(shareholding["period"].unique())[-1]]
        pledge = latest["pledged_pct"].dropna()
        if len(pledge):
            p = float(pledge.max())
            flags.append(_flag("Concentration", "Promoter pledge", _band(p, 0, 10, 25), f"{p:.1f}%",
                               "0% low · ≤10% moderate · ≤25% elevated · >25% high",
                               "Pledged promoter shares may be sold by lenders in a falling market (forced selling)."))
    # ---- market
    if prices is not None and len(prices) > 60:
        px = prices.tail(T.TRADING_DAYS)
        vol = T.annualised_volatility(px["close"])
        mdd = T.max_drawdown(px["close"])
        flags.append(_flag("Market", "Annualised volatility (1 yr)", _band(vol, 0.25, 0.35, 0.50), f"{vol:.0%}",
                           "≤25% low · ≤35% moderate · ≤50% elevated · >50% high", "Standard deviation of daily returns × √252."))
        flags.append(_flag("Market", "Maximum drawdown (1 yr)", _band(-mdd, 0.15, 0.25, 0.40), f"{mdd:.0%}",
                           "≤15% low · ≤25% moderate · ≤40% elevated · >40% high", "Largest peak-to-trough fall in the last year."))
    # ---- solvency score
    if not fin:
        z, zone, _ = altman_z_double_prime(fd)
        if z is not None:
            flags.append(_flag("Debt", "Altman Z'' score", {"safe": "good", "grey": "warning", "distress": "serious"}[zone],
                               f"{z:.2f} ({zone})", ">2.6 safe · 1.1-2.6 grey · <1.1 distress",
                               "Altman (1995) model for non-manufacturers/emerging markets using book values. A screening tool, not a prediction."))
    return flags


def summarise(flags: list[dict]) -> pd.DataFrame:
    """Worst level per category plus counts."""
    rank = {lvl: i for i, lvl in enumerate(LEVELS)}
    rows = []
    for cat in dict.fromkeys(f["category"] for f in flags):
        fl = [f for f in flags if f["category"] == cat and f["level"] in rank]
        worst = max(fl, key=lambda f: rank[f["level"]])["level"] if fl else "na"
        rows.append({"Category": cat, "Level": worst, "Checks": len(fl),
                     "Elevated or high": sum(1 for f in fl if rank[f["level"]] >= 2)})
    return pd.DataFrame(rows)


def overall_score(flags: list[dict]) -> float | None:
    """0 (lowest risk) to 100 (highest) - average of assessed checks."""
    pts = {"good": 0, "warning": 33, "serious": 67, "critical": 100}
    vals = [pts[f["level"]] for f in flags if f["level"] in pts]
    return float(np.mean(vals)) if vals else None
