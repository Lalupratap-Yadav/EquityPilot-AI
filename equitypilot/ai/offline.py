"""Offline research analyst (free, no API).

A deterministic, rule-based assistant that answers from the grounded context only. It separates
FACTS (with source IDs), CALCULATIONS (with formulas), ASSUMPTIONS, an AUTOMATED INTERPRETATION
(rule-based, clearly labelled) and LIMITATIONS. It never issues buy/sell recommendations.
"""
from __future__ import annotations

import re

import pandas as pd

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
    ("profitability", r"\b(profit|margin|ebitda|roe|roce|return on|profitab|earnings|eps)\b"),
    ("growth", r"\b(growth|grow|revenue|sales|cagr|top ?line)\b"),
    ("risk", r"\b(risk|risks|red flag|concern|weakness|pledge|volatil)\b"),
    ("ownership", r"\b(shareholding|promoter|fii|dii|ownership|holding pattern)\b"),
    ("segments", r"\b(segment|business mix|division|geograph)\b"),
    ("news", r"\b(news|announcement|disclosure|headline|recent)\b"),
    ("overview", r"\b(overview|summary|summari[sz]e|tell me about|about the company|snapshot|business model)\b"),
]


def detect_intents(q: str) -> list[str]:
    ql = q.lower()
    found = [name for name, pat in INTENTS if re.search(pat, ql)]
    return found or ["overview"]


def _sid(ctx: ResearchContext, startswith: str) -> str:
    for b in ctx.blocks:
        if b.title.startswith(startswith):
            return b.sid
    return "—"


class Answer:
    def __init__(self):
        self.facts, self.calcs, self.assumptions, self.interp, self.limits = [], [], [], [], []

    def md(self, title: str | None = None) -> str:
        parts = [f"**{title}**\n"] if title else []
        sections = [("Facts from sources", self.facts), ("Calculations", self.calcs), ("Assumptions", self.assumptions),
                    ("Automated interpretation (rule-based, not advice)", self.interp),
                    ("Limitations and missing information", self.limits)]
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
        a.interp.append(f"Latest revenue growth of {F.pct(last)} is {'above' if c3 is not None and last > c3 else 'below'} the "
                        f"3-year CAGR of {F.pct(c3)}, i.e. growth is {'accelerating' if c3 is not None and last > c3 else 'slowing'} versus the recent trend.")
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


def _overview(ctx, a: Answer):
    c, s0 = ctx.company, _sid(ctx, "Company profile")
    a.facts.append(f"{c['name']} - {c.get('sector') or 'sector n/a'} / {c.get('industry') or 'industry n/a'} [{s0}]")
    if c.get("description"):
        a.facts.append(f"Business: {c['description'][:600]}{'…' if len(c['description']) > 600 else ''} [{s0}]")
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
            "segments": _segments, "news": _news, "overview": _overview, "document": _document}

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
    if "concept" in intents:
        if _concept(ctx, a, q):
            intents = [i for i in intents if i not in ("concept", "valuation", "profitability", "debt", "growth", "liquidity", "cashflow")]
        else:
            intents = [i for i in intents if i != "concept"] or ["overview"]
    for i in intents:
        fn = HANDLERS.get(i)
        if fn:
            fn(ctx, a)
    if ctx.company.get("is_sample"):
        a.limits.append("This is a FICTIONAL sample company - figures are generated for demonstration.")
    body = a.md()
    return "\n\n".join(parts + [body]) if body else "\n\n".join(parts) or \
        "I could not find information relevant to that question in the available data."
