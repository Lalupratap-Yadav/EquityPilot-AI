"""Grounded context for the research assistant.

Everything the assistant may use is collected here as numbered source blocks [S1], [S2], ...
Each block carries its provenance (source, data type, period, retrieval time). The assistant
- offline or LLM - may only state figures that appear in these blocks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from .. import config, db
from .. import formatting as F
from ..analytics import ratios as R
from ..analytics import risk as K
from ..analytics import valuation as V
from ..data import repository as repo
from ..data import uploads as U


@dataclass
class SourceBlock:
    sid: str
    title: str
    text: str
    source: str
    data_type: str
    url: str | None = None
    retrieved: str | None = None


@dataclass
class ResearchContext:
    symbol: str
    company: dict
    blocks: list[SourceBlock] = field(default_factory=list)
    data: dict = field(default_factory=dict)          # structured values used by the offline analyst

    def add(self, title, text, source, data_type, url=None, retrieved=None) -> str:
        sid = f"S{len(self.blocks) + 1}"
        self.blocks.append(SourceBlock(sid, title, text, source, data_type, url, retrieved))
        return sid

    def render(self) -> str:
        out = []
        for b in self.blocks:
            label = config.DATA_TYPES.get(b.data_type, (b.data_type,))[0]
            meta = f"source: {b.source}; type: {label}" + (f"; retrieved: {b.retrieved}" if b.retrieved else "") + \
                   (f"; url: {b.url}" if b.url else "")
            out.append(f"[{b.sid}] {b.title} ({meta})\n{b.text}")
        return "\n\n".join(out)

    def source_list(self) -> pd.DataFrame:
        return pd.DataFrame([{"ID": b.sid, "Content": b.title, "Source": b.source,
                              "Type": config.DATA_TYPES.get(b.data_type, (b.data_type,))[0],
                              "Retrieved": b.retrieved or "—", "Link": b.url} for b in self.blocks])


def _amt(v, cur):
    if F.is_missing(v):
        return "n/a"
    return f"₹{F.amount(v, cur)} Cr" if (cur or "INR") == "INR" else f"{cur} {F.amount(v, cur)} mn"


def build_context(symbol: str, question: str = "", doc_ids: list[int] | None = None,
                  include_news: bool = True, max_doc_chars: int = 12000) -> ResearchContext | None:
    company = repo.get_company(symbol)
    if not company:
        return None
    ctx = ResearchContext(symbol, company)
    sample = bool(company.get("is_sample"))
    dtype_default = "sample" if sample else "third_party"

    # ---- profile
    ctx.add("Company profile",
            f"Name: {company['name']}; symbol: {symbol}; exchange: {company.get('exchange')}; sector: {company.get('sector')}; "
            f"industry: {company.get('industry')}.\nDescription: {company.get('description') or 'not available'}"
            + ("\nNOTE: This is a FICTIONAL sample company; its data is generated for demonstration." if sample else ""),
            company.get("source") or "—", company.get("data_type") or dtype_default, company.get("source_url"),
            F.ist(company.get("fetched_at")))

    # ---- market data
    quote = repo.get_quote(symbol)
    fd = repo.get_financials(symbol, auto_refresh=False)
    fq = repo.get_financials(symbol, "quarterly", basis=fd.basis if not fd.empty else None, auto_refresh=False)
    snap = V.market_snapshot(quote, fd, fq)
    ctx.data.update(company=company, quote=quote, fd=fd, snap=snap)
    if quote:
        ctx.add("Market data and valuation multiples",
                f"Price: {F.inr(quote.get('price'))} (as of {F.ist(quote.get('as_of') or quote.get('fetched_at'))}); "
                f"market cap: {F.big_inr(snap.get('market_cap'))}; P/E: {F.mult(snap.get('pe'))} "
                f"(earnings basis: {snap['basis'].get('earnings')}); P/B: {F.mult(snap.get('pb'))}; "
                f"EV/EBITDA: {F.mult(snap.get('ev_ebitda'))}; enterprise value: {F.big_inr(snap.get('ev'))}; "
                f"dividend yield: {F.pct(snap.get('dividend_yield'))}; 52-week range: {F.inr(quote.get('week52_low'))} - "
                f"{F.inr(quote.get('week52_high'))}; provider beta: {F.num(quote.get('beta'))}. "
                "Multiples are calculated by EquityPilot from the price and the statements below.",
                quote.get("source") or "—", quote.get("data_type") or dtype_default, quote.get("source_url"),
                F.ist(quote.get("fetched_at")))

    # ---- statements
    if not fd.empty:
        cur = fd.currency
        lines = []
        for p in fd.periods:
            g = lambda k: fd.wide.at[k, p] if k in fd.wide.index else None  # noqa: E731
            lines.append(f"{F.fiscal_label(p)}: revenue {_amt(g('revenue'), cur)}; EBITDA {_amt(g('ebitda'), cur)}; "
                         f"EBIT {_amt(g('ebit'), cur)}; net profit {_amt(g('net_income'), cur)}; diluted EPS "
                         f"{F.num(g('eps_diluted'))}; equity {_amt(g('total_equity'), cur)}; borrowings {_amt(g('total_debt'), cur)}; "
                         f"cash {_amt(g('cash'), cur)}; CFO {_amt(g('cfo'), cur)}; capex {_amt(g('capex'), cur)}")
        ctx.add(f"Annual financial statements summary ({fd.basis} basis, currency {cur})", "\n".join(lines),
                "; ".join(fd.sources) or "—", fd.data_types[0] if fd.data_types else dtype_default,
                fd.source_urls[0] if fd.source_urls else None, F.ist(fd.fetched_at))
        rt = R.compute_ratios(fd)
        ctx.data["ratios"] = rt
        rl = []
        for k, d in R.RATIOS.items():   # every ratio the assistant may cite must be in the context
            vals = ", ".join(f"{F.fiscal_label(p)} {F.by_kind(rt.at[k, p], d.kind)}" for p in rt.columns)
            rl.append(f"{d.label} [{d.formula}]: {vals}")
        dp = R.dupont(fd)
        if not dp.empty:
            last = dp.iloc[:, -1]
            rl.append(f"DuPont (latest FY): net margin {F.pct(last['Net margin'])} × asset turnover "
                      f"{F.mult(last['Asset turnover'], 2)} × equity multiplier {F.mult(last['Equity multiplier'], 2)} "
                      f"= ROE {F.pct(last['ROE (product)'])}")
        cg = f"Revenue CAGR (3y): {F.pct(R.cagr(fd.get('revenue'), 3))}; net profit CAGR (3y): {F.pct(R.cagr(fd.get('net_income'), 3))}."
        ctx.add("Financial ratios calculated by EquityPilot", "\n".join(rl) + "\n" + cg,
                "Calculated by EquityPilot from the statements above", "calculated")
        issues = R.quality_checks(fd)
        if issues:
            ctx.add("Data-quality notes", "\n".join(f"- {i['check']}: {i['detail']}" for i in issues),
                    "EquityPilot data-quality checks", "calculated")
        if R.is_financial(company):
            ctx.add("Sector note", "This is a financial-sector company: EV/EBITDA, debt/equity and current ratio are not "
                    "meaningful; use P/B, ROE and asset-quality data from filings.", "EquityPilot methodology", "calculated")

    # ---- risk
    px = repo.get_prices(symbol, auto_refresh=False)
    flags = K.assess(company, fd, px, repo.get_shareholding(symbol), repo.get_segments(symbol))
    ctx.data["risk_flags"] = flags
    if flags:
        score = K.overall_score(flags)
        ctx.add("Rule-based risk checks", "\n".join(f"- {f['category']} / {f['title']}: {f['value']} -> "
                                                    f"{K.LEVEL_LABEL.get(f['level'])} (thresholds: {f['rule']})" for f in flags)
                + (f"\nComposite risk score: {score:.0f}/100 (Low 0, Moderate 33, Elevated 67, High 100; average of checks)"
                   if score is not None else ""),
                "Calculated by EquityPilot (rule-based thresholds)", "calculated")

    # ---- segments & shareholding
    seg = repo.get_segments(symbol)
    if not seg.empty:
        latest = seg[seg["period"] == sorted(seg["period"].unique())[-1]]
        tot = latest["revenue"].sum()
        ctx.add(f"Revenue segments ({latest['period'].iloc[0]})",
                "; ".join(f"{r['segment']}: {F.crore(r['revenue'])} ({r['revenue'] / tot:.0%})" for _, r in latest.iterrows()),
                latest["source"].iloc[0] or "—", latest["data_type"].iloc[0], latest["source_url"].iloc[0])
    sh = repo.get_shareholding(symbol)
    if not sh.empty:
        latest = sh[sh["period"] == sorted(sh["period"].unique())[-1]]
        ctx.add(f"Shareholding pattern (quarter ended {latest['period'].iloc[0]})",
                "; ".join(f"{r['category']}: {r['pct']:.2f}%" + (f" (pledged {r['pledged_pct']:.1f}%)" if pd.notna(r['pledged_pct']) else "")
                          for _, r in latest.iterrows()),
                latest["source"].iloc[0] or "—", latest["data_type"].iloc[0], latest["source_url"].iloc[0])

    # ---- saved valuation & notes
    val = db.get_setting(f"valuation:{symbol}")
    if val:
        i = val["inputs"]
        ctx.add("Saved DCF valuation (user assumptions)",
                f"Value per share {F.inr(val['per_share'])} vs price {F.inr(val.get('price'))} at save time ({val.get('saved')}). "
                f"Assumptions: WACC {F.pct(i['wacc'])}, terminal growth {F.pct(i['terminal_growth'])}, revenue growth "
                f"{F.pct(i['growth_start'])} fading to {F.pct(i['growth_end'])} over {i['years']} years, EBIT margin "
                f"{F.pct(i['ebit_margin'])}, tax {F.pct(i['tax_rate'])}.", "User valuation in EquityPilot", "assumption")
    notes = db.get_setting(f"notes:{symbol}") or {}
    if any(notes.get(k) for k in ("business_model", "products", "moat", "management")):
        ctx.add("Analyst's own research notes", "\n".join(f"{k.replace('_', ' ').title()}: {notes[k]}" for k in
                                                         ("business_model", "products", "moat", "management") if notes.get(k)),
                f"User notes; cited source: {notes.get('source') or 'not given'}", "user_entered")
    rn = db.get_setting(f"risk_notes:{symbol}") or {}
    if rn.get("text"):
        ctx.add("Analyst's risk notes", rn["text"], f"User notes; cited source: {rn.get('source') or 'not given'}", "user_entered")

    # ---- news & disclosures
    if include_news:
        d = repo.get_disclosures(symbol, limit=15)
        if not d.empty:
            ctx.add("Recent headlines and disclosures (titles only)",
                    "\n".join(f"- {F.fdate(r['date'])} [{r['category']}] {r['title']} ({r['publisher'] or r['source']})"
                              for _, r in d.iterrows()),
                    "Yahoo Finance news aggregator / user-logged filings", d["data_type"].iloc[0])

    # ---- documents: keyword-ranked pages
    for doc_id in doc_ids or []:
        doc = U.get_document(int(doc_id))
        if not doc:
            continue
        pages = U.text_to_pages(doc["text"])
        chosen = rank_pages(pages, question, max_doc_chars)
        if chosen:
            ctx.add(f"Excerpts from uploaded document '{doc['filename']}' ({doc['doc_type']}, {doc['period']})",
                    "\n".join(f"<page {p['page']}>\n{p['text'].strip()}" for p in chosen),
                    f"Uploaded document: {doc['filename']}", "official_upload", doc.get("source_url"), F.ist(doc["uploaded_at"]))
            ctx.data.setdefault("doc_pages", []).append((doc, pages))
    return ctx


KEY_TERMS = ["revenue", "profit", "margin", "growth", "guidance", "outlook", "risk", "capex", "dividend", "debt",
             "segment", "ebitda", "order", "demand", "strategy", "expansion", "cash flow", "working capital"]


def rank_pages(pages: list[dict], question: str, max_chars: int) -> list[dict]:
    """Pick the pages most relevant to the question (keyword overlap), within a character budget."""
    words = [w for w in re.findall(r"[a-z]{4,}", (question or "").lower()) if w not in
             {"what", "which", "about", "does", "this", "that", "with", "from", "have", "company", "explain", "please", "summarise", "summarize"}]
    terms = set(words) or set(KEY_TERMS)
    scored = []
    for p in pages:
        low = p["text"].lower()
        score = sum(low.count(t) for t in terms)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    out, used = [], 0
    for _, p in scored:
        t = p["text"][:4000]
        if used + len(t) > max_chars:
            break
        out.append({"page": p["page"], "text": t})
        used += len(t)
    return sorted(out, key=lambda p: p["page"])


NUM_RE = re.compile(r"(?<![\w.])[-+]?\d[\d,]*\.?\d*")


def _norm_numbers(text: str) -> set[str]:
    out = set()
    for m in NUM_RE.findall(text):
        s = m.replace(",", "").lstrip("+")
        try:
            v = float(s)
        except ValueError:
            continue
        if abs(v) < 10 and "." not in s:
            continue
        out.add(f"{v:.2f}".rstrip("0").rstrip("."))
        out.add(f"{round(v):d}")
        out.add(f"{v:.1f}".rstrip("0").rstrip("."))
    return out


def grounding_check(answer: str, context_text: str) -> tuple[int, list[str]]:
    """Heuristic: list figures in the answer that do not appear in the context (after normalisation).
    Small integers (years, counts < 10) are ignored."""
    ctx_nums = _norm_numbers(context_text)
    untraced = []
    total = 0
    for m in NUM_RE.findall(answer):
        s = m.replace(",", "").lstrip("+")
        try:
            v = float(s)
        except ValueError:
            continue
        if abs(v) < 10 and "." not in s or (1990 <= v <= 2100 and "." not in s):
            continue
        total += 1
        cands = {f"{v:.2f}".rstrip("0").rstrip("."), f"{round(v):d}", f"{v:.1f}".rstrip("0").rstrip(".")}
        if not cands & ctx_nums:
            untraced.append(m)
    return total, untraced
