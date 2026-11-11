"""Valuation: market multiples, WACC (CAPM), FCFF DCF, scenarios, sensitivity, reverse DCF,
justified P/B (for banks) and peer-relative valuation. All formulas are documented inline and
mirrored in the UI so a reviewer can follow every step.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np
import pandas as pd

from ..data.repository import FinancialData
from . import ratios as R


# ------------------------------------------------------------------ market multiples
def market_snapshot(quote: dict | None, fd: FinancialData, fq: FinancialData | None = None) -> dict:
    """Current valuation multiples. Earnings use TTM (last 4 quarters) when available, else latest FY."""
    out: dict = {"basis": {}}
    price = (quote or {}).get("price")
    shares = (quote or {}).get("shares_outstanding") or fd.latest("shares_outstanding")
    mcap = (quote or {}).get("market_cap") or (price * shares if price and shares else None)
    out.update(price=price, shares=shares, market_cap=mcap)

    def flow(key):
        if fq is not None and not fq.empty:
            v, lbl = R.ttm(fq, key)
            if v is not None:
                return v, lbl
        if fd.empty:
            return None, None
        s = fd.get(key).dropna()
        if s.empty:
            return None, None
        return float(s.iloc[-1]), f"FY ending {pd.Timestamp(s.index[-1]).strftime('%b %Y')}"

    ni, ni_lbl = flow("net_income")
    rev, rev_lbl = flow("revenue")
    ebitda, eb_lbl = flow("ebitda")
    equity = fd.latest("total_equity") if not fd.empty else None
    debt = fd.latest("total_debt") if not fd.empty else None
    cash = fd.latest("cash") if not fd.empty else None
    ev = mcap + (debt or 0) - (cash or 0) if mcap else None
    out.update(
        net_income=ni, revenue=rev, ebitda=ebitda, equity=equity, debt=debt, cash=cash, ev=ev,
        pe=mcap / ni if mcap and ni and ni > 0 else None,
        pb=mcap / equity if mcap and equity and equity > 0 else None,
        ps=mcap / rev if mcap and rev and rev > 0 else None,
        ev_ebitda=ev / ebitda if ev and ebitda and ebitda > 0 else None,
        ev_sales=ev / rev if ev and rev and rev > 0 else None,
        earnings_yield=ni / mcap if mcap and ni else None,
        dividend_yield=((quote or {}).get("dividend_rate") / price) if price and (quote or {}).get("dividend_rate") else None,
    )
    out["basis"] = {"earnings": ni_lbl, "revenue": rev_lbl, "ebitda": eb_lbl,
                    "balance_sheet": f"Balance sheet as of {pd.Timestamp(fd.periods[-1]).strftime('%b %Y')}" if not fd.empty else None}
    return out


MULTIPLE_FORMULAS = {
    "pe": "P/E = Market capitalisation / Net profit  (= Price / EPS)",
    "pb": "P/B = Market capitalisation / Shareholders' equity",
    "ps": "P/S = Market capitalisation / Revenue",
    "ev": "Enterprise value = Market capitalisation + Total borrowings - Cash & short-term investments",
    "ev_ebitda": "EV/EBITDA = Enterprise value / EBITDA",
    "ev_sales": "EV/Sales = Enterprise value / Revenue",
    "dividend_yield": "Dividend yield = Annual dividend per share / Price",
}


# ------------------------------------------------------------------ cost of capital
def capm_cost_of_equity(rf: float, beta: float, erp: float) -> float:
    """Ke = Rf + β × ERP"""
    return rf + beta * erp


def wacc(rf: float, beta: float, erp: float, kd_pre_tax: float, tax_rate: float,
         equity_value: float, debt_value: float) -> dict:
    ke = capm_cost_of_equity(rf, beta, erp)
    kd = kd_pre_tax * (1 - tax_rate)
    total = equity_value + debt_value
    we = equity_value / total if total > 0 else 1.0
    wd = 1 - we
    return {"ke": ke, "kd_post_tax": kd, "we": we, "wd": wd, "wacc": we * ke + wd * kd}


# ------------------------------------------------------------------ DCF
@dataclass
class DCFInputs:
    base_revenue: float              # last fiscal year revenue (INR)
    growth_start: float              # revenue growth in year 1
    growth_end: float                # growth in final explicit year (linear fade)
    ebit_margin: float
    tax_rate: float
    da_pct: float                    # depreciation as % of revenue
    capex_pct: float                 # capex as % of revenue
    nwc_pct: float                   # incremental working capital as % of incremental revenue
    wacc: float
    terminal_growth: float
    net_debt: float                  # borrowings - cash (INR); negative = net cash
    shares: float
    years: int = 5
    minority_interest: float = 0.0


@dataclass
class DCFResult:
    projection: pd.DataFrame
    pv_fcff: float
    terminal_value: float
    pv_terminal: float
    enterprise_value: float
    equity_value: float
    per_share: float
    terminal_share: float            # share of EV coming from terminal value


class DCFError(ValueError):
    pass


def run_dcf(i: DCFInputs) -> DCFResult:
    """FCFF = EBIT×(1-t) + D&A - Capex - ΔNWC;  EV = Σ FCFF_t/(1+WACC)^t + TV/(1+WACC)^N;
    TV = FCFF_N×(1+g)/(WACC-g);  Equity = EV - Net debt - Minority interest."""
    if i.wacc <= i.terminal_growth:
        raise DCFError("WACC must be greater than the terminal growth rate (Gordon growth model).")
    if i.base_revenue <= 0 or i.shares <= 0:
        raise DCFError("Base revenue and share count must be positive.")
    if i.years < 1:
        raise DCFError("Explicit forecast must be at least one year.")
    growth = np.linspace(i.growth_start, i.growth_end, i.years)
    rows, rev_prev = [], i.base_revenue
    for t, g in enumerate(growth, start=1):
        rev = rev_prev * (1 + g)
        ebit = rev * i.ebit_margin
        nopat = ebit * (1 - i.tax_rate)
        da, capex = rev * i.da_pct, rev * i.capex_pct
        d_nwc = (rev - rev_prev) * i.nwc_pct
        fcff = nopat + da - capex - d_nwc
        df = 1 / (1 + i.wacc) ** t
        rows.append({"Year": t, "Growth": g, "Revenue": rev, "EBIT": ebit, "NOPAT": nopat, "D&A": da,
                     "Capex": capex, "ΔNWC": d_nwc, "FCFF": fcff, "Discount factor": df, "PV of FCFF": fcff * df})
        rev_prev = rev
    proj = pd.DataFrame(rows).set_index("Year")
    pv_fcff = float(proj["PV of FCFF"].sum())
    tv = float(proj["FCFF"].iloc[-1] * (1 + i.terminal_growth) / (i.wacc - i.terminal_growth))
    pv_tv = tv / (1 + i.wacc) ** i.years
    ev = pv_fcff + pv_tv
    equity = ev - i.net_debt - i.minority_interest
    return DCFResult(proj, pv_fcff, tv, pv_tv, ev, equity, equity / i.shares, pv_tv / ev if ev else float("nan"))


def default_dcf_inputs(fd: FinancialData, quote: dict | None, wacc_value: float = 0.12,
                       terminal_growth: float = 0.05) -> tuple[DCFInputs | None, dict[str, str]]:
    """Starting assumptions derived from the company's own history. Every value is an editable
    ASSUMPTION; the dict explains where each default came from."""
    notes: dict[str, str] = {}
    if fd.empty:
        return None, {"error": "No financial statements available."}
    rev = fd.get("revenue").dropna()
    if rev.empty or rev.iloc[-1] <= 0:
        return None, {"error": "Revenue is missing - a revenue-based DCF cannot be built."}
    rt = R.compute_ratios(fd)
    hist_cagr = R.cagr(rev, 3)
    g0 = float(np.clip(hist_cagr if hist_cagr is not None else 0.08, 0.0, 0.25))
    notes["growth_start"] = (f"Historical revenue CAGR {hist_cagr:.1%} (last {min(3, len(rev) - 1)} yrs), capped to 0-25%"
                             if hist_cagr is not None else "No usable history - generic 8% placeholder")

    def avg(key, default, lo, hi, label):
        s = rt.loc[key].dropna().iloc[-3:] if key in rt.index else pd.Series(dtype=float)
        if s.empty:
            notes[key] = f"Not available - default {default:.1%}"
            return default
        v = float(np.clip(s.mean(), lo, hi))
        notes[key] = f"{label}: 3-yr average {s.mean():.1%}" + (" (clipped)" if v != s.mean() else "")
        return v

    margin = avg("ebit_margin", 0.15, -0.5, 0.6, "EBIT margin")
    capex_pct = avg("capex_to_revenue", 0.05, 0.0, 0.5, "Capex/Revenue")
    da = (fd.get("depreciation") / fd.get("revenue")).dropna().iloc[-3:]
    da_pct = float(np.clip(da.mean(), 0, 0.3)) if len(da) else capex_pct * 0.8
    notes["da_pct"] = f"D&A/Revenue: 3-yr average {da.mean():.1%}" if len(da) else "Not available - 80% of capex"
    tax = (fd.get("tax") / fd.get("pretax_income")).where(fd.get("pretax_income") > 0).dropna().iloc[-3:]
    tax_rate = float(np.clip(tax.mean(), 0.15, 0.35)) if len(tax) else 0.25
    notes["tax_rate"] = (f"Effective tax rate: 3-yr average {tax.mean():.1%} (bounded 15-35%)" if len(tax)
                         else "Not available - 25% (approx. Indian corporate rate under the new regime incl. surcharge/cess)")
    debt, cash = fd.latest("total_debt") or 0.0, fd.latest("cash") or 0.0
    shares = (quote or {}).get("shares_outstanding") or fd.latest("shares_outstanding")
    if not shares:
        return None, {"error": "Share count is missing - per-share value cannot be computed."}
    notes["nwc_pct"] = "Assumption: 10% of incremental revenue tied up in working capital"
    notes["growth_end"] = "Assumption: growth fades linearly towards the terminal rate by the final year"
    notes["net_debt"] = "Latest balance sheet: borrowings - cash & short-term investments"
    return DCFInputs(
        base_revenue=float(rev.iloc[-1]), growth_start=g0,
        growth_end=float(max(terminal_growth + 0.01, min(g0, 0.10))), ebit_margin=margin, tax_rate=tax_rate,
        da_pct=da_pct, capex_pct=capex_pct, nwc_pct=0.10, wacc=wacc_value, terminal_growth=terminal_growth,
        net_debt=float(debt - cash), shares=float(shares), minority_interest=fd.latest("minority_interest") or 0.0,
    ), notes


SCENARIO_SHIFTS = {
    # (growth shift, margin shift, wacc shift, terminal-growth shift) applied to the base case
    "Bear": (-0.04, -0.03, 0.01, -0.01),
    "Base": (0.0, 0.0, 0.0, 0.0),
    "Bull": (0.03, 0.02, -0.01, 0.005),
}


def scenarios(base: DCFInputs, shifts: dict[str, tuple] | None = None) -> dict[str, DCFResult | str]:
    out: dict[str, DCFResult | str] = {}
    for name, (dg, dm, dw, dtg) in (shifts or SCENARIO_SHIFTS).items():
        inp = replace(base, growth_start=base.growth_start + dg, growth_end=base.growth_end + dg,
                      ebit_margin=base.ebit_margin + dm, wacc=base.wacc + dw,
                      terminal_growth=base.terminal_growth + dtg)
        try:
            out[name] = run_dcf(inp)
        except DCFError as exc:
            out[name] = str(exc)
    return out


def sensitivity(base: DCFInputs, waccs: list[float], growths: list[float]) -> pd.DataFrame:
    """Per-share value grid: rows = WACC, columns = terminal growth."""
    grid = pd.DataFrame(index=[f"{w:.1%}" for w in waccs], columns=[f"{g:.1%}" for g in growths], dtype=float)
    for w in waccs:
        for g in growths:
            try:
                grid.loc[f"{w:.1%}", f"{g:.1%}"] = run_dcf(replace(base, wacc=w, terminal_growth=g)).per_share
            except DCFError:
                grid.loc[f"{w:.1%}", f"{g:.1%}"] = np.nan
    return grid


def reverse_dcf(base: DCFInputs, target_price: float, lo: float = -0.2, hi: float = 0.6) -> float | None:
    """Constant explicit-period growth that makes DCF value = market price (bisection)."""
    def value(g):
        return run_dcf(replace(base, growth_start=g, growth_end=g)).per_share - target_price
    try:
        f_lo, f_hi = value(lo), value(hi)
    except DCFError:
        return None
    if f_lo * f_hi > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        f_mid = value(mid)
        if abs(f_mid) < 0.01:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def justified_pb(roe: float, cost_of_equity: float, growth: float) -> float | None:
    """Gordon-growth justified P/B = (ROE - g) / (Ke - g). Suited to banks and financials."""
    if cost_of_equity <= growth:
        return None
    return (roe - growth) / (cost_of_equity - growth)


def peer_relative(target: dict, peers: pd.DataFrame) -> pd.DataFrame:
    """Implied price from peer median multiples. `target` is a market_snapshot dict;
    `peers` has columns pe, pb, ev_ebitda (one row per peer)."""
    rows = []
    shares = target.get("shares")
    if not shares:
        return pd.DataFrame()
    net_debt = (target.get("debt") or 0) - (target.get("cash") or 0)
    for mult, metric, is_ev in (("pe", "net_income", False), ("pb", "equity", False), ("ev_ebitda", "ebitda", True)):
        col = peers[mult].dropna() if mult in peers else pd.Series(dtype=float)
        col = col[col > 0]  # negative multiples (loss-makers) are not meaningful for a median
        base = target.get(metric)
        if col.empty or not base or base <= 0:
            rows.append({"Method": mult, "Peer median": np.nan, "Company metric": base, "Implied price": np.nan,
                         "Peers used": len(col)})
            continue
        med = float(col.median())
        value = med * base - (net_debt if is_ev else 0)
        rows.append({"Method": mult, "Peer median": med, "Company metric": base,
                     "Implied price": value / shares, "Peers used": len(col)})
    return pd.DataFrame(rows)


def inputs_table(i: DCFInputs) -> dict:
    return asdict(i)
