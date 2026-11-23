"""Offline research analyst (free, no API).

A deterministic, rule-based assistant that answers from the grounded context only. It separates
FACTS (with source IDs), CALCULATIONS (with formulas), ASSUMPTIONS, an AUTOMATED INTERPRETATION
(rule-based, clearly labelled) and LIMITATIONS. It never issues buy/sell recommendations.
"""
from __future__ import annotations

import re

import pandas as pd

from .. import config
from .. import formatting as F
from ..analytics import ratios as R
from ..analytics import risk as K
from ..content.glossary import GLOSSARY, find_term
from .context import ResearchContext

INTENTS = [
    ("recommendation", r"\b(buy|sell|hold|should i (buy|invest|sell)|worth (buying|investing)|target price|multibagger|good (stock|investment)|invest in)\b"),
    ("document", r"\b(annual report|document|pdf|presentation|transcript|summari[sz]e the (report|document|filing))\b"),
    ("concept", r"\b(what is|what's|what are|explain|define|definition|meaning of|how (is|do you|to) calculate|formula)\b"),
    ("valuation", r"\b(valuation|value|valued|p/?e|p/?b|ev/?ebitda|dcf|intrinsic|expensive|cheap|multiple|overvalued|undervalued)\b"),
    ("debt", r"\b(debt|leverage|borrow|solvency|interest coverage|gearing|balance sheet|financial (health|strength)|strong)\b"),
    ("liquidity", r"\b(liquidity|current ratio|quick ratio|working capital|balance sheet|financial (health|strength))\b"),
    ("cashflow", r"\b(cash ?flow|fcf|cfo|capex|cash conversion)\b"),
    ("profitability", r"\b(profits?|margins?|ebitda|roe|roce|return on|profitab\w*|earnings|eps)\b"),
    ("growth", r"\b(growth|grow|grows|grew|grown|growing|revenues?|sales|cagr|top ?line)\b"),
    ("risk", r"\b(risk|risks|red flag|concern|weakness|pledge|volatil)\b"),
    ("ownership", r"\b(shareholding|promoter|fii|dii|ownership|holding pattern)\b"),
    ("segments", r"\b(segment|business mix|division|geograph)\b"),
    ("news", r"\b(news|announcement|disclosure|headline|recent)\b"),
    ("overview", r"\b(overview|summary|summari[sz]e|tell me about|about the company|snapshot|business model)\b"),
    ("quarterly", r"\b(quarter|quarters|quarterly|q[1-4]|latest results|recent results|last results|results)\b"),
    ("plain", r"\b(simple (english|words|terms|language)|plain (english|language|words)|layman'?s?|beginners?|eli5|explain like|"
              r"for a (beginner|newbie|child|student)|in simple|easy (words|language)|non-?expert)\b"),
]


def detect_intents(q: str) -> list[str]:
    ql = q.lower()
    found = [name for name, pat in INTENTS if re.search(pat, ql)]
    if "quarterly" in found and re.search(r"\b(annual|yearly|full[- ]year)\b", ql):
        found.remove("quarterly")
    return found or ["overview"]


# A specific metric named in the question -> a direct answer with its latest value. Most specific patterns first.
METRIC_ALIASES: list[tuple[str, str]] = [
    (r"\bnet debt\s*(to|/)\s*ebitda\b", "net_debt_to_ebitda"),
    (r"\bdebt[- ]?(to[- ]?)?equity\b|\bd/e\b|\bgearing\b|\bleverage ratio\b", "debt_to_equity"),
    (r"\binterest coverage\b", "interest_coverage"),
    (r"\bcurrent ratio\b", "current_ratio"),
    (r"\bquick ratio\b|\bacid[- ]test\b", "quick_ratio"),
    (r"\broce\b|\breturn on capital( employed)?\b", "roce"),
    (r"\broe\b|\breturn on (shareholders'? )?equity\b", "roe"),
    (r"\broa\b|\breturn on assets\b", "roa"),
    (r"\bebitda margins?\b|\boperating (profit )?margins?\b", "ebitda_margin"),
    (r"\bebit margins?\b", "ebit_margin"),
    (r"\bgross margins?\b", "gross_margin"),
    (r"\b(net (profit )?|profit )margins?\b", "net_margin"),
    (r"\beps growth\b", "eps_growth"),
    (r"\b(revenue|sales|top ?line) growth\b|\bgrowth (in|of) (revenue|sales)\b", "revenue_growth"),
    (r"\b((net )?profit|earnings|bottom ?line) growth\b|\bgrowth (in|of) (net )?profits?\b", "net_income_growth"),
    (r"\beps\b|\bearnings per share\b", "eps"),
    (r"\bbook value( per share)?\b|\bbvps\b", "bvps"),
    (r"\bcfo\s*(to|/)\s*(net )?profit\b|\bcash conversion\b", "cfo_to_net_income"),
    (r"\bfcf margin\b|\bfree cash flow margin\b", "fcf_margin"),
    (r"\bdividend payout\b|\bpayout ratio\b", "dividend_payout"),
    (r"\basset turnover\b", "asset_turnover"),
    (r"\b(receivable|debtor)s? days\b", "receivable_days"),
    (r"\binventory days\b", "inventory_days"),
    (r"\bev\s*/\s*ebitda\b|\bev to ebitda\b", "ev_ebitda"),
    (r"\bp\s*/\s*e\b|\bpe ratio\b|\bprice[- ]to[- ]earnings\b|\bpe multiple\b", "pe"),
    (r"\bp\s*/\s*b\b|\bpb ratio\b|\bprice[- ]to[- ]book\b", "pb"),
    (r"\bdividend yield\b", "dividend_yield"),
    (r"\bmarket (cap|capitali[sz]ation|value)\b|\bm-?cap\b", "market_cap"),
]
SNAP_LABELS = {"pe": "P/E", "pb": "P/B", "ev_ebitda": "EV/EBITDA", "dividend_yield": "Dividend yield", "market_cap": "Market capitalisation"}
LENDER_BLIND = {"debt_to_equity", "net_debt_to_ebitda", "interest_coverage", "current_ratio", "quick_ratio", "ev_ebitda"}
# What a value means, in everyday words. {n} is the number exactly as displayed, so it can be traced to the data.
PLAIN_MEANING = {
    "debt_to_equity": "For every ₹1 of shareholders' money, the company has borrowed about ₹{n}.",
    "net_debt_to_ebitda": "It would take about {n} years of operating profit (EBITDA) to repay its borrowings after using its cash "
                          "(a negative figure means it holds more cash than debt).",
    "interest_coverage": "Its operating profit covers the yearly interest bill about {n} times.",
    "current_ratio": "It has about ₹{n} of short-term assets for every ₹1 it has to pay within a year.",
    "quick_ratio": "Leaving out stock (inventory), it has about ₹{n} of short-term assets for every ₹1 due within a year.",
    "roe": "For every ₹100 of shareholders' money, the company earned about ₹{n} of profit in the year.",
    "roce": "For every ₹100 of capital used in the business (shareholders' money plus borrowings), it earned about ₹{n} of operating profit.",
    "roa": "For every ₹100 of assets, it earned about ₹{n} of profit.",
    "net_margin": "From every ₹100 of sales, the company kept about ₹{n} as profit.",
    "ebitda_margin": "From every ₹100 of sales, about ₹{n} was left as operating profit before depreciation, interest and tax.",
    "ebit_margin": "From every ₹100 of sales, about ₹{n} was left as operating profit after depreciation.",
    "gross_margin": "From every ₹100 of sales, about ₹{n} was left after the direct cost of what was sold.",
    "revenue_growth": "Sales changed by {n}% compared with the previous year.",
    "net_income_growth": "Profit changed by {n}% compared with the previous year.",
    "eps_growth": "Profit per share changed by {n}% compared with the previous year.",
    "eps": "The company earned ₹{n} of profit for each share.",
    "bvps": "The net worth shown in the accounts works out to ₹{n} per share.",
    "cfo_to_net_income": "For every ₹1 of reported profit, the business brought in about ₹{n} of cash from operations.",
    "fcf_margin": "From every ₹100 of sales, about ₹{n} was left as free cash after spending on assets.",
    "dividend_payout": "It paid out about {n}% of its profit as dividends.",
    "asset_turnover": "Every ₹1 of assets produced about ₹{n} of sales in the year.",
    "receivable_days": "Customers took about {n} days on average to pay.",
    "inventory_days": "Goods sat in stock for about {n} days on average before being sold.",
    "pe": "Investors are paying about ₹{n} for every ₹1 of the company's yearly profit.",
    "pb": "The market values the company at about {n} times the net worth shown in its accounts.",
    "ev_ebitda": "The whole business (shares plus borrowings minus cash) is valued at about {n} times its yearly operating profit.",
    "dividend_yield": "At the current price, last year's dividends equal about {n}% of the share price.",
}


def asked_metric(q: str) -> str | None:
    ql = q.lower()
    for pat, key in METRIC_ALIASES:
        if re.search(pat, ql):
            return key
    return None


def _shown_number(text: str) -> str:
    """'48.7%' -> '48.7', '0.4x' -> '0.4', '45 days' -> '45' (the number as displayed, for plain-English sentences)."""
    m = re.search(r"-?[\d,]+(\.\d+)?", text or "")
    return m.group(0) if m else text


def _sid(ctx: ResearchContext, startswith: str) -> str:
    for b in ctx.blocks:
        if b.title.startswith(startswith):
            return b.sid
    return "—"


class Answer:
    """Layout: a direct answer first, then verified facts, calculations, assumptions, the rule-based interpretation in
    plain English, limitations, and the sources and reporting periods used."""

    def __init__(self):
        self.direct, self.facts, self.calcs, self.assumptions, self.interp, self.limits = [], [], [], [], [], []
        self.periods: list[str] = []

    def lead(self, text: str) -> None:
        """Set the direct answer unless a more specific handler already did."""
        if not self.direct:
            self.direct.append(text)

    def md(self, title: str | None = None) -> str:
        parts = [f"**{title}**\n"] if title else []
        if self.direct:
            parts.append("**Answer**\n" + "\n".join(dict.fromkeys(self.direct)))
        sections = [("Facts from sources", self.facts), ("Calculations", self.calcs), ("Assumptions", self.assumptions),
                    ("Automated interpretation (rule-based, not advice)", self.interp),
                    ("Limitations and missing information", self.limits), ("Sources and periods", self.periods)]
        for name, items in sections:
            if items:
                parts.append(f"**{name}**\n" + "\n".join(f"- {i}" for i in dict.fromkeys(items)))
        return "\n\n".join(parts)


money = F.money   # ₹2,25,458 Cr for INR; "USD 1,234 mn" otherwise


def _series_text(rt: pd.DataFrame, key: str) -> str:
    d = R.RATIOS[key]
    return ", ".join(f"{F.fiscal_label(p)} {F.by_kind(rt.at[key, p], d.kind)}" for p in rt.columns)


def _trend(rt: pd.DataFrame, key: str) -> float | None:
    s = rt.loc[key].dropna() if key in rt.index else pd.Series(dtype=float)
    return float(s.iloc[-1] - s.iloc[0]) if len(s) >= 2 else None


def _growth(ctx, a: Answer):
    fd, rt = ctx.data.get("fd"), ctx.data.get("ratios")
    s_fin, s_rat = _sid(ctx, "Annual financial"), _sid(ctx, "Financial ratios")
    if fd is None or fd.empty:
        a.limits.append("No financial statements are available for this company.")
        return
    rev = fd.get("revenue")
    a.facts.append("Revenue by year: " + ", ".join(f"{F.fiscal_label(p)} {money(v, fd.currency)}" for p, v in rev.items())
                   + f" [{s_fin}]")
    a.calcs.append(f"Revenue growth (YoY): {_series_text(rt, 'revenue_growth')} [{s_rat}]")
    c3 = R.cagr(rev, 3)
    a.calcs.append(f"3-year revenue CAGR = (latest / 3 years earlier)^(1/3) - 1 = {F.pct(c3)} [{s_rat}]")
    a.calcs.append(f"Net profit growth (YoY): {_series_text(rt, 'net_income_growth')} [{s_rat}]")
    g = rt.loc["revenue_growth"].dropna()
    if len(g):
        last = g.iloc[-1]
        a.lead(f"Revenue changed by {F.pct(last)} in {F.fiscal_label(g.index[-1])} to {money(fd.latest('revenue'), fd.currency)}; "
               f"over the last 3 years it grew at {F.pct(c3)} a year (CAGR) [{s_rat}].")
        a.interp.append(f"Latest revenue growth of {F.pct(last)} is {'above' if c3 is not None and last > c3 else 'below'} the "
                        f"3-year CAGR of {F.pct(c3)}, i.e. growth is {'accelerating' if c3 is not None and last > c3 else 'slowing'} versus the recent trend.")
        jumps = [(p_, v) for p_, v in g.items() if v > 0.5 or v < -0.4]
        if jumps:
            p_, v = jumps[-1]
            a.interp.append(f"The {F.pct(v)} change in {F.fiscal_label(p_)} is unusually large. Changes of this size usually come from a "
                            "merger, acquisition, demerger or an accounting change rather than ordinary growth, and they also lift or "
                            "lower the 3-year CAGR - check the annual report before reading it as a trend.")
    ni_g = rt.loc["net_income_growth"].dropna()
    if len(g) and len(ni_g):
        a.interp.append("Profit grew faster than revenue in the latest year (operating leverage / margin expansion)."
                        if ni_g.iloc[-1] > g.iloc[-1] else "Profit grew slower than revenue in the latest year (margin pressure).")


def _profitability(ctx, a: Answer):
    rt = ctx.data.get("ratios")
    s_rat = _sid(ctx, "Financial ratios")
    if rt is None or rt.empty:
        a.limits.append("Ratios cannot be calculated without financial statements.")
        return
    nm, em = rt.loc["net_margin"].dropna(), rt.loc["ebitda_margin"].dropna()
    if len(nm):
        a.lead(f"In {F.fiscal_label(nm.index[-1])} the net profit margin was {F.pct(nm.iloc[-1])}"
               + (f" and the EBITDA (operating) margin {F.pct(em.iloc[-1])}" if len(em) else "") + f" [{s_rat}].")
    for k in ("ebitda_margin", "net_margin", "roe", "roce"):
        a.calcs.append(f"{R.RATIOS[k].label} = {R.RATIOS[k].formula}: {_series_text(rt, k)} [{s_rat}]")
    roe = rt.loc["roe"].dropna()
    if len(roe):
        v = roe.iloc[-1]
        a.interp.append(f"Latest ROE of {F.pct(v)} is " + ("above a typical Indian cost of equity (~12-14%), consistent with value creation."
                                                          if v > 0.14 else "within or below a typical cost of equity (~12-14%) - returns barely cover the cost of capital."
                                                          if v > 0 else "negative - the company lost money for shareholders."))
    t = _trend(rt, "ebitda_margin")
    if t is not None:
        a.interp.append(f"EBITDA margin moved {t * 100:+.1f} percentage points over the period shown.")
    fd = ctx.data.get("fd")
    if fd is not None and not fd.empty:
        dp = R.dupont(fd)
        if not dp.empty:
            last = dp.iloc[:, -1]
            a.calcs.append(f"DuPont (latest): net margin {F.pct(last['Net margin'])} × asset turnover {F.mult(last['Asset turnover'], 2)} "
                           f"× equity multiplier {F.mult(last['Equity multiplier'], 2)} = ROE {F.pct(last['ROE (product)'])} [{s_rat}]")


def _debt(ctx, a: Answer):
    rt, company = ctx.data.get("ratios"), ctx.company
    s_rat, s_fin = _sid(ctx, "Financial ratios"), _sid(ctx, "Annual financial")
    if R.is_financial(company):
        a.facts.append(f"{company['name']} is a financial-sector company [{_sid(ctx, 'Sector note')}].")
        a.interp.append("For lenders, borrowings are raw material; strength is judged by capital adequacy (CRAR), "
                        "asset quality (GNPA/NNPA, provision coverage) and funding (CASA), not debt/equity.")
        s_bank = _sid(ctx, "Bank metrics")
        if s_bank == "—":
            a.limits.append("Bank metrics (GNPA, NNPA, CRAR, CASA, NIM) are not in the dataset - enter them from the bank's "
                            "quarterly disclosure on Company Research → Bank metrics.")
            return
        a.facts.append(next(b.text for b in ctx.blocks if b.sid == s_bank).replace("\n", "; ") + f" [{s_bank}]")
        for f in [f for f in ctx.data.get("risk_flags", []) if f["category"] in ("Asset quality", "Capital", "Funding & efficiency")]:
            if f["level"] in ("good", "warning", "serious", "critical"):
                a.interp.append(f"{f['title']}: {f['value']} → {K.LEVEL_LABEL[f['level']]} under EquityPilot screening bands "
                                f"({f['rule']}) [{_sid(ctx, 'Rule-based risk')}]")
        return
    if rt is None or rt.empty:
        a.limits.append("No statements available.")
        return
    fd = ctx.data["fd"]
    de = rt.loc["debt_to_equity"].dropna() if "debt_to_equity" in rt.index else pd.Series(dtype=float)
    if len(de):
        lvl = next((K.LEVEL_LABEL[f["level"]] for f in ctx.data.get("risk_flags", []) if f["category"] == "Debt"
                    and "equity" in f["title"].lower()), None)
        a.lead(f"Debt to equity was {F.mult(de.iloc[-1])} in {F.fiscal_label(de.index[-1])}"
               + (f" - {lvl} under EquityPilot's thresholds" if lvl else "") + f" [{s_rat}].")
    a.facts.append(f"Borrowings (latest): {money(fd.latest('total_debt'), fd.currency)}; cash & short-term investments: "
                   f"{money(fd.latest('cash'), fd.currency)} [{s_fin}]")
    for k in ("debt_to_equity", "net_debt_to_ebitda", "interest_coverage"):
        a.calcs.append(f"{R.RATIOS[k].label} = {R.RATIOS[k].formula}: {_series_text(rt, k)} [{s_rat}]")
    flags = [f for f in ctx.data.get("risk_flags", []) if f["category"] == "Debt"]
    for f in flags:
        a.interp.append(f"{f['title']}: {f['value']} → {K.LEVEL_LABEL[f['level']]} under EquityPilot thresholds ({f['rule']}) [{_sid(ctx, 'Rule-based risk')}]")


def _liquidity(ctx, a: Answer):
    rt = ctx.data.get("ratios")
    if rt is None or rt.empty or R.is_financial(ctx.company):
        a.limits.append("Liquidity ratios are unavailable or not meaningful for this company.")
        return
    s = _sid(ctx, "Financial ratios")
    for k in ("current_ratio", "quick_ratio", "receivable_days", "inventory_days"):
        a.calcs.append(f"{R.RATIOS[k].label} = {R.RATIOS[k].formula}: {_series_text(rt, k)} [{s}]")
    cr = rt.loc["current_ratio"].dropna()
    if len(cr):
        a.interp.append(f"Current ratio of {F.mult(cr.iloc[-1], 2)} " + ("indicates comfortable short-term liquidity." if cr.iloc[-1] >= 1.5
                        else "is adequate." if cr.iloc[-1] >= 1 else "is below 1x - check whether this is structural (e.g. supplier credit) or a sign of stress."))


def _cashflow(ctx, a: Answer):
    rt, fd = ctx.data.get("ratios"), ctx.data.get("fd")
    if rt is None or rt.empty:
        a.limits.append("No cash-flow data available.")
        return
    s_fin, s_rat = _sid(ctx, "Annual financial"), _sid(ctx, "Financial ratios")
    a.facts.append("Cash flow from operations: " + ", ".join(f"{F.fiscal_label(p)} {money(v, fd.currency)}" for p, v in fd.get("cfo").items()) + f" [{s_fin}]")
    a.facts.append("Capital expenditure: " + ", ".join(f"{F.fiscal_label(p)} {money(v, fd.currency)}" for p, v in fd.get("capex").items()) + f" [{s_fin}]")
    for k in ("cfo_to_net_income", "fcf_margin", "capex_to_revenue"):
        a.calcs.append(f"{R.RATIOS[k].label} = {R.RATIOS[k].formula}: {_series_text(rt, k)} [{s_rat}]")
    conv = rt.loc["cfo_to_net_income"].dropna().iloc[-3:]
    if len(conv):
        a.interp.append(f"Average cash conversion over the last {len(conv)} years is {conv.mean():.2f}x - "
                        + ("profits are well backed by cash." if conv.mean() >= 0.9 else "a meaningful share of reported profit is not converting to operating cash; check working capital and revenue recognition."))


def _valuation(ctx, a: Answer):
    snap, quote = ctx.data.get("snap") or {}, ctx.data.get("quote")
    s_mkt = _sid(ctx, "Market data")
    if not quote:
        a.limits.append("No market price available.")
        return
    a.lead(f"At {F.inr(quote.get('price'))} (as of {F.ist(quote.get('as_of') or quote.get('fetched_at'))}) the shares trade at a "
           f"P/E of {F.mult(snap.get('pe'))} and a P/B of {F.mult(snap.get('pb'))} [{s_mkt}].")
    a.facts.append(f"Price {F.inr(quote.get('price'))} as of {F.ist(quote.get('as_of') or quote.get('fetched_at'))} [{s_mkt}]")
    a.calcs.append(f"P/E = Market cap / Net profit = {F.mult(snap.get('pe'))} (earnings basis: {snap['basis'].get('earnings')}) [{s_mkt}]")
    a.calcs.append(f"P/B = Market cap / Equity = {F.mult(snap.get('pb'))}; EV/EBITDA = {F.mult(snap.get('ev_ebitda'))}; "
                   f"EV = {F.big_inr(snap.get('ev'))} [{s_mkt}]")
    if snap.get("currency_mismatch"):
        a.limits.append("Statements are in a different currency from the price, so multiples are not computed.")
    sv = _sid(ctx, "Saved DCF")
    if sv != "—":
        blk = next(b for b in ctx.blocks if b.sid == sv)
        a.assumptions.append(f"{blk.text} [{sv}]")
        a.interp.append("The DCF value reflects the user's assumptions; small changes in WACC or terminal growth change it materially - see the sensitivity table on the Valuation page.")
    else:
        a.limits.append("No DCF has been saved for this company - build one on the Valuation page to include intrinsic-value assumptions.")
    pe = snap.get("pe")
    if pe:
        a.interp.append("A P/E is only meaningful relative to the company's own history, its growth and close peers - see 'Valuation history' and 'Relative to peers' on the Valuation page.")


def _risk(ctx, a: Answer):
    flags = ctx.data.get("risk_flags") or []
    s = _sid(ctx, "Rule-based risk")
    high = [f for f in flags if f["level"] in ("serious", "critical")]
    mod = [f for f in flags if f["level"] == "warning"]
    for f in high:
        a.facts.append(f"{f['category']} - {f['title']}: {f['value']} ({K.LEVEL_LABEL[f['level']]}; thresholds {f['rule']}) [{s}]")
    for f in mod:
        a.facts.append(f"{f['category']} - {f['title']}: {f['value']} (MODERATE) [{s}]")
    if high or mod:
        top = (high + mod)[:2]
        a.lead(f"{len(high)} check(s) are at elevated or high risk and {len(mod)} at moderate risk. The most important: "
               + "; ".join(f"{f['title'].lower()} {f['value']}" for f in top) + f" [{s}].")
    elif flags:
        a.lead(f"None of EquityPilot's {len(flags)} quantitative risk checks is at a moderate or higher level [{s}].")
    score = K.overall_score(flags)
    if score is not None:
        a.calcs.append(f"Composite risk score = average of check levels (Low 0, Moderate 33, Elevated 67, High 100) = {score:.0f}/100 [{s}]")
    if not high and not mod:
        a.interp.append("None of the quantitative checks are at moderate or higher risk levels.")
    else:
        a.interp.append(f"{len(high)} check(s) at elevated/high and {len(mod)} at moderate risk; prioritise these in your review.")
    rn = _sid(ctx, "Analyst's risk notes")
    if rn != "—":
        a.facts.append(f"Your recorded risk notes are included [{rn}].")
    a.limits.append("Qualitative risks (litigation, governance, regulatory actions) need reading of the annual report and exchange disclosures.")


def _ownership(ctx, a: Answer):
    s = _sid(ctx, "Shareholding")
    if s == "—":
        a.limits.append("No shareholding pattern stored - enter it from the latest exchange filing (Company Research → Shareholding).")
        return
    blk = next(b for b in ctx.blocks if b.sid == s)
    a.facts.append(f"{blk.title}: {blk.text} [{s}]")


def _segments(ctx, a: Answer):
    s = _sid(ctx, "Revenue segments")
    if s == "—":
        a.limits.append("No segment data stored - enter it from the segment note of the annual report.")
        return
    a.facts.append(next(b.text for b in ctx.blocks if b.sid == s) + f" [{s}]")


def _news(ctx, a: Answer):
    s = _sid(ctx, "Recent headlines")
    if s == "—":
        a.limits.append("No headlines or disclosures stored - fetch them on the News & Disclosures page.")
        return
    a.facts.append("Recent items (titles only - open the links on the News page for full text) [" + s + "]:\n  " +
                   next(b.text for b in ctx.blocks if b.sid == s).replace("\n", "\n  "))
    a.limits.append("Only headlines are stored; EquityPilot does not summarise article bodies it has not retrieved.")


def _quarterly(ctx, a: Answer):
    fq = ctx.data.get("fq")
    s_q, s_f = _sid(ctx, "Quarterly results"), _sid(ctx, "Exchange filings about results")
    if fq is None or fq.empty or s_q == "—":
        a.limits.append("No quarterly statements are stored for this company. The official results are in its quarterly results "
                        "filing on NSE/BSE.")
        return
    qs = R.quarterly_summary(fq)
    last, p = qs.iloc[-1], qs.index[-1]
    label = pd.Timestamp(p).strftime("%b %Y")
    cur = fq.currency
    def changes(yoy, qoq) -> str:
        parts = (([f"{F.pct(yoy, 1, True)} versus the same quarter last year"] if pd.notna(yoy) else [])
                 + ([f"{F.pct(qoq, 1, True)} versus the previous quarter"] if pd.notna(qoq) else []))
        return f" ({', '.join(parts)})" if parts else ""
    a.lead(f"In the quarter ended {label}, revenue was {money(last['revenue'], cur)}{changes(last['revenue_yoy'], last['revenue_qoq'])} "
           f"and net profit was {money(last['net_income'], cur)}{changes(last['net_income_yoy'], last['net_income_qoq'])} [{s_q}].")
    if pd.isna(last["revenue_yoy"]):
        a.limits.append("The same quarter of last year is not in the stored quarterly data, so year-on-year changes cannot be "
                        "calculated here; the results filing shows them.")
    a.facts.append(f"EBITDA margin {F.pct(last['ebitda_margin'])}"
                   + (f" (same quarter last year {F.pct(last['ebitda_margin_ly'])})" if pd.notna(last['ebitda_margin_ly']) else "")
                   + f"; net margin {F.pct(last['net_margin'])}; diluted EPS {F.num(last['eps'])} [{s_q}]")
    if len(qs) >= 2:
        prev = qs.iloc[-2]
        a.facts.append(f"Previous quarter ({pd.Timestamp(qs.index[-2]).strftime('%b %Y')}): revenue {money(prev['revenue'], cur)}, "
                       f"net profit {money(prev['net_income'], cur)} [{s_q}]")
    if s_f != "—":
        filing = next(b.text for b in ctx.blocks if b.sid == s_f).split("\n")[0]
        a.facts.append(f"{filing} [{s_f}]")
    ry, ny = last["revenue_yoy"], last["net_income_yoy"]
    if pd.notna(ry) and pd.notna(ny):
        a.interp.append("Profit grew faster than sales over the year - margins widened." if ny > ry else
                        "Profit grew more slowly than sales over the year (or fell) - margins narrowed.")
    em, em_ly = last["ebitda_margin"], last["ebitda_margin_ly"]
    if pd.notna(em) and pd.notna(em_ly):
        a.interp.append(f"The operating (EBITDA) margin {'improved' if em > em_ly else 'declined'} versus the same quarter a year "
                        "earlier, which compares like with like for seasonal businesses.")
    a.limits.append("Quarterly figures come from the data provider and can lag or differ from the company's filing; the official "
                    "numbers, segment details and management commentary are in the results filing on NSE/BSE.")


def _first_sentence(text: str | None, limit: int = 260) -> str | None:
    if not text:
        return None
    m = re.match(r"(.+?[.!?])(\s|$)", text.strip())
    out = (m.group(1) if m else text.strip())
    return out if len(out) <= limit else out[:limit].rsplit(" ", 1)[0] + "…"


def _plain(ctx, a: Answer):
    """A short explanation in everyday words, every figure taken from the sources."""
    c = ctx.company
    s0, s_m, s_f, s_r = _sid(ctx, "Company profile"), _sid(ctx, "Market data"), _sid(ctx, "Annual financial"), _sid(ctx, "Financial ratios")
    fd, rt, snap = ctx.data.get("fd"), ctx.data.get("ratios"), ctx.data.get("snap") or {}
    what = _first_sentence(c.get("description"))
    lines = [f"**{c['name']}** - {what} [{s0}]" if what else f"**{c['name']}** is listed in {c.get('sector') or 'n/a'} / "
             f"{c.get('industry') or 'n/a'} [{s0}]."]
    if snap.get("market_cap"):
        lines.append(f"The stock market values the whole company at about {F.big_inr(snap['market_cap']).replace(' L Cr', ' lakh crore')} [{s_m}].")
    if fd is not None and not fd.empty and rt is not None and not rt.empty:
        p = fd.periods[-1]
        lines.append(f"In {F.fiscal_label(p)} it sold goods and services worth {money(fd.latest('revenue'), fd.currency)} and kept "
                     f"{money(fd.latest('net_income'), fd.currency)} as profit [{s_f}].")
        g = rt.loc["revenue_growth"].dropna()
        if len(g):
            lines.append(f"Sales changed by {F.pct(g.iloc[-1])} compared with the year before [{s_r}].")
        nm = rt.loc["net_margin"].dropna()
        if len(nm):
            lines.append(PLAIN_MEANING["net_margin"].format(n=_shown_number(F.pct(nm.iloc[-1]))) + f" [{s_r}]")
        roe = rt.loc["roe"].dropna()
        if len(roe):
            lines.append(PLAIN_MEANING["roe"].format(n=_shown_number(F.pct(roe.iloc[-1]))) + f" [{s_r}]")
        if not R.is_financial(c):
            de = rt.loc["debt_to_equity"].dropna()
            if len(de):
                lines.append(PLAIN_MEANING["debt_to_equity"].format(n=_shown_number(F.mult(de.iloc[-1]))) + f" [{s_r}]")
        else:
            lines.append("As a lender, it borrows and lends money as its business, so its debt is judged differently - by capital "
                         f"adequacy and loan quality [{_sid(ctx, 'Sector note')}].")
    if snap.get("pe"):
        lines.append(PLAIN_MEANING["pe"].format(n=_shown_number(F.mult(snap['pe']))) + f" [{s_m}]")
    a.direct.extend(lines)
    a.interp.append("A high return on shareholders' money (above about 15%) with low borrowing usually signals a strong business; "
                    "a high P/E means investors expect strong future growth, which raises the risk if growth disappoints.")
    a.limits.append("This is a simplified summary of the latest figures. Read the annual report for the business segments, risks "
                    "and management's own explanation.")


def _metric_direct(ctx, a: Answer, key: str) -> bool:
    """Direct answer for a question about one named metric: its latest value, the period, the formula and what it means."""
    c, name = ctx.company, ctx.company["name"]
    if key in LENDER_BLIND and R.is_financial(c):
        label = R.RATIOS[key].label if key in R.RATIOS else SNAP_LABELS.get(key, key)
        a.direct.append(f"{label} is not a meaningful measure for {name}: lenders borrow and lend money as their business. Their "
                        "strength is judged by capital adequacy (CRAR), asset quality (gross and net NPA) and funding (CASA) "
                        f"[{_sid(ctx, 'Sector note')}].")
        return True
    if key in SNAP_LABELS:
        snap, s = ctx.data.get("snap") or {}, _sid(ctx, "Market data")
        v = snap.get(key)
        if v is None or s == "—":
            a.direct.append(f"{SNAP_LABELS[key]} is not available for {name} (it needs a current price and positive earnings or "
                            "book value in the statements).")
            return True
        shown = F.big_inr(v) if key == "market_cap" else F.pct(v) if key == "dividend_yield" else F.mult(v)
        basis = snap.get("basis", {}).get("earnings") if key == "pe" else None
        a.direct.append(f"**{name}: {SNAP_LABELS[key]} {shown}**" + (f" (earnings basis: {basis})" if basis else "") + f" [{s}].")
    else:
        rt, s = ctx.data.get("ratios"), _sid(ctx, "Financial ratios")
        if rt is None or rt.empty or key not in rt.index or not rt.loc[key].notna().any():
            a.direct.append(f"{R.RATIOS[key].label} cannot be calculated for {name} from the stored statements (an input is missing).")
            return True
        series = rt.loc[key].dropna()
        d = R.RATIOS[key]
        shown = F.by_kind(series.iloc[-1], d.kind)
        a.direct.append(f"**{name}: {d.label} {shown} in {F.fiscal_label(series.index[-1])}** ({d.formula}) [{s}].")
        if len(series) >= 2:
            a.facts.append(f"{d.label} by year: " + ", ".join(f"{F.fiscal_label(p_)} {F.by_kind(v_, d.kind)}" for p_, v_ in series.items())
                           + f" [{s}]")
    meaning = PLAIN_MEANING.get(key)
    if meaning:
        a.interp.insert(0, "In simple terms: " + meaning.format(n=_shown_number(shown)))
    return True


def _periods(ctx, a: Answer):
    """Where every figure came from and which period it covers."""
    fd, fq, quote = ctx.data.get("fd"), ctx.data.get("fq"), ctx.data.get("quote")
    if fd is not None and not fd.empty:
        basis = fd.basis if fd.basis not in ("unspecified", "—") else "consolidated/standalone basis not stated by the provider"
        a.periods.append(f"Annual statements: {', '.join(fd.sources) or 'n/a'}; {F.fiscal_label(fd.periods[0])} to "
                         f"{F.fiscal_label(fd.periods[-1])} (Indian fiscal years end in March); {basis}; amounts in "
                         f"{'₹ crore' if fd.currency == 'INR' else fd.currency + ' million'}; retrieved {F.ist(fd.fetched_at)}.")
    if fq is not None and not fq.empty and _sid(ctx, "Quarterly results") != "—":
        a.periods.append(f"Quarterly statements: latest quarter ended {pd.Timestamp(fq.periods[-1]).strftime('%b %Y')}.")
    if quote:
        label = config.DATA_TYPES.get(quote.get("data_type") or "", (quote.get("data_type") or "delayed",))[0]
        a.periods.append(f"Price: {F.inr(quote.get('price'))} ({label}) as of {F.ist(quote.get('as_of') or quote.get('fetched_at'))}, "
                         f"{quote.get('source') or 'source n/a'}; valuation multiples calculated by EquityPilot from this price.")
    if ctx.data.get("ratios") is not None:
        a.periods.append("Ratios and growth rates: calculated by EquityPilot from the statements above (formulas shown).")


def _overview(ctx, a: Answer):
    c, s0 = ctx.company, _sid(ctx, "Company profile")
    fd, rt = ctx.data.get("fd"), ctx.data.get("ratios")
    if fd is not None and not fd.empty and rt is not None and not rt.empty:
        roe = rt.loc["roe"].dropna()
        a.lead(f"{c['name']} ({c.get('sector') or 'sector n/a'}) reported revenue of {money(fd.latest('revenue'), fd.currency)} and "
               f"net profit of {money(fd.latest('net_income'), fd.currency)} in {F.fiscal_label(fd.periods[-1])}"
               + (f", with a return on equity of {F.pct(roe.iloc[-1])}" if len(roe) else "") + f" [{_sid(ctx, 'Annual financial')}].")
    a.facts.append(f"{c['name']} - {c.get('sector') or 'sector n/a'} / {c.get('industry') or 'industry n/a'} [{s0}]")
    if c.get("description"):
        first = _first_sentence(c["description"], 320) or ""
        rest = c["description"][len(first):].strip()
        second = _first_sentence(rest, 200) if rest and len(first) < 200 else None
        a.facts.append(f"Business: {first}{(' ' + second) if second else ''} [{s0}]")
    notes = _sid(ctx, "Analyst's own research notes")
    if notes != "—":
        a.facts.append(f"Your business-model notes are on record [{notes}].")
    _growth(ctx, a)
    _profitability(ctx, a)
    if not R.is_financial(ctx.company):
        _debt(ctx, a)
    _valuation(ctx, a)


def _concept(ctx, a: Answer, q: str) -> bool:
    term = find_term(q)
    if not term:
        return False
    e = GLOSSARY[term]
    a.facts.append(f"**{term}** - {e['definition']}")
    if e.get("formula") and e["formula"] != "—":
        a.calcs.append(f"Formula: {e['formula']}")
    a.interp.append(e["interpretation"])
    rt, key = ctx.data.get("ratios") if ctx else None, e.get("ratio")
    if ctx and key in R.RATIOS and rt is not None and key in rt.index:
        a.calcs.append(f"{ctx.company['name']}: {_series_text(rt, key)} [{_sid(ctx, 'Financial ratios')}]")
    elif ctx and key in ("pe", "pb", "ev_ebitda"):
        snap = ctx.data.get("snap") or {}
        a.calcs.append(f"{ctx.company['name']} current {term}: {F.mult(snap.get(key))} [{_sid(ctx, 'Market data')}]")
    return True


SUMMARY_TERMS = {"revenue": 3, "profit": 3, "growth": 2, "margin": 2, "guidance": 3, "outlook": 3, "expect": 2,
                 "capex": 2, "capacity": 2, "dividend": 2, "debt": 2, "risk": 2, "order book": 3, "demand": 2,
                 "segment": 1, "strategy": 2, "ebitda": 2, "crore": 1, "%": 1}


def summarise_document(pages: list[dict], n: int = 10) -> list[tuple[int, str]]:
    """Extractive summary: highest-scoring sentences (financial keywords + figures), with page numbers."""
    cands = []
    for p in pages:
        for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", p["text"])):
            if not 60 <= len(s) <= 400:
                continue
            low = s.lower()
            score = sum(w for t, w in SUMMARY_TERMS.items() if t in low) + (1.5 if re.search(r"\d", s) else 0)
            if score >= 4:
                cands.append((score, p["page"], s.strip()))
    cands.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for _, page, s in cands:
        key = s[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append((page, s))
        if len(out) >= n:
            break
    return sorted(out)


def _document(ctx, a: Answer):
    docs = ctx.data.get("doc_pages") or []
    if not docs:
        a.limits.append("No document selected. Upload a PDF in the Data Manager and tick it under 'Context' to summarise it.")
        return
    for doc, pages in docs:
        sid = next((b.sid for b in ctx.blocks if doc["filename"] in b.title), "—")
        sents = summarise_document(pages)
        if not sents:
            a.limits.append(f"No extractable financial statements found in {doc['filename']} (scanned PDF?).")
            continue
        a.facts.append(f"Key sentences from **{doc['filename']}** (extractive - quoted verbatim, page numbers in brackets) [{sid}]:\n  " +
                       "\n  ".join(f"(p. {pg}) \"{s}\"" for pg, s in sents))
    a.limits.append("The offline analyst extracts sentences; it does not paraphrase or infer. Connect an AI provider for an abstractive summary.")


HANDLERS = {"growth": _growth, "profitability": _profitability, "debt": _debt, "liquidity": _liquidity,
            "cashflow": _cashflow, "valuation": _valuation, "risk": _risk, "ownership": _ownership,
            "segments": _segments, "news": _news, "overview": _overview, "document": _document,
            "quarterly": _quarterly, "plain": _plain}
DATA_INTENTS = set(HANDLERS) - {"document"}

RECOMMENDATION_POLICY = (
    "**I can't give buy, sell or hold recommendations.** In India, investment recommendations may only be issued by "
    "SEBI-registered research analysts or investment advisers, and this tool is an educational research aid. "
    "Here is the evidence you would weigh when forming your own view:")


def answer(ctx: ResearchContext | None, question: str) -> str:
    q = question.strip()
    intents = detect_intents(q)
    parts = []
    if "recommendation" in intents:
        parts.append(RECOMMENDATION_POLICY)
        intents = ["overview", "risk"]
    if ctx is None:
        a = Answer()
        if not _concept(None, a, q):
            return "Select a company first, or ask about a finance concept (e.g. 'What is ROCE?')."
        return a.md()
    a = Answer()
    metric = asked_metric(q)
    if metric:
        _metric_direct(ctx, a, metric)
    if "concept" in intents:
        if _concept(ctx, a, q):
            intents = [i for i in intents if i not in ("concept", "valuation", "profitability", "debt", "growth", "liquidity", "cashflow")]
        else:
            intents = [i for i in intents if i != "concept"] or ["overview"]
    if "plain" in intents:                      # everyday-language summary replaces the detailed overview
        intents = ["plain"] + [i for i in intents if i not in ("plain", "overview")]
    if "quarterly" in intents:                  # the latest quarter answers revenue / profit / margin questions
        intents = ["quarterly"] + [i for i in intents if i not in ("quarterly", "growth", "profitability", "overview")]
    for i in intents:
        fn = HANDLERS.get(i)
        if fn:
            fn(ctx, a)
    if metric or any(i in DATA_INTENTS for i in intents):
        _periods(ctx, a)
    if ctx.company.get("is_sample"):
        a.limits.append("This is a FICTIONAL sample company - figures are generated for demonstration.")
    body = a.md()
    return "\n\n".join(parts + [body]) if body else "\n\n".join(parts) or \
        "I could not find information relevant to that question in the available data."
