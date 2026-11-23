"""Case studies with real companies, built only from the statements EquityPilot has already stored (no provider calls).

Every figure carries its financial year, source, data type and fetch time; ratios are shown with the formula and the
inputs used, so the learner can redo the arithmetic. If statements are missing the case study says so instead of
showing anything estimated."""
from __future__ import annotations

import math

from ... import formatting as F

CASE_COMPANIES = ["TCS.NS", "HINDUNILVR.NS", "TATASTEEL.NS", "HDFCBANK.NS", "RELIANCE.NS"]

_FIGURES = [("revenue", "Revenue"), ("ebitda", "EBITDA"), ("ebit", "EBIT (operating profit)"), ("interest_expense", "Finance costs"),
            ("net_income", "PAT (net profit)"), ("total_assets", "Total assets"), ("current_liabilities", "Current liabilities"),
            ("total_equity", "Shareholders' equity"), ("total_debt", "Borrowings"), ("cash", "Cash and equivalents"),
            ("cfo", "Cash from operations (CFO)"), ("capex", "Capital expenditure (cash spent)")]

_BASIS_NOTE = {"consolidated": "Consolidated statements.", "standalone": "Standalone statements.",
               "unspecified": "The data provider does not say whether these statements are consolidated or standalone; check the annual report."}

_READING = {
    "Information Technology Services": "IT services: an asset-light business. Margins, cash conversion and ROE matter most; book value says little.",
    "Household & Personal Products": "Consumer goods: look at margins, ROCE, working capital and how steady growth is.",
    "Steel": "Steel: cyclical and capital-heavy. Look at capex, borrowings and interest coverage, and judge profits across the cycle.",
    "Banks - Regional": "Bank: borrowing is its raw material, so debt to equity, the current ratio and EV/EBITDA do not apply. Use NIM, asset quality, capital adequacy, ROA and P/B.",
    "Oil & Gas Refining & Marketing": "Conglomerate: several businesses with different economics. Use consolidated figures and read the segment mix, capex and debt.",
}


def _val(fd, key: str, period) -> float | None:
    s = fd.get(key)
    v = s.get(period) if period in s.index else None
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def case_study(symbol: str) -> dict | None:
    from ...analytics import ratios as R
    from ...data import repository as repo
    from ...data.official import official_links
    company = repo.get_company(symbol)
    if not company:
        return None
    base = {"symbol": symbol, "name": company.get("name") or symbol, "industry": company.get("industry"), "sector": company.get("sector"),
            "sample": bool(company.get("is_sample")), "links": {k: v for k, v in official_links(symbol).items()
                                                                   if k in ("NSE annual reports", "NSE financial results", "NSE quote page", "BSE results")}}
    fd = repo.get_financials(symbol, auto_refresh=False)
    if fd.empty:
        return {**base, "available": False,
                "note": "EquityPilot has no stored statements for this company yet. Open its company page to fetch them, then come back."}
    last = fd.periods[-1]
    prev = fd.periods[-2] if len(fd.periods) > 1 else None
    val = lambda k, p=last: _val(fd, k, p)                     # noqa: E731
    financial = R.is_financial(company)
    def shown(k, p):                                          # providers store capex as a negative cash flow
        v = val(k, p) if p is not None else None
        return abs(v) if k == "capex" and v is not None else v
    figures = [{"key": k, "label": label, "value": shown(k, last), "previous": shown(k, prev)}
               for k, label in _FIGURES if val(k) is not None and not (financial and k in ("ebitda", "current_liabilities"))]
    ratios: list[dict] = []

    def add(key, name, value, formula, steps, kind="pct"):
        if value is not None and math.isfinite(value):
            ratios.append({"key": key, "name": name, "value": value, "kind": kind, "formula": formula, "steps": steps})

    rev, ni, ebit, ebitda = val("revenue"), val("net_income"), val("ebit"), val("ebitda")
    if rev and ni is not None and not financial:          # bank "revenue" is defined differently by data providers
        add("net_margin", "Net margin", ni / rev, "PAT ÷ Revenue", f"{F.crore(ni)} ÷ {F.crore(rev)} = {F.pct(ni / rev)}")
    if rev and ebitda is not None and not financial:
        add("ebitda_margin", "EBITDA margin", ebitda / rev, "EBITDA ÷ Revenue", f"{F.crore(ebitda)} ÷ {F.crore(rev)} = {F.pct(ebitda / rev)}")
    eq, eq0 = val("total_equity"), val("total_equity", prev) if prev is not None else None
    if ni is not None and eq and eq0:
        avg = (eq + eq0) / 2
        add("roe", "ROE", ni / avg, "PAT ÷ Average shareholders' equity",
            f"{F.crore(ni)} ÷ (({F.crore(eq0)} + {F.crore(eq)}) ÷ 2 = {F.crore(avg)}) = {F.pct(ni / avg)}")
    ta, cl = val("total_assets"), val("current_liabilities")
    ta0 = val("total_assets", prev) if prev is not None else None
    cl0 = val("current_liabilities", prev) if prev is not None else None
    if not financial and ebit is not None and ta and cl is not None and ta0 and cl0 is not None:
        ce, ce0 = ta - cl, ta0 - cl0
        avg = (ce + ce0) / 2
        add("roce", "ROCE", ebit / avg, "EBIT ÷ Average capital employed (Total assets − Current liabilities)",
            f"{F.crore(ebit)} ÷ (({F.crore(ce0)} + {F.crore(ce)}) ÷ 2 = {F.crore(avg)}) = {F.pct(ebit / avg)}")
    if ni is not None and ta and ta0:
        avg = (ta + ta0) / 2
        add("roa", "ROA", ni / avg, "PAT ÷ Average total assets", f"{F.crore(ni)} ÷ {F.crore(avg)} = {F.pct(ni / avg, 2)}")
    debt = val("total_debt")
    if not financial and debt is not None and eq:
        add("debt_to_equity", "Debt to equity", debt / eq, "Borrowings ÷ Shareholders' equity", f"{F.crore(debt)} ÷ {F.crore(eq)} = {F.mult(debt / eq, 2)}", "mult")
    interest = val("interest_expense")
    if not financial and ebit is not None and interest:
        add("interest_coverage", "Interest coverage", ebit / abs(interest), "EBIT ÷ Finance costs",
            f"{F.crore(ebit)} ÷ {F.crore(abs(interest))} = {F.mult(ebit / abs(interest))}", "mult")
    cfo, capex = val("cfo"), val("capex")
    if not financial and cfo is not None and ni:
        add("cash_conversion", "Cash conversion", cfo / ni, "CFO ÷ PAT", f"{F.crore(cfo)} ÷ {F.crore(ni)} = {F.mult(cfo / ni, 2)}", "mult")
    if not financial and cfo is not None and capex is not None:
        fcf = cfo - abs(capex)
        add("fcf", "Free cash flow", fcf, "CFO − Capex", f"{F.crore(cfo)} − {F.crore(abs(capex))} = {F.crore(fcf)}", "inr")
    notes = []
    if financial:
        notes.append("Bank or financial company: EBITDA, ROCE, debt to equity, interest coverage, the current ratio and cash-flow-based "
                     "measures are not meaningful and are left out, and net margin is skipped because providers define bank revenue differently. See the Bank metrics tab on the company page.")
    reading = _READING.get(company.get("industry") or "")
    return {**base, "available": True, "financial": financial,
            "period": F.fiscal_label(last), "period_end": str(last.date()) if hasattr(last, "date") else str(last),
            "previous_period": F.fiscal_label(prev) if prev is not None else None,
            "basis": fd.basis, "basis_note": _BASIS_NOTE.get(fd.basis, _BASIS_NOTE["unspecified"]),
            "source": ", ".join(fd.sources) or "Unknown", "source_urls": fd.source_urls, "data_types": fd.data_types,
            "fetched_at": F.ist(fd.fetched_at) if fd.fetched_at is not None else None, "currency": fd.currency,
            "figures": figures, "ratios": ratios, "notes": notes, "reading": reading,
            "labels": {"facts": "Reported figures from the source named above (third-party data unless stated otherwise).",
                       "calculations": "Ratios calculated by EquityPilot from those figures, with every input shown.",
                       "interpretation": "Reading notes are general educational guidance for this type of business, not a view on the shares."}}
