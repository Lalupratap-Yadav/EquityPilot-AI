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
from ..analytics import bank as B
from ..analytics import ratios as R
from ..analytics import risk as K
from ..analytics import valuation as V
from ..data import repository as repo
from ..data import source_tiers as ST
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


def _results_filings(symbol: str) -> list[str]:
    """Latest results the company filed with NSE and its next confirmed results board meeting - dates exactly as the
    exchange records them, never estimated."""
    try:
        from ..data import events as EV
        filed = [f for f in EV.results_filed(400, symbol) if f["kind"] == "results"]
        meets = [m for m in EV.board_meetings(400, symbol) if m["results"]]
        today = EV.today_ist().isoformat()
    except Exception:          # the filings feed is optional context
        return []
    filed.sort(key=lambda f: f["filed"] or "", reverse=True)
    upcoming = sorted((m for m in meets if m["meeting_date"] >= today), key=lambda m: m["meeting_date"])
    out = []
    for f in filed[:2]:
        out.append(f"Results filed on {(f['filed'] or '')[:10]}: {f['subject'] or 'financial results'}"
                   + (f"; period {f['period']}" if f.get("period") else "") + (f"; {f['basis']}" if f.get("basis") else "")
                   + (f"; filing: {f['url']}" if f.get("url") else ""))
    for m in upcoming[:1]:
        out.append(f"Next board meeting to consider results (date confirmed by the company): {m['meeting_date']}"
                   + (f" - {m['purpose'][:140]}" if m.get("purpose") else ""))
    return out


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

    # ---- quarterly results (provider statements) and the exchange filings about them
    ctx.data["fq"] = fq
    if fq is not None and not fq.empty:
        qs = R.quarterly_summary(fq).tail(5)
        if not qs.empty:
            cur = fq.currency
            ql = []
            for p, r in qs.iterrows():
                ql.append(f"Quarter ended {pd.Timestamp(p).strftime('%b %Y')}: revenue {_amt(r['revenue'], cur)} "
                          f"(vs previous quarter {F.pct(r['revenue_qoq'], 1, True)}, vs same quarter last year {F.pct(r['revenue_yoy'], 1, True)}); "
                          f"EBITDA {_amt(r['ebitda'], cur)}; net profit {_amt(r['net_income'], cur)} "
                          f"(vs previous quarter {F.pct(r['net_income_qoq'], 1, True)}, vs same quarter last year {F.pct(r['net_income_yoy'], 1, True)}); "
                          f"EBITDA margin {F.pct(r['ebitda_margin'])} (same quarter last year {F.pct(r['ebitda_margin_ly'])}); "
                          f"net margin {F.pct(r['net_margin'])}; diluted EPS {F.num(r['eps'])}")
            ctx.add(f"Quarterly results ({fq.basis} basis, currency {cur})", "\n".join(ql), "; ".join(fq.sources) or "—",
                    fq.data_types[0] if fq.data_types else dtype_default, fq.source_urls[0] if fq.source_urls else None,
                    F.ist(fq.fetched_at))
    if not sample:
        lines = _results_filings(symbol)
        if lines:
            ctx.add("Exchange filings about results", "\n".join(lines), "NSE corporate announcements (RSS)", "official",
                    "https://www.nseindia.com/companies-listing/corporate-filings-financial-results")

    # ---- bank metrics (quarterly disclosures entered by the user)
    bm = repo.get_bank_metrics(symbol)
    if not bm.empty:
        w = B.wide(bm)
        lines = [f"{B.BANK_METRICS[k][0]}: " + ", ".join(f"{p} {v:.2f}%" for p, v in w.loc[k].dropna().items())
                 for k in w.index]
        ctx.add("Bank metrics from quarterly disclosures", "\n".join(lines), bm["source"].dropna().iloc[-1] if bm["source"].notna().any() else "—",
                bm["data_type"].iloc[-1], bm["source_url"].dropna().iloc[-1] if bm["source_url"].notna().any() else None,
                F.ist(pd.to_datetime(bm["fetched_at"]).max()))
        ctx.data["bank_metrics"] = bm

    # ---- risk
    px = repo.get_prices(symbol, auto_refresh=False)
    flags = K.assess(company, fd, px, repo.get_shareholding(symbol), repo.get_segments(symbol),
                     repo.get_bank_metrics(symbol))
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
        d = repo.get_disclosures(symbol, limit=25)
        if not d.empty:  # unrated publishers (tip sites, blogs) are never used as evidence
            d = d[[ST.tier(r["publisher"], r["data_type"]) != "unrated" for _, r in d.iterrows()]].head(15)
        if not d.empty:
            ctx.add("Recent headlines and disclosures (titles only)",
                    "\n".join(f"- {F.fdate(r['date'])} [{r['category']}] {r['title']} ({r['publisher'] or r['source']})"
                              for _, r in d.iterrows()),
                    "Yahoo Finance news aggregator (established publishers only) / user-logged filings", d["data_type"].iloc[0])

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


CITE_RE = re.compile(r"\[((?:[TS]\d+)(?:\s*[,;]\s*[TS]\d+)*)\]")
_CALC_LINE_RE = re.compile(r"=|\bcalculat|\bformula\b|×|\bdivided by\b|\bminus\b|\bdifference\b", re.I)


def _counted_figures(text: str) -> list[tuple[str, float]]:
    out = []
    for m in NUM_RE.findall(text):
        s = m.replace(",", "").lstrip("+")
        try:
            v = float(s)
        except ValueError:
            continue
        if abs(v) < 10 and "." not in s or (1990 <= v <= 2100 and "." not in s):
            continue                                   # small counts and years
        out.append((m, v))
    return out


def _traced(v: float, ctx_nums: set[str]) -> bool:
    return bool({f"{v:.2f}".rstrip("0").rstrip("."), f"{round(v):d}", f"{v:.1f}".rstrip("0").rstrip(".")} & ctx_nums)


def grounding_report(answer: str, context_text: str, source_ids: list[str] | None = None) -> dict:
    """Checks an AI answer against the data it was given, so problems are shown with the answer, never hidden:
    - `untraced`: figures that appear nowhere in the retrieved data;
    - `calculated`: figures on a line marked as a calculation (with '=' or 'calculated') whose other figures are traced -
      the model computed them from cited inputs, which the answer must show;
    - `unknown_citations`: source IDs cited in the answer that were never retrieved;
    - `uncited_lines`: lines that state figures but cite no source."""
    ctx_nums = _norm_numbers(context_text)
    total, untraced, calculated, uncited = 0, [], [], 0
    for line in answer.splitlines():
        figs = _counted_figures(line)
        if not figs:
            continue
        total += len(figs)
        traced = [_traced(v, ctx_nums) for _, v in figs]
        calc_line = bool(_CALC_LINE_RE.search(line)) and any(traced)
        for (raw, _), ok in zip(figs, traced):
            if not ok:
                (calculated if calc_line else untraced).append(raw)
        if not CITE_RE.search(line) and not line.lstrip().startswith(("|---", "#")):
            uncited += 1
    known = set(source_ids or [])
    cited = {c for grp in CITE_RE.findall(answer) for c in re.split(r"\s*[,;]\s*", grp)}
    unknown = sorted(cited - known) if known else []
    return {"figures": total, "untraced": untraced[:10], "calculated": calculated[:10], "unknown_citations": unknown[:10],
            "uncited_lines": uncited}


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
