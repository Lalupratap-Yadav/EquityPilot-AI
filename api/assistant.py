"""EquityPilot research agent.

One set of grounded research tools serves every engine:

* Claude (Anthropic API) runs an agentic tool-use loop: it decides which tools to call (find a company, pull its
  research pack, compare peers, screen the universe, read the market, check news, search the user's documents),
  then writes an answer that cites the tool results by ID ([T1], [T2] ...). Answers stream to the browser.
* The free offline analyst routes the question with rules (market / compare / screen / company / concept) and
  calls the same tools, so it can answer market-wide and multi-company questions without any API key.
* Ollama (local model) receives the tool results gathered by the offline router as its context.

Every tool result is labelled with its source and data type, and every figure the model writes is checked
against the tool results (grounding check). Nothing here places orders or gives buy/sell recommendations.
"""
from __future__ import annotations

import inspect
import json
import logging
import re
import threading
import time
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pandas as pd

from equitypilot import config
from equitypilot import formatting as F
from equitypilot.ai import learning as LRN
from equitypilot.ai import offline, rag
from equitypilot.ai import providers as P
from equitypilot.ai.context import build_context, grounding_report
from equitypilot.analytics import technicals as T
from equitypilot.analytics.screener import METRIC_COLUMNS
from equitypilot.content import curriculum as CU
from equitypilot.content import metrics_guide as MG
from equitypilot.content.glossary import GLOSSARY, find_term
from equitypilot.content.industries import BY_ID, INDUSTRIES
from equitypilot.data import marketdata as M
from equitypilot.data import repository as repo
from equitypilot.data import securities as S

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
MAX_NEW_COMPANIES = 2            # companies the agent may fetch from the provider per question
MAX_TURNS = 8


class ToolError(Exception):
    pass


# ------------------------------------------------------------------ formatting helpers
def fmt_metric(key: str, v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n/a"
    kind = METRIC_COLUMNS.get(key, ("", "num"))[1]
    v = float(v)
    if kind == "pct":
        return f"{v * 100:+.2f}%" if key == "day_change" else f"{v * 100:.1f}%"
    if kind == "x":
        return f"{v:.2f}x"
    if kind == "inr":
        return f"₹{v:,.2f}"
    if kind == "cr":
        return F.crore(v)
    return f"{v:.0f}" if key == "piotroski" else f"{v:,.2f}"


def _label(key: str) -> str:
    return METRIC_COLUMNS.get(key, (key,))[0]


def _now_ist() -> str:
    return datetime.now(IST).strftime("%d %b %Y, %H:%M IST")


# ------------------------------------------------------------------ tool definitions (Anthropic tool-use schema)
METRIC_KEYS = list(METRIC_COLUMNS)
TOOLS = [
    {"name": "find_company",
     "description": "Resolve a company name, brand or partial symbol to EquityPilot symbols (NSE '.NS' / BSE '.BO'). "
                    "Call this first whenever the user names a company and you do not already know its exact symbol.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "Company name or symbol, e.g. 'Infosys' or 'HDFC Bank'"}},
                      "required": ["query"]}},
    {"name": "company_research",
     "description": "Full research pack for ONE company: profile, latest delayed quote and valuation multiples, multi-year "
                    "financial statements summary, calculated ratios (growth, margins, ROE/ROCE, leverage, cash conversion), "
                    "rule-based risk checks, shareholding, segments, saved DCF and recent headlines. Use for any company-specific question.",
     "input_schema": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Exact symbol, e.g. TCS.NS"}},
                      "required": ["symbol"]}},
    {"name": "price_performance",
     "description": "Price returns over 1 week, 1/3/6 months, 1/3/5 years, 52-week high/low, distance from the high, "
                    "annualised volatility and maximum drawdown for one company or index (e.g. ^NSEI for NIFTY 50, ^BSESN for SENSEX).",
     "input_schema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
    {"name": "compare_companies",
     "description": "Side-by-side key metrics (valuation, growth, profitability, leverage, cash conversion, day change) for 2-6 companies.",
     "input_schema": {"type": "object", "properties": {"symbols": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6}},
                      "required": ["symbols"]}},
    {"name": "screen_companies",
     "description": "Filter and rank the companies EquityPilot tracks (about 120 large and mid caps plus anything users added). "
                    f"Metrics: {', '.join(METRIC_KEYS)}. Percent metrics are fractions (0.15 = 15%). Ratios like pe are plain numbers.",
     "input_schema": {"type": "object", "properties": {
         "filters": {"type": "array", "items": {"type": "object", "properties": {
             "metric": {"type": "string", "enum": METRIC_KEYS}, "op": {"type": "string", "enum": [">", ">=", "<", "<="]},
             "value": {"type": "number"}}, "required": ["metric", "op", "value"]}},
         "industry": {"type": "string", "enum": [i["id"] for i in INDUSTRIES]},
         "sort_by": {"type": "string", "enum": METRIC_KEYS}, "ascending": {"type": "boolean"},
         "limit": {"type": "integer", "minimum": 1, "maximum": 25}}}},
    {"name": "market_overview",
     "description": "Today's market snapshot: NIFTY/SENSEX and sector indices (value, day change, 1-month change), market "
                    "breadth, top gainers/losers/most active among tracked companies, and sector moves. Includes market session status.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "latest_news",
     "description": "Recent headlines from primary sources (NSE/BSE disclosures, RBI, SEBI) and established publishers. "
                    "Give a symbol for company news, or a section: disclosures, results, economy, regulation, global.",
     "input_schema": {"type": "object", "properties": {"symbol": {"type": "string"},
                                                        "section": {"type": "string", "enum": ["disclosures", "results", "economy", "regulation", "global"]},
                                                        "limit": {"type": "integer", "minimum": 1, "maximum": 15}}}},
    {"name": "search_documents",
     "description": "Search the annual reports / filings the user selected for this conversation; returns verbatim passages with page numbers.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "learning_content",
     "description": "EquityPilot Learning Centre content (beginner to advanced, reviewed against official sources): for a topic, the "
                    "glossary entry and the lesson's concept, formulas or key rules, worked example, interpretation, common mistakes "
                    "and practice question ids; for a question id such as 'ratios-returns:c1', that quiz question with its correct "
                    "answer, explanation, calculation and why each option is wrong. Use it for learning questions: explaining a concept "
                    "more simply, formulas step by step, differences between concepts, practice questions and quiz answers.",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string", "description": "Concept or lesson, e.g. 'ROCE' or 'terminal value'"},
                                                        "question_id": {"type": "string", "description": "Learning Centre question id, e.g. 'dcf-wacc:c2'"}}}},
    {"name": "explain_metric",
     "description": "Plain-English definition, formula, how to read it and benchmark guidance for a finance metric or term (e.g. ROCE, P/E, free cash flow).",
     "input_schema": {"type": "object", "properties": {"term": {"type": "string"}}, "required": ["term"]}},
]
for _t in TOOLS:
    _t["eager_input_streaming"] = True     # inputs stream as generated; validated below before any tool runs

STATUS_TEXT = {"find_company": "Looking up {query}", "company_research": "Reading {symbol} financials, ratios and filings",
               "price_performance": "Checking {symbol} price history", "compare_companies": "Comparing {symbols}",
               "screen_companies": "Screening tracked companies", "market_overview": "Reading today's market",
               "latest_news": "Checking latest news", "search_documents": "Searching your documents for '{query}'",
               "explain_metric": "Looking up {term}", "learning_content": "Reading the Learning Centre"}


# ------------------------------------------------------------------ the toolbox (one per question)
class ToolBox:
    def __init__(self, uid: int | None = None, doc_ids: list[int] | None = None, allow_fetch: bool = True):
        self.uid, self.doc_ids, self.allow_fetch = uid, doc_ids or [], allow_fetch
        self.sources: list[dict] = []
        self.texts: list[str] = []
        self.fetched = 0
        self.symbols_used: list[str] = []
        self._lock = threading.RLock()        # tools may run in parallel threads: IDs and lists stay consistent

    # -- bookkeeping
    def src(self, content: str, source: str, dtype: str, link: str | None = None, retrieved: str | None = None,
            excerpt: str | None = None) -> str:
        label = config.DATA_TYPES.get(dtype, (dtype,))[0]
        with self._lock:
            sid = f"T{len(self.sources) + 1}"
            self.sources.append({"ID": sid, "Content": content, "Source": source, "Type": label, "Retrieved": retrieved or "—",
                                 "Link": link, **({"excerpt": excerpt} if excerpt else {})})
        return sid

    def describe(self, name: str, args: dict) -> str:
        def show(v):
            if isinstance(v, list):
                return ", ".join(f"{_label(x.get('metric', ''))} {x.get('op', '')} {fmt_metric(x.get('metric', ''), x.get('value'))}"
                                 if isinstance(x, dict) else str(x) for x in v)
            return v
        a = {k: show(v) for k, v in (args or {}).items()}
        if name == "screen_companies" and a.get("filters"):
            return f"Screening tracked companies: {a['filters']}"
        try:
            return STATUS_TEXT.get(name, name).format(**{"query": "", "symbol": "", "symbols": "", "term": "", **a})
        except (KeyError, IndexError, ValueError):
            return name.replace("_", " ")

    def context_text(self) -> str:
        return "\n\n".join(self.texts)

    def run(self, name: str, args: dict) -> str:
        if not isinstance(args, dict):
            raise ToolError("Tool input must be a JSON object.")
        fn = getattr(self, f"t_{name}", None)
        if fn is None:
            raise ToolError(f"Unknown tool '{name}'.")
        params = set(inspect.signature(fn).parameters)
        out = fn(**{k: v for k, v in args.items() if k in params})
        with self._lock:
            self.texts.append(out)
        return out

    def run_many(self, calls: list[tuple[str, dict]]) -> list[tuple[str | None, str | None]]:
        """Independent tool calls at once (threads; the data reads release the interpreter for I/O). Returns
        (result, error message) per call, in the order given."""
        def one(call):
            name, args = call
            try:
                return self.run(name, args), None
            except ToolError as exc:
                return None, str(exc)
            except Exception as exc:              # a data problem must not kill the conversation
                log.exception("tool %s failed", name)
                return None, f"tool failed ({type(exc).__name__})"
        if len(calls) <= 1:
            return [one(c) for c in calls]
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(4, len(calls))) as ex:
            return list(ex.map(one, calls))

    # -- symbol handling
    def resolve(self, raw: str) -> str:
        """Exact tracked symbol for user/model input ('tcs', 'TCS', 'TCS.NS', 'Tata Consultancy')."""
        if not isinstance(raw, str) or not raw.strip():
            raise ToolError("A symbol is required.")
        s = raw.strip()[:40]
        if s.startswith("^") or s.upper().startswith("SAMPLE-"):
            return s.upper() if s.upper().startswith("SAMPLE-") else s
        cand = s.upper()
        if repo.get_company(cand):
            return cand
        if "." not in cand and repo.get_company(cand + ".NS"):
            return cand + ".NS"
        best = S.resolve(s, 3)
        if best and best[0]["score"] >= 75:
            return best[0]["symbol"]
        hits = S.search(s, 5)
        if not hits:
            raise ToolError(f"No company found for '{raw}'. Try find_company with the company name.")
        exact = [h for h in hits if h["symbol"].rsplit(".", 1)[0].upper() == cand.rsplit(".", 1)[0]]
        return (exact or hits)[0]["symbol"]

    def ensure_tracked(self, sym: str) -> dict:
        c = repo.get_company(sym)
        if c:
            return c
        if sym.startswith(("^", "SAMPLE-")):
            raise ToolError(f"{sym} is not a company in EquityPilot.")
        if config.OFFLINE or not self.allow_fetch:
            raise ToolError(f"{sym} is not tracked yet. Open its company page once to load its data.")
        with self._lock:
            if self.fetched >= MAX_NEW_COMPANIES:
                raise ToolError(f"{sym} is not tracked yet and the per-question fetch limit was reached.")
            self.fetched += 1
        ok, msg, sym2 = repo.add_company(sym)
        if not ok:
            raise ToolError(f"Could not load {sym} from the data provider: {msg}")
        try:
            from .routes_explore import invalidate_metrics
            invalidate_metrics()
        except Exception:
            pass
        return repo.get_company(sym2) or {}

    # -- tools
    def t_find_company(self, query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ToolError("query is required.")
        hits = S.search(query.strip()[:60], 6)
        if not hits:
            return f"No listed company matched '{query}'."
        lines = [f"- {h['symbol']}: {h['name']}" + (f" ({h.get('sector') or h.get('category') or ''})" if h.get("sector") or h.get("category") else "")
                 + ("" if h.get("tracked") else " [not tracked yet - data is fetched on first use]") for h in hits]
        return f"Matches for '{query}':\n" + "\n".join(lines)

    def t_company_research(self, symbol: str) -> str:
        sym = self.resolve(symbol)
        self.ensure_tracked(sym)
        ctx = build_context(sym, "")
        if ctx is None:
            raise ToolError(f"No data for {sym}.")
        self.symbols_used.append(sym)
        out = [f"Research pack for {ctx.company.get('name')} ({sym}), retrieved {_now_ist()}:"]
        for b in ctx.blocks:
            sid = self.src(f"{sym}: {b.title}", b.source, b.data_type, b.url, b.retrieved)
            label = config.DATA_TYPES.get(b.data_type, (b.data_type,))[0]
            out.append(f"[{sid}] {b.title} (source: {b.source}; type: {label})\n{b.text}")
        return "\n\n".join(out)

    def t_price_performance(self, symbol: str) -> str:
        sym = self.resolve(symbol)
        if sym.startswith("SAMPLE-"):
            px = repo.get_prices(sym, auto_refresh=False)
            source, dtype = "EquityPilot sample dataset (fictional)", "sample"
        else:
            from .routes_market import _bars_cached
            try:
                px = _bars_cached(sym, "5Y")
            except Exception as exc:
                log.warning("price tool %s: %s", sym, exc)
                px = pd.DataFrame()
            if px.empty and repo.get_company(sym):
                px = repo.get_prices(sym, auto_refresh=False)
            source, dtype = M.provider().name, "delayed"
        if px is None or px.empty:
            raise ToolError(f"No price history available for {sym}.")
        px = px.sort_values("time")
        c = px.set_index(pd.to_datetime(px["time"]))["close"].astype(float).dropna()
        q = M.QUOTES.get([sym], stale_ok=True).get(sym) or {}
        last = float(q["price"]) if q.get("price") else float(c.iloc[-1])
        end = c.index[-1]
        rows = []
        for label, days in (("1 week", 7), ("1 month", 30), ("3 months", 91), ("6 months", 182), ("1 year", 365),
                            ("3 years", 1095), ("5 years", 1825)):
            past = c[c.index <= end - pd.Timedelta(days=days)]
            if len(past):
                r = last / float(past.iloc[-1]) - 1
                yrs = days / 365
                extra = f" (CAGR {((1 + r) ** (1 / yrs) - 1) * 100:.1f}% a year)" if yrs >= 3 else ""
                rows.append(f"- {label}: {r * 100:+.1f}%{extra}")
        yr = c[c.index > end - pd.Timedelta(days=365)]
        hi, lo = float(yr.max()), float(yr.min())
        ret = yr.pct_change().dropna()
        vol = float(ret.std() * 252 ** 0.5) if len(ret) > 20 else None
        dd = T.max_drawdown(yr) if len(yr) > 2 else None
        sid = self.src(f"{sym}: price performance", source, dtype, retrieved=_now_ist())
        return (f"[{sid}] Price performance of {sym} (source: {source}; delayed/end-of-day; latest value {last:,.2f}"
                f"{' as of ' + str(M.ist_date(q.get('time'))) if q.get('time') else ''}):\n" + "\n".join(rows) +
                f"\n- 52-week high {hi:,.2f}, low {lo:,.2f}; latest is {(last / hi - 1) * 100:+.1f}% from the high and "
                f"{(last / lo - 1) * 100:+.1f}% above the low"
                + (f"\n- Annualised volatility (1 year, daily): {vol * 100:.1f}%" if vol is not None else "")
                + (f"\n- Maximum drawdown in the last year: {dd * 100:.1f}%" if dd is not None else "")
                + "\nPast returns do not predict future returns.")

    def _metrics(self) -> pd.DataFrame:
        from .routes_explore import metrics_frame
        from .routes_market import universe_snapshot
        df = metrics_frame().copy()
        snap = {r["symbol"]: r for r in universe_snapshot()}
        df["day_change"] = [snap.get(s, {}).get("change_pct", d) for s, d in zip(df["symbol"], df.get("day_change", [None] * len(df)))]
        df["price"] = [snap.get(s, {}).get("price") or p for s, p in zip(df["symbol"], df["price"])]
        return df

    COMPARE_KEYS = ["price", "day_change", "market_cap", "pe", "pb", "ev_ebitda", "dividend_yield", "revenue_growth",
                    "revenue_cagr_3y", "profit_cagr_3y", "ebitda_margin", "net_margin", "roe", "roce", "debt_to_equity",
                    "interest_coverage", "cfo_to_net_income", "piotroski"]

    def t_compare_companies(self, symbols: list) -> str:
        if not isinstance(symbols, list) or not 2 <= len(symbols) <= 6:
            raise ToolError("Give 2 to 6 symbols.")
        syms = []
        for s in symbols:
            sym = self.resolve(str(s))
            self.ensure_tracked(sym)
            syms.append(sym)
        df = self._metrics()
        missing = [s for s in syms if s not in set(df["symbol"])]
        if missing:
            from equitypilot.analytics.screener import company_metrics
            df = pd.concat([df, pd.DataFrame([company_metrics(s) for s in missing])], ignore_index=True)
        df = df[df["symbol"].isin(syms)]
        if df.empty:
            raise ToolError("No metrics available for these companies yet (try again in a minute).")
        df = df.set_index("symbol").reindex([s for s in syms if s in set(df["symbol"])])
        self.symbols_used += syms
        sid = self.src("Comparison: " + ", ".join(syms), "EquityPilot calculations from company filings data (Yahoo Finance) and delayed quotes",
                       "calculated", retrieved=_now_ist())
        head = "| Metric | " + " | ".join(s.rsplit(".", 1)[0] for s in df.index) + " |"
        sep = "|---" * (len(df.index) + 1) + "|"
        self.last_compare = df
        body = []
        for k in self.COMPARE_KEYS:
            vals = [fmt_metric(k, df.at[s, k] if k in df.columns else None) for s in df.index]
            if any(v != "n/a" for v in vals):              # hide rows with no data for any company
                body.append(f"| {_label(k)} | " + " | ".join(vals) + " |")
        fin = [s for s in df.index if bool(df.at[s, "is_financial"])] if "is_financial" in df.columns else []
        note = f"\nNote: {', '.join(fin)} {'is a' if len(fin) == 1 else 'are'} financial compan{'y' if len(fin) == 1 else 'ies'}: EV/EBITDA, debt/equity and ROCE are not meaningful for lenders." if fin else ""
        return f"[{sid}] Key metrics (latest fiscal year; percentages are yearly unless noted; day change is today's):\n" + \
            "\n".join([head, sep, *body]) + note

    def t_screen_companies(self, filters: list | None = None, industry: str | None = None, sort_by: str | None = None,
                           ascending: bool = False, limit: int = 10) -> str:
        df = self._metrics()
        df = df[~df["is_sample"].astype(bool)]
        universe = len(df)
        applied = []
        if industry:
            if industry not in BY_ID:
                raise ToolError(f"Unknown industry '{industry}'.")
            df = df[df["industry_id"] == industry]
            applied.append(f"industry = {BY_ID[industry]['name']}")
        for f in filters or []:
            if not isinstance(f, dict) or f.get("metric") not in METRIC_COLUMNS or f.get("op") not in (">", ">=", "<", "<="):
                raise ToolError(f"Invalid filter {f!r}.")
            try:
                v = float(f["value"])
            except (TypeError, ValueError) as exc:
                raise ToolError(f"Invalid filter value {f.get('value')!r}.") from exc
            col = pd.to_numeric(df[f["metric"]], errors="coerce")
            df = df[{">": col > v, ">=": col >= v, "<": col < v, "<=": col <= v}[f["op"]]]
            applied.append(f"{_label(f['metric'])} {f['op']} {fmt_metric(f['metric'], v)}")
        key = sort_by if sort_by in METRIC_COLUMNS else "market_cap"
        lender_blind = {"debt_to_equity", "ev_ebitda", "roce", "current_ratio", "interest_coverage"}
        if (key in lender_blind or any(isinstance(f, dict) and f.get("metric") in lender_blind for f in filters or []))                 and "is_financial" in df.columns:
            df = df[~df["is_financial"].astype(bool)]
            applied.append("banks/NBFCs excluded (this ratio is not meaningful for lenders)")
        df = df.assign(_k=pd.to_numeric(df[key], errors="coerce")).dropna(subset=["_k"]).sort_values("_k", ascending=bool(ascending))
        try:
            n = max(1, min(int(limit or 10), 25))
        except (TypeError, ValueError):
            n = 10
        total = len(df)
        df = df.head(n)
        sid = self.src("Screen: " + ("; ".join(applied) or "all tracked companies"), "EquityPilot screener over tracked companies",
                       "calculated", retrieved=_now_ist())
        cols = [key] + [k for k in ("market_cap", "pe", "roe", "revenue_cagr_3y", "debt_to_equity") if k != key]
        lines = [f"| Company | {' | '.join(_label(k) for k in cols)} |", "|---" * (len(cols) + 1) + "|"]
        for _, r in df.iterrows():
            lines.append(f"| {r['name']} ({r['symbol']}) | " + " | ".join(fmt_metric(k, r.get(k)) for k in cols) + " |")
        odd = [str(r["name"]) for _, r in df.iterrows()
               if pd.notna(pd.to_numeric(r.get("pe"), errors="coerce")) and 0 < float(r.get("pe")) < 3]
        if odd:
            lines.append(f"\nCheck before relying on it: a P/E below 3 ({', '.join(odd)}) usually means net profit includes a "
                         "one-off gain (for example from a demerger or an asset sale); see the results filing.")
        return (f"[{sid}] Screen over the {universe} companies EquityPilot tracks (not the whole exchange). "
                f"Filters: {'; '.join(applied) or 'none'}. Sorted by {_label(key)} {'ascending' if ascending else 'descending'}. "
                f"{total} matched; showing {len(df)}.\n" + ("\n".join(lines) if len(df) else "No company matched.")
                + "\nA screen is a rule-based filter, not a recommendation.")

    def t_market_overview(self) -> str:
        from .routes_market import movers, sectors
        st = M.market_status()
        idx = M.index_overview()
        mv = movers(5)
        sec = sectors()
        sid = self.src("Market overview (indices, breadth, movers, sectors)", M.provider().name, "live" if M.provider().realtime else "delayed",
                       retrieved=_now_ist())
        lines = [f"[{sid}] Market snapshot at {st['now_ist']} - session: {st['phase']}"
                 + (" (exchange holiday)" if st.get("holiday") else "") + f". {st['note']}"]
        lines.append("Indices (value, day change, 1-month change):")
        for i in idx:
            lines.append(f"- {i['name']}: {i['last']:,.2f}, {F.pct(i.get('change_pct'), 2, True)} today, "
                         f"{F.pct(i.get('month_change_pct'), 1, True)} over 1 month (as of {i.get('as_of')})")
        b = mv.get("breadth")
        if b:
            lines.append(f"Breadth among {mv['universe']} tracked companies: {b['advances']} up, {b['declines']} down, "
                         f"{b['unchanged']} unchanged; median move {F.pct(b['median_change'], 2, True)}.")
        for k, title in (("gainers", "Top gainers"), ("losers", "Top losers"), ("active", "Most active by turnover")):
            rows = mv.get(k) or []
            if rows:
                lines.append(f"{title}: " + "; ".join(f"{r['name']} ({r['symbol']}) {F.pct(r.get('change_pct'), 2, True)}" for r in rows))
        inds = sec.get("industries") or []
        if inds:
            lines.append("Sector moves (market-cap weighted, tracked companies): " +
                         "; ".join(f"{s['name']} {F.pct(s['avg_change'], 2, True)}" for s in inds))
        return "\n".join(lines)

    def t_latest_news(self, symbol: str | None = None, section: str | None = None, limit: int = 8) -> str:
        from .routes_research import news_data
        try:
            n = max(1, min(int(limit or 8), 15))
        except (TypeError, ValueError):
            n = 8
        if symbol:
            sym = self.resolve(symbol)
            d = news_data(section="company", symbol=sym, limit=n)
            what = f"news and disclosures for {sym}"
        else:
            sec = section if section in ("disclosures", "results", "economy", "regulation", "global") else "disclosures"
            d = news_data(section=sec, limit=n)
            what = d.get("section", sec)
        items = d.get("items") or []
        if not items:
            return f"No recent {what} found in EquityPilot's feeds."
        out = [f"Recent {what} (primary and established sources only; titles as published):"]
        for it in items[:n]:
            sid = self.src(f"News: {it['title'][:80]}", it.get("source") or "", "official" if it.get("tier") == "primary" else "third_party",
                           it.get("url"), str(it.get("published") or "")[:16])
            out.append(f"[{sid}] {str(it.get('published') or '')[:10]} - {it.get('source')}: {it['title']}"
                       + (f" - {it['summary'][:200]}" if it.get("summary") else ""))
        return "\n".join(out)

    def t_search_documents(self, query: str) -> str:
        if not self.doc_ids:
            return "The user has not selected any documents for this conversation."
        if not isinstance(query, str) or not query.strip():
            raise ToolError("query is required.")
        passages = rag.retrieve(query, self.doc_ids, k=6)
        if not passages:
            return "No passage in the selected documents matches this query."
        out = []
        for p in passages:
            sid = self.src(f"{p['filename']} - page {p['page']}", f"Uploaded document {p['filename']}", "official_upload",
                           excerpt=p["text"][:400])
            out.append(f"[{sid}] {p['filename']}, page {p['page']}:\n{p['text']}")
        return "\n\n".join(out)

    def t_learning_content(self, topic: str | None = None, question_id: str | None = None) -> str:
        if not (isinstance(topic, str) and topic.strip()) and not (isinstance(question_id, str) and question_id.strip()):
            raise ToolError("Give a topic or a question_id.")
        text = LRN.content_for(topic, question_id)
        if text.startswith(("No Learning Centre", "The Learning Centre has no")):
            return text
        sid = self.src(f"Learning Centre: {question_id or topic}", "EquityPilot Learning Centre", "calculated",
                       retrieved=f"content reviewed {CU.REVIEWED}")
        return f"[{sid}] " + text

    def t_explain_metric(self, term: str) -> str:
        if not isinstance(term, str) or not term.strip():
            raise ToolError("term is required.")
        t = term.strip()
        key = next((k for k in MG.GUIDE if k.replace("_", " ") == t.lower() or MG.GUIDE[k].get("name", "").lower() == t.lower()), None)
        if key:
            g = MG.GUIDE[key]
            sid = self.src(f"Metric guide: {g.get('name', key)}", "EquityPilot metric guide", "calculated")
            return f"[{sid}] {g.get('name', key)}\n" + "\n".join(f"{k}: {v}" for k, v in g.items() if k != "name" and isinstance(v, str))
        gk = find_term(t) or next((k for k in GLOSSARY if k.lower() == t.lower()), None)
        if gk:
            e = GLOSSARY[gk]
            sid = self.src(f"Glossary: {gk}", "EquityPilot glossary", "calculated")
            return f"[{sid}] {gk}\n" + "\n".join(f"{k}: {v}" for k, v in e.items() if isinstance(v, str))
        return f"'{term}' is not in EquityPilot's glossary; explain it from general finance knowledge and say so."


# ------------------------------------------------------------------ Claude agent
AGENT_PROMPT = """You are EquityPilot's research analyst for Indian listed equities. Your users range from first-time investors to analysts.

How to work:
- Use the tools to get facts. Never state a company figure, price, date or news item that did not come from a tool result.
- When the user names a company you do not have an exact symbol for, call find_company first. A company already selected on screen is given in the message.
- Pick the smallest set of tools that answers the question well. Call independent tools in parallel. Typical patterns:
  company question -> company_research (+ price_performance for returns/volatility questions);
  "compare A and B" -> compare_companies (+ company_research for depth);
  "which/find/top companies ..." -> screen_companies; "how is the market" -> market_overview; "news" -> latest_news.
- If a tool fails or data is missing, say exactly what is missing and where to find it (annual report, NSE/BSE filing). Never guess.

How to answer:
- Cite every fact with the tool-result ID in square brackets, e.g. [T3]. Cite each ID only where it supports the sentence.
- Start with **Answer**: 1-3 sentences that answer the question directly in plain English, with the key figure, its period and unit.
- Then only the sections that add something:
  **Key figures** - verified facts from tool results, each cited, with period (FY2026 = year to March 2026, or the quarter) and unit;
  **Calculations** - anything you computed yourself: formula, cited inputs and result (never present a calculated number as reported);
  **What it means** - your interpretation in simple English, clearly your analysis, jargon explained the first time;
  **Risks and limitations** - data gaps, third-party data, one-off items, mergers or anything that could mislead;
  **Sources and periods** - sources used, data timestamps, currency and units, consolidated/standalone basis when stated.
- Be concise by default (about 250 words or less); give more detail only when the user asks for it.
- Copy figures exactly as they appear in the tool results (same rounding and units); if you convert a unit, show the original too.
- Prefer compact markdown tables for comparisons. Use Indian conventions: ₹, crore, lakh, FY2026 = year ending March 2026.
- Explain jargon briefly the first time (e.g. "ROE - profit earned on shareholders' money").
- State data labels: prices are DELAYED or end-of-day unless the tool says real-time; SAMPLE companies are fictional; third-party
  data should be verified with filings.
- No buy/sell/hold calls, target prices or personal advice (SEBI rules for investment advisers). If asked, explain the evidence on both
  sides and what an investor might check, and say you cannot recommend.
- Intrinsic-value or DCF numbers are model estimates that depend on assumptions; never present them as exact.
- Learning questions (explain a concept more simply, a formula step by step, the difference between two concepts, practice
  questions, why a quiz answer is wrong): call learning_content and base the explanation on it. Label any numbers you make up as an
  illustrative example, not company data. Never invent formulas or regulatory rules; if the Learning Centre does not cover a point, say so.
Today is {today}."""


def _sse(ev: dict) -> str:
    return "data: " + json.dumps(ev, ensure_ascii=False, default=str) + "\n\n"


def _user_message(question: str, symbol: str | None, doc_names: list[str]) -> str:
    extra = []
    if symbol:
        extra.append(f"Company selected on screen: {symbol}")
    if doc_names:
        extra.append("Documents selected for this conversation (use search_documents): " + ", ".join(doc_names))
    return question + ("\n\n(" + "; ".join(extra) + ")" if extra else "")


def plan_prefetch(question: str, symbol: str | None, history: list[dict] | None = None) -> tuple[list[tuple[str, dict]], list[str]]:
    """Deterministic routing for predictable questions: the first tool calls the agent would make anyway, run before
    the first model call so a typical question is answered in one model turn instead of two. Returns (calls, notes)."""
    q = question.strip()
    named, notes = find_companies(q)
    if history and not named and (REFERS_BACK_RE.search(q) or len(re.findall(r"\w+", q)) <= 6):
        earlier = _conversation_companies(history)
        named = earlier[:6] if len(earlier) > 1 and COMPARATIVE_RE.search(q) else earlier[:1]
    intents = offline.detect_intents(q)
    if not named and symbol and not MARKET_RE.search(q) and not set(intents) <= {"concept"}:
        named = [symbol]
    if len(named) >= 2:
        return [("compare_companies", {"symbols": named[:6]})], notes
    if named:
        calls = [("company_research", {"symbol": named[0]})]
        if PERF_RE.search(q):
            calls.append(("price_performance", {"symbol": named[0]}))
        if NEWS_RE.search(q):
            calls.append(("latest_news", {"symbol": named[0], "limit": 8}))
        return calls, notes
    thresholds = parse_screen_filters(q)
    if thresholds:
        return [("screen_companies", {"filters": thresholds, "sort_by": thresholds[0]["metric"],
                                      "ascending": thresholds[0]["op"] in ("<", "<=")})], notes
    if MARKET_RE.search(q) and not SCREEN_RE.search(q):
        return [("market_overview", {})], notes
    if NEWS_RE.search(q):
        sec = "regulation" if re.search(r"\b(sebi|regulat)", q, re.I) else "economy" if re.search(r"\b(rbi|economy|inflation|repo)", q, re.I) else "disclosures"
        return [("latest_news", {"section": sec, "limit": 8})], notes
    learn = LRN.detect(q, history)
    if learn:
        return [("learning_content", {"question_id": learn["qid"]} if learn["intent"] == "quiz" else {"topic": q})], notes
    return [], notes


def _echo_content(content: list) -> tuple[list, list]:
    """Blocks to send back after a turn, and the tool calls to run. After a mid-output refusal fallback, thinking,
    tool-use and other model-internal blocks before the last `fallback` block belong to the declined attempt: they are
    not echoed or run (text blocks and the `fallback` block itself stay where they were)."""
    cut = max((i for i, b in enumerate(content) if getattr(b, "type", None) == "fallback"), default=-1)
    echo = [b for i, b in enumerate(content) if i > cut or getattr(b, "type", None) in ("text", "fallback")]
    live = [b for i, b in enumerate(content) if i > cut and getattr(b, "type", None) == "tool_use"]
    return echo, live


def _usage_parts(resp, model: str) -> list[tuple[str, int, int, int, int]]:
    """(model, input, output, cache read, cache write) per attempt - per-attempt usage when a fallback ran."""
    u = resp.usage
    parts = []
    for it in getattr(u, "iterations", None) or []:
        if getattr(it, "type", None) in ("message", "fallback_message"):
            parts.append((getattr(it, "model", None) or model, it.input_tokens or 0, it.output_tokens or 0,
                          getattr(it, "cache_read_input_tokens", 0) or 0, getattr(it, "cache_creation_input_tokens", 0) or 0))
    if not parts:
        parts.append((model, u.input_tokens or 0, u.output_tokens or 0, getattr(u, "cache_read_input_tokens", 0) or 0,
                      getattr(u, "cache_creation_input_tokens", 0) or 0))
    return parts


FALLBACK_MODELS = ("claude-opus", "claude-sonnet", "claude-fable")


def run_claude(question: str, history: list[dict], symbol: str | None, tb: ToolBox, model: str, api_key: str,
               doc_names: list[str], effort: str = "medium", prefetch: bool = True) -> Iterator[dict]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=180)
    system = [{"type": "text", "text": AGENT_PROMPT.replace("{today}", datetime.now(IST).strftime("%d %B %Y")),
               "cache_control": {"type": "ephemeral"}}]
    content = _user_message(question, symbol, doc_names)
    plan, notes = plan_prefetch(question, symbol, history) if prefetch else ([], [])
    if plan:                    # deterministic retrieval first, in parallel; the model calls tools only for what is missing
        for name, args in plan:
            yield {"type": "status", "text": tb.describe(name, args)}
        results = tb.run_many(plan)
        got = [res if res is not None else f"Error from {name}: {err}" for (name, _), (res, err) in zip(plan, results)]
        content += ("\n\nResearch data EquityPilot already retrieved for this question (cite the [T#] IDs; call tools only "
                    "for anything still missing):\n\n" + "\n\n".join(got)
                    + ("\n\nNotes on company names: " + " ".join(notes) if notes else ""))
    messages: list = [*history, {"role": "user", "content": content}]
    parts: list[tuple[str, int, int, int, int]] = []
    extra = {"thinking": {"type": "adaptive"}} if model.startswith(FALLBACK_MODELS) else {}
    if model.startswith(FALLBACK_MODELS):
        # server-side refusal fallback: if a safety classifier declines, the API re-runs the request on Anthropic's
        # recommended model for that refusal category, inside the same call
        extra.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    final_text, retries, note, served_by = "", 0, None, None
    turn = 0
    while turn < MAX_TURNS:
        turn += 1
        text_this_turn = []
        try:
            with client.beta.messages.stream(model=model, max_tokens=16000, system=system, tools=TOOLS, messages=messages,
                                             output_config={"effort": effort}, **extra) as stream:
                for event in stream:
                    if event.type == "text":
                        text_this_turn.append(event.text)
                        yield {"type": "delta", "text": event.text}
                resp = stream.get_final_message()
            retries = 0
        except anthropic.APIError as exc:        # explained to the user; the free offline engine answers instead
            raise P.ProviderError(P.explain_anthropic_error(exc)) from exc
        except ValueError:              # tool input the SDK could not parse at all: re-issue the turn (bounded)
            retries += 1
            if retries > 2:
                raise P.ProviderError("The model produced an unreadable tool request twice; please retry.")
            yield {"type": "reset"}
            turn -= 1
            continue
        parts += _usage_parts(resp, model)
        if getattr(resp, "model", None) and resp.model != model:
            served_by = resp.model
        echo, tool_uses = _echo_content(list(resp.content))
        if resp.stop_reason == "refusal":
            note = "The model declined part of this request."
            final_text = "".join(text_this_turn) or "The model declined to answer this request. Try rephrasing the question."
            break
        if not tool_uses:
            final_text = "".join(text_this_turn)
            if resp.stop_reason == "max_tokens":
                note = "Response truncated at the token limit."
            break
        if resp.stop_reason == "max_tokens":    # a truncated tool input parses as a partial object: never run it
            note = "The model ran out of room while requesting data."
            final_text = "".join(text_this_turn)
            break
        if text_this_turn:
            yield {"type": "interim", "text": "".join(text_this_turn)}
        messages.append({"role": "assistant", "content": echo})
        for b in tool_uses:
            yield {"type": "status", "text": tb.describe(b.name, b.input if isinstance(b.input, dict) else {})}
        outcomes = tb.run_many([(b.name, b.input) for b in tool_uses])     # parallel tool calls run at once
        results = []
        for b, (res, err) in zip(tool_uses, outcomes):
            if res is not None:
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": res})
            else:
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": f"Error: {err}", "is_error": True})
        messages.append({"role": "user", "content": results})
    else:
        note = "Stopped after the maximum number of research steps."
    cost = P.cost_of(parts)
    if served_by:
        note = ((note + " ") if note else "") + (f"Part of this answer was written by {served_by} after {model} declined the "
                                                  "request (automatic server-side fallback).")
    report = grounding_report(final_text, tb.context_text(), [x["ID"] for x in tb.sources])
    yield {"type": "final", "text": final_text, "meta": {
        "engine": model, "tokens": [sum(x[1] + x[3] + x[4] for x in parts), sum(x[2] for x in parts)], "cost_usd": cost,
        "grounding": report, "note": note, "steps": turn, "prefetched": len(plan)}}


# ------------------------------------------------------------------ free offline analyst: rule-based router over the same tools
MARKET_RE = re.compile(r"\b(market|markets|nifty|sensex|index|indices|gainers?|losers?|movers|breadth|sectors?|today'?s? (market|session)|bank ?nifty)\b", re.I)
SCREEN_RE = re.compile(r"\b(find|list|show me|screen|which (companies|stocks|shares)|top \d+|top (companies|stocks)|best|highest|lowest|cheapest|companies with|stocks with)\b", re.I)
COMPARE_RE = re.compile(r"\b(compare|comparison|versus|vs\.?|better than|against)\b", re.I)
NEWS_RE = re.compile(r"\b(news|headlines?|announcements?|disclosures?|latest on)\b", re.I)
PERF_RE = re.compile(r"\b(return|returns|performance|performed|52[- ]week|volatil|drawdown|price (history|movement|trend)|stock price)\b", re.I)
SCREEN_WORDS = [  # (pattern, sort metric, ascending, optional filter)
    (r"\bdividend", "dividend_yield", False, None),
    (r"\b(cheap|cheapest|low p/?e|lowest p/?e|undervalued|value stocks?)\b", "pe", True, {"metric": "pe", "op": ">", "value": 0}),
    (r"\b(debt[- ]free|zero debt|no debt)\b", "debt_to_equity", True, {"metric": "debt_to_equity", "op": "<=", "value": 0.1}),
    (r"\b(low debt|least debt|lowest debt)\b", "debt_to_equity", True, None),
    (r"\broce\b", "roce", False, None), (r"\b(roe|return on equity)\b", "roe", False, None),
    (r"\b(fast(est)? growing|high growth|growth|growing)\b", "revenue_cagr_3y", False, None),
    (r"\bprofit growth\b", "profit_cagr_3y", False, None),
    (r"\b(margin|profitable|most profitable)\b", "net_margin", False, None),
    (r"\b(quality|f-?score|piotroski)\b", "piotroski", False, None),
    (r"\b(largest|biggest|large ?cap|market cap)\b", "market_cap", False, None),
    (r"\b(gainers?|top performers? today|up today)\b", "day_change", False, None),
    (r"\b(losers?|down today|fell today)\b", "day_change", True, None),
]
INDUSTRY_WORDS = {"it": r"\b(it|tech|technology|software)\b", "banking": r"\b(bank|banks|banking)\b", "pharma": r"\b(pharma|drug|pharmaceutical)",
                  "automobiles": r"\b(auto|autos|automobile|car|cars)\b", "fmcg": r"\b(fmcg|consumer staples)\b",
                  "energy": r"\b(energy|power|oil|gas|utilities)\b", "metals": r"\b(metal|metals|steel|mining)\b",
                  "infrastructure": r"\b(infra|infrastructure|cement|construction)\b", "real-estate": r"\b(real estate|realty)\b",
                  "telecom": r"\btelecom", "financial-services": r"\b(nbfc|insurance|financial services)\b",
                  "chemicals": r"\b(chemical|chemicals|paints?)\b", "healthcare": r"\b(hospital|healthcare)\b",
                  "consumer-durables": r"\b(consumer durables?|appliances)\b", "agriculture": r"\b(agri|agriculture|fertili[sz]er)"}
_STOP = {"the", "and", "for", "are", "how", "what", "with", "has", "its", "this", "that", "best", "top", "today", "market", "news",
         "state", "national", "union", "general", "global", "great", "united", "new", "asian", "money", "price", "value", "growth",
         "india", "indian", "ltd", "limited", "company", "stock", "stocks", "share", "shares", "bank", "vs", "compare", "infra", "power",
         "energy", "life", "steel", "motors", "industries", "finance", "capital", "first", "auto", "it", "is", "of", "in", "on"}


Q_STOP = set("""a an the and or vs versus v with between of in on at for to from by about into over under than then
compare comparison compared against better best worse which what whats who how is are was were be been do does did
should would could can will may might tell me show give list find explain define meaning latest recent news today
todays now current currently price prices stock stocks share shares equity company companies firm firms business sector
sectors industry industries market markets index indices nifty sensex bank banks banking it tech oil gas power energy
steel cement auto autos pharma fmcg metal metals realty infra financial finance growth grow grown growing revenue sales
profit profits margin margins debt leverage valuation valued value cheap expensive pe pb roe roce ratio ratios risk risks
dividend dividends return returns performance performed perform high higher highest low lower lowest top bottom year years
month months week weeks day days quarter quarterly annual results result report reports analysis analyse analyze overview
summary summarise summarize snapshot buy sell hold invest investing investment good bad strong weak healthy health
balance sheet cash flow flows fcf cfo capex eps ebitda book my i we you its their this that these those there please also
idea fact vs. long term short future outlook why when where much many more most than doing done lately past fall fell rise
rose up down hello hi hey thanks thank state order impact effect news update updates""".split())


# Everyday words that also begin company names ("have" -> Havells, "indian" -> Indian Oil, "asian" -> Asian Paints,
# "united" -> United Spirits). On their own they may name a company only by an exact match of a symbol or brand
# ("titan", "reliance"), never by a prefix or a spelling correction. Inside a longer name ("Indian Oil") they still count.
COMMON_WORDS = set("""have has had having indian india national global general simple plain easy english hindi major minor
main key big small large huge good great nice fine latest current recent new old next last first second third final
happening going doing done said say tell show give make made take see look get got want need know think explain describe
detail details information info data annual results result update news story stories report reports summary summarise
summarize question answer help please could would should can will may might must also just only very much many more
most less least some any each every other another such same different own above below over under between across after
before during since until within without asian american us usa china chinese europe european japan japanese global world
foreign international united states union central western eastern northern southern north south east west premier prime
royal golden gold silver crude rupee dollar rate rates inflation repo budget tax gst ipo ipos fii fiis dii mutual fund funds
etf etfs bond bonds yield gdp economy policy election elections sector sectors stock market markets trade trading trader
investors investor money cash profit profits loss losses sales revenue income value price growth future outlook today
week month year quarter daily weekly monthly yearly people public private limited ltd india's indian's
cap caps capitalisation capitalization lakh lakhs crore crores cr mn bn billion million trillion percent times
roe roce eps ebitda ebit pat margin margins ratio ratios yield yields dividend dividends coverage turnover equity debt
leverage gearing payout cagr fcf cfo capex assets asset liabilities liquidity valuation multiple multiples score""".split())


def find_companies(question: str, limit: int = 6) -> tuple[list[str], list[str]]:
    """Companies named in a question - by name, brand, everyday name or symbol, with typo tolerance.

    Tries the longest word span first ('state bank of india' before 'state'). Spans containing common words must match
    a company name exactly; single brand words that match several companies ('Adani') pick the tracked / largest one
    and return a note listing the others. Returns (symbols, notes)."""
    text = question.replace("’", "'")
    toks = [re.sub(r"'s$", "", t.lower()).rstrip(".") for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9&'.-]*", text)]
    stop = [t in Q_STOP or t.isdigit() or len(t) < 2 for t in toks]
    found: list[str] = []
    notes: list[str] = []
    i = 0
    while i < len(toks) and len(found) < limit:
        hit = None
        for j in range(min(len(toks), i + 5), i, -1):
            span = toks[i:j]
            has_stop = any(stop[i:j])
            if j - i == 1 and has_stop:
                continue
            phrase = " ".join(span)
            res = S.resolve(phrase, 6, fuzzy=not has_stop)
            if not res:
                continue
            top = res[0]
            if has_stop or (j - i == 1 and span[0] in COMMON_WORDS):
                ok = top["score"] >= 98
            else:
                ok = top["score"] >= 80 and (top["score"] >= 95 or top.get("tracked") or (top.get("rank") or 99999) <= 500)
                if top.get("corrected") and top["score"] < 85:
                    ok = False
            if ok:
                hit = (top, res, phrase, j)
                break
        if not hit:
            i += 1
            continue
        top, res, phrase, j = hit
        if top["symbol"] not in found:
            found.append(top["symbol"])
            same = [r for r in res[1:] if r["score"] == top["score"]]
            if same and top["score"] <= 90:
                notes.append(f"“{phrase}” matches several companies, so I used **{top['name']}** (the largest tracked one). "
                             f"Others: {', '.join(r['name'] for r in same[:4])}. Name the exact company to switch.")
            elif top["score"] < 100 and len(res) > 1 and res[1].get("tracked") and res[1]["score"] >= top["score"] - 8 \
                    and res[1]["symbol"] != top["symbol"]:
                notes.append(f"“{phrase}” also matches **{res[1]['name']}** ({res[1]['symbol']}). I used **{top['name']}** "
                             f"({top['symbol']}); name the other company to switch.")
            if top.get("corrected"):
                notes.append(f"Read “{phrase}” as “{top['corrected']}”.")
        i = j
    return found, notes


_OPS = [(r">=|at least|not less than|no less than|minimum(?: of)?|min", ">="),
        (r"<=|at most|not more than|no more than|maximum(?: of)?|max|up to|upto", "<="),
        (r">|above|over|greater than|more than|higher than|exceed(?:ing|s)?|bigger than|better than", ">"),
        (r"<|below|under|less than|lower than|smaller than|beneath", "<")]
_OP_RE = "|".join(f"(?:{pat})" for pat, _ in _OPS)
_SCREEN_EXTRA = [(r"\b(3|three)[- ]?y(ea)?r revenue (growth|cagr)\b|\brevenue cagr\b|\bsales cagr\b", "revenue_cagr_3y"),
                 (r"\b(3|three)[- ]?y(ea)?r (profit|earnings) (growth|cagr)\b|\bprofit cagr\b", "profit_cagr_3y"),
                 (r"\bpiotroski\b|\bf-?score\b", "piotroski"), (r"\bshare price\b|\bprice\b", "price")]


def parse_screen_filters(question: str) -> list[dict]:
    """Numeric conditions in a question, e.g. 'ROE above 20%' -> {metric: roe, op: '>', value: 0.20}. Only metrics the
    screener holds are used. Percent metrics accept '20%' or '20' (= 20%); amounts default to crore ('1 lakh crore' too)."""
    ql = question.lower().replace("per cent", "%").replace("percent", "%")
    found: dict[str, dict] = {}
    where: dict[str, int] = {}
    for pat, key in _SCREEN_EXTRA + offline.METRIC_ALIASES:
        if key not in METRIC_COLUMNS or key in found:
            continue
        for m in re.finditer(pat, ql):
            tail = ql[m.end(): m.end() + 48]
            mm = re.match(rf"\s*(?:ratio|is|of|was|at|level|levels|a|an)?\s*({_OP_RE})\s*(?:of\s*)?(-?\d[\d,]*(?:\.\d+)?)\s*"
                          r"(%|x|times|lakh crore|lakh cr|l cr|crore|cr)?", tail)
            if not mm:
                continue
            op = next(o for pat2, o in _OPS if re.fullmatch(pat2, mm.group(1)))
            num = float(mm.group(2).replace(",", ""))
            unit, kind = mm.group(3) or "", METRIC_COLUMNS[key][1]
            if kind == "pct":
                value = num / 100 if (unit == "%" or abs(num) >= 1) else num
            elif kind == "cr":
                value = num * (1e12 if unit.startswith(("lakh", "l ")) else 1e7)
            else:
                value = num
            found[key] = {"metric": key, "op": op, "value": value}
            where[key] = m.start()
            break
    return sorted(found.values(), key=lambda f: where[f["metric"]])     # in the order the question states them


def mentioned_companies(question: str, limit: int = 6) -> list[str]:
    return find_companies(question, limit)[0]


def _snapshot_md(tb: "ToolBox", sym: str) -> str:
    """Key numbers at a glance for one company (from the universe table, or computed now)."""
    df = tb._metrics()
    row = df[df["symbol"] == sym]
    if row.empty:
        from equitypilot.analytics.screener import company_metrics
        r = company_metrics(sym)
    else:
        r = row.iloc[0].to_dict()
    keys = ["price", "day_change", "market_cap", "pe", "pb", "dividend_yield", "revenue_cagr_3y", "profit_cagr_3y", "net_margin",
            "roe", "roce", "debt_to_equity"]
    if r.get("is_financial"):
        keys = [k for k in keys if k not in ("roce", "debt_to_equity")]
    cells = [(_label(k), fmt_metric(k, r.get(k))) for k in keys if fmt_metric(k, r.get(k)) != "n/a"]
    if not cells:
        return ""
    sid = tb.src(f"{sym}: key numbers", "EquityPilot calculations from filings data (Yahoo Finance) and delayed quotes", "calculated",
                 retrieved=_now_ist())
    half = (len(cells) + 1) // 2
    rows = ["| Metric | Value | Metric | Value |", "|---|---|---|---|"]
    for k in range(half):
        a, b = cells[k], cells[k + half] if k + half < len(cells) else ("", "")
        rows.append(f"| {a[0]} | {a[1]} | {b[0]} | {b[1]} |")
    return f"**{r.get('name', sym)} ({sym}) at a glance** [{sid}]\n\n" + "\n".join(rows)


COMPARATIVE_RE = re.compile(r"\b(which|better|best|worse|higher|highest|lower|lowest|more|less|stronger|weaker|cheaper|"
                            r"costlier|bigger|smaller|faster|slower|vs\.?|versus|compare|comparison|between)\b", re.I)
REFERS_BACK_RE = re.compile(r"\b(it|its|it's|they|their|them|this company|that company|the company|this stock|that stock|"
                            r"the stock|same company|what about|how about|and (its|the|their))\b", re.I)


def _conversation_companies(history: list[dict] | None) -> list[str]:
    """Companies in the most recent earlier user message that named any."""
    for h in reversed(history or []):
        if h.get("role") == "user":
            found = find_companies(str(h.get("content") or ""))[0]
            if found:
                return found
    return []


def _learning_answer(q: str, history: list[dict] | None, tb: ToolBox) -> str | None:
    """Learning-mode answer from the curriculum, or None. Follow-ups such as 'explain it more simply' in a conversation about
    a company stay with the company, unless the question itself names a concept."""
    if "recommendation" in offline.detect_intents(q):
        return None
    if not CU.find_terms(q) and not LRN.QID_RE.search(q) and _conversation_companies(history):
        return None
    res = LRN.answer(q, history)
    if not res:
        return None
    text, lids = res
    for lid in lids:
        les = CU.LESSONS.get(lid)
        if les:
            tb.src(f"Learning Centre lesson: {les['title']}", "EquityPilot Learning Centre", "calculated",
                   retrieved=f"content reviewed {CU.REVIEWED}")
    return text


def _offline_answer(question: str, symbol: str | None, tb: ToolBox, history: list[dict] | None = None) -> tuple[str, list[str]]:
    """Returns (markdown answer, steps taken)."""
    q = question.strip()
    steps: list[str] = []
    named, notes = find_companies(q)
    if not named:
        learned = _learning_answer(q, history, tb)
        if learned:
            steps.append("Using the Learning Centre")
            return learned, steps
    short_follow_up = len(re.findall(r"\w+", q)) <= 6 and not MARKET_RE.search(q)
    if history and (REFERS_BACK_RE.search(q) or (not named and short_follow_up)):
        earlier = _conversation_companies(history)
        continuing = False
        if earlier and not named:
            named = earlier[:6] if len(earlier) > 1 and COMPARATIVE_RE.search(q) else earlier[:1]
            steps.append("Continuing with " + ", ".join(named) + " from the conversation")
            continuing = True
        elif earlier and COMPARE_RE.search(q) and earlier[0] not in named:
            named = [earlier[0]] + named           # "compare it with Infosys"
    else:
        continuing = False
    if named and not continuing:
        steps.append("Recognised " + ", ".join(named))
    syms = named or ([symbol] if symbol else [])
    lead = ("\n".join(f"> {n}" for n in notes) + "\n\n") if notes else ""
    if symbol and named and symbol not in named and COMPARE_RE.search(q):
        syms = [symbol] + named
    intents = offline.detect_intents(q)
    if "recommendation" in intents:
        ctx = build_context(syms[0], q) if syms and repo.get_company(syms[0]) else None
        return offline.answer(ctx, q), steps

    def call(name: str, **args) -> str:
        steps.append(tb.describe(name, args))
        return tb.run(name, args)

    # market-wide
    if not syms and MARKET_RE.search(q) and not SCREEN_RE.search(q.replace("top gainers", "").replace("top losers", "")):
        txt = call("market_overview")
        return _market_md(txt), steps
    # comparison
    if len(syms) >= 2:
        try:
            txt = call("compare_companies", symbols=syms[:6])
        except ToolError as exc:
            return lead + f"I could not compare these companies: {exc}", steps
        direct = _compare_direct(tb, q)
        return lead + direct + ("**Comparison** (latest fiscal year; day change is today's; rule-based summary - not a recommendation)\n\n"
                + txt.split("\n", 1)[1] + "\n\n" + _compare_reading(tb, syms[:6])
                + f"\n\nSource: [{tb.sources[-1]['ID']}] {tb.sources[-1]['Source']}. Open **Compare** for charts and more metrics."), steps
    # screens (need a list-like question: "top IT companies by ROE", "debt-free stocks", "highest dividend yield")
    ind_hit = next((iid for iid, pat in INDUSTRY_WORDS.items() if re.search(pat, q, re.I)), None)
    listy = re.search(r"\b(compan|stocks?\b|shares\b|banks\b|firms|names|dividend|gainers?|losers?)", q, re.I) or ind_hit
    thresholds = parse_screen_filters(q) if not syms else []
    if not syms and ((SCREEN_RE.search(q) and listy) or thresholds):
        sort_by, asc, filt = "market_cap", False, []
        if thresholds:                       # sort by the first condition, in the direction the user asked for
            filt = thresholds
            sort_by, asc = thresholds[0]["metric"], thresholds[0]["op"] in ("<", "<=")
        else:
            for pat, key, a, f in SCREEN_WORDS:
                if re.search(pat, q, re.I):
                    sort_by, asc = key, a
                    if f:
                        filt.append(f)
                    break
        ind = ind_hit
        m = re.search(r"\btop (\d{1,2})\b", q, re.I)
        txt = call("screen_companies", filters=filt, industry=ind, sort_by=sort_by, ascending=asc, limit=int(m.group(1)) if m else 10)
        return ("**Screen result** - " + txt.split("] ", 1)[1] + "\n\nOpen the **Screener** to change the filters, or ask about any company in the list."), steps
    # news without a company
    if not syms and NEWS_RE.search(q):
        sec = "regulation" if re.search(r"\b(sebi|regulat)", q, re.I) else "economy" if re.search(r"\b(rbi|economy|inflation|repo)", q, re.I) else "disclosures"
        txt = call("latest_news", section=sec, limit=8)
        return "**Latest headlines**\n\n" + "\n".join(f"- {line}" for line in txt.split("\n")[1:]) + \
            "\n\nHeadlines are listed as published by the source; open each link for the full text.", steps
    # single company
    if syms:
        sym = syms[0]
        try:
            tb.ensure_tracked(sym)
        except ToolError as exc:
            return f"I could not load data for {sym}: {exc}", steps
        if NEWS_RE.search(q) and set(intents) <= {"news", "overview", "concept"}:   # only news was asked for
            try:
                txt = call("latest_news", symbol=sym, limit=8)
            except ToolError as exc:
                return lead + f"I could not read news for {sym}: {exc}", steps
            name = (repo.get_company(sym) or {}).get("name", sym)
            items = txt.split("\n")[1:]
            if not items:
                return lead + (f"**Answer**\nNo recent exchange filings or verified headlines for {name} are stored in "
                               "EquityPilot. Check the company's announcements on NSE/BSE."), steps
            return lead + (f"**Answer**\nLatest exchange filings and headlines for **{name}** (titles exactly as published; "
                           "exchange filings are official, media reports are secondary):\n\n" + "\n".join(f"- {x}" for x in items)
                           + "\n\nOpen each link for the full text - EquityPilot does not summarise articles it has not retrieved."), steps
        steps.append(tb.describe("company_research", {"symbol": sym}))
        ctx = build_context(sym, q)
        if ctx is None:
            return f"No data is available for {sym}.", steps
        for b in ctx.blocks:            # register the context blocks as sources (same IDs the answer cites: S1..)
            tb.texts.append(b.text)
        body = offline.answer(ctx, q)
        if "overview" in intents or "valuation" in intents:
            snap = _snapshot_md(tb, sym)
            if snap:
                if body.startswith("**Answer**") and "\n\n**" in body:      # direct answer first, then the table
                    head, rest = body.split("\n\n**", 1)
                    body = head + "\n\n" + snap + "\n\n**" + rest
                else:
                    body = snap + "\n\n" + body
        body = lead + body
        extra = ""
        if PERF_RE.search(q):
            try:
                extra = "\n\n**Price performance**\n" + "\n".join(call("price_performance", symbol=sym).split("\n")[1:])
            except ToolError as exc:
                extra = f"\n\nPrice history unavailable: {exc}"
        if NEWS_RE.search(q) and "Recent headlines" not in body:
            try:
                extra += "\n\n**Recent news**\n" + "\n".join(f"- {x}" for x in call("latest_news", symbol=sym, limit=6).split("\n")[1:])
            except ToolError:
                pass
        tb.ctx_sources = ctx.source_list().to_dict("records")   # type: ignore[attr-defined]
        return body + extra, steps
    # documents asked for but none selected
    if "document" in intents and not tb.doc_ids:
        return ("**No document is selected.** Upload the report on the **Documents** page, then tick it in the document picker "
                "next to the question box. I can then summarise it or answer questions with quotes and page numbers."), steps
    # concept or nothing matched
    a = offline.answer(None, q)
    term = CU.find_term(q)
    if term and not a.startswith("Select a company first"):
        more = LRN.lesson_line([term])
        if more:
            a += "\n\n" + more
    if a.startswith("Select a company first"):
        a = (HELP_PREFIX + "\n- **Any company** - e.g. *How has Infosys grown?*, *Is Tata Motors' debt high?*\n"
             "- **Comparisons** - *Compare TCS and Infosys*\n- **The market** - *How is the market today?*, *Top gainers*\n"
             "- **Screens** - *Top 10 IT companies by ROE*, *Debt-free companies*, *Highest dividend yield*\n"
             "- **News** - *Latest RBI news*, *News on Reliance*\n- **Concepts** - *What is ROCE?*, *Explain P/E*")
    return a, steps


def _market_md(txt: str) -> str:
    lines = txt.split("\n")
    head = lines[0].split("] ", 1)[1]
    sid = lines[0].split("]", 1)[0].lstrip("[")
    idx = [x for x in lines if x.startswith("- ")]
    rest = [x for x in lines[1:] if not x.startswith("- ") and not x.startswith("Indices")]
    nifty = next((x for x in idx if x.startswith("- NIFTY 50:")), None)
    summary = ""
    if nifty:
        m = re.search(r"NIFTY 50: ([\d,\.]+), ([+-][\d\.]+%) today", nifty)
        if m:
            up = m.group(2).startswith("+")
            summary = f"NIFTY 50 is **{'up' if up else 'down'} {m.group(2).lstrip('+-')}** at {m.group(1)} [{sid}]. "
    indices = "\n".join(idx[:8]) or ("Index values are not available right now (the market-data provider could not be "
                                      "reached, or EquityPilot is running offline).")
    return ("**Summary**\n" + summary + head + "\n\n**Indices**\n" + indices + "\n\n**Breadth, movers and sectors**\n"
            + "\n".join(f"- {x}" for x in rest) +
            f"\n\n**Limitations**\n- Values are delayed (not real-time) unless marked LIVE. Breadth and movers cover the companies "
            f"EquityPilot tracks, not the whole exchange. [{sid}]")


_LOWER_IS_BETTER = {"pe", "pb", "ev_ebitda", "debt_to_equity"}


def _compare_direct(tb: ToolBox, q: str) -> str:
    """'Which has better margins?' -> the leader on the metric asked about, with the values (from the table above)."""
    df = getattr(tb, "last_compare", None)
    if df is None or df.empty:
        return ""
    key = offline.asked_metric(q)
    keys = [key] if key in getattr(tb, "COMPARE_KEYS", []) else (["net_margin", "ebitda_margin"] if re.search(r"\bmargins?\b", q, re.I) else [])
    sid = tb.sources[-1]["ID"] if tb.sources else "T1"
    lines = []
    for k in keys:
        col = pd.to_numeric(df.get(k), errors="coerce").dropna() if k in df.columns else pd.Series(dtype=float)
        if k in ("debt_to_equity", "ev_ebitda") and "is_financial" in df.columns:
            col = col[~df.loc[col.index, "is_financial"].astype(bool)]
        if k == "pe":
            col = col[col > 0]
        if len(col) < 2:
            missing = [s_.rsplit(".", 1)[0] for s_ in df.index if s_ not in col.index]
            if len(col) == 1 and missing:
                only = col.index[0]
                lines.append(f"{_label(k)} is available only for {only.rsplit('.', 1)[0]} ({fmt_metric(k, col.iloc[0])}); it cannot be "
                             f"calculated for {', '.join(missing)} from the stored data (for example, statements in another "
                             f"currency or a missing input) [{sid}].")
            continue
        best = col.idxmin() if k in _LOWER_IS_BETTER else col.idxmax()
        word = "Lower" if k in _LOWER_IS_BETTER else "Higher"
        lines.append(f"{word} {_label(k)}: **{df.at[best, 'name']}** - " +
                     ", ".join(f"{s_.rsplit('.', 1)[0]} {fmt_metric(k, v)}" for s_, v in col.items()) + f" [{sid}].")
    return ("**Answer**\n" + "\n".join(lines) + "\n\n") if lines else ""


def _compare_reading(tb: ToolBox, syms: list[str]) -> str:
    df = getattr(tb, "last_compare", None)
    if df is None:
        df = tb._metrics()
        df = df[df["symbol"].isin(syms)].set_index("symbol")
    if df.empty:
        return ""
    out = ["**What stands out** (automated reading of the table above)"]
    for key, better, word in (("roe", "high", "return on equity"), ("revenue_cagr_3y", "high", "3-year revenue growth"),
                              ("net_margin", "high", "net margin"), ("debt_to_equity", "low", "debt to equity"),
                              ("pe", "low", "P/E (cheapest on earnings)")):
        col = pd.to_numeric(df.get(key), errors="coerce").dropna()
        if key in ("debt_to_equity",) and "is_financial" in df.columns:
            col = col[~df.loc[col.index, "is_financial"].astype(bool)]
        if key == "pe":
            col = col[col > 0]
        if len(col) >= 2:
            s = col.idxmax() if better == "high" else col.idxmin()
            out.append(f"- Best {word}: **{df.at[s, 'name']}** ({fmt_metric(key, col[s])})")
    out.append("- A lower P/E can mean cheaper *or* lower expected growth; compare it with growth and return ratios together.")
    return "\n".join(out)


HELP_PREFIX = "I can help with:"


SUMMARY_RE = re.compile(r"\b(summar(y|ise|ize)|key (points|takeaways|highlights)|highlights|main points|overview of (the|this) (report|document))\b", re.I)


def _document_summary(doc_ids: list[int], tb: "ToolBox") -> str:
    """Extractive summary of the selected documents: the sentences with the most financial content, quoted verbatim
    with page numbers. Scanned PDFs (no text layer) are reported, never summarised from nothing."""
    from equitypilot.data import uploads as U
    parts = []
    for d in doc_ids:
        doc = U.get_document(d)
        if not doc:
            continue
        pages = U.text_to_pages(doc.get("text") or "")
        if sum(len(pg["text"].strip()) for pg in pages) < 200:
            parts.append(f"**{doc['filename']}** has no readable text layer (probably a scanned PDF). OCR is not available in "
                         "EquityPilot, so it cannot be summarised; open the original or upload a text-based PDF.")
            continue
        sents = offline.summarise_document(pages, n=10)
        if not sents:
            parts.append(f"**{doc['filename']}**: no sentences with financial content were found to quote.")
            continue
        sid = tb.src(f"{doc['filename']} - summary passages", f"Uploaded document {doc['filename']}", "official_upload")
        parts.append(f"**Key passages from {doc['filename']}** (quoted verbatim; most financial content first) [{sid}]\n"
                     + "\n".join(f"- \"{t}\" — *p. {pg}*" for pg, t in sents))
    return "\n\n".join(parts)


def run_offline(question: str, symbol: str | None, tb: ToolBox, history: list[dict] | None = None) -> Iterator[dict]:
    answer, steps = _offline_answer(question, symbol, tb, history)
    if tb.doc_ids and SUMMARY_RE.search(question):
        steps.append("Summarising your documents")
        summary = _document_summary(tb.doc_ids, tb)
        if answer.startswith(HELP_PREFIX) or answer.startswith("**No document is selected"):
            answer = ""
        answer = (summary + ("\n\n" + answer if answer else "")) if summary else answer
    elif tb.doc_ids:
        steps.append("Searching your documents")
        passages = rag.retrieve(question, tb.doc_ids, k=6)
        sents = rag.best_sentences(passages, question) if passages else []
        if answer.startswith(HELP_PREFIX) or answer.startswith("**No document is selected"):
            answer = ""
        if sents:
            ids: dict[tuple, str] = {}
            for p in passages:
                key = (p["filename"], p["page"])
                if key not in ids:
                    ids[key] = tb.src(f"{p['filename']} - page {p['page']}", f"Uploaded document {p['filename']}",
                                      "official_upload", excerpt=p["text"][:400])
            quotes = "\n".join(f"- \"{s['sentence']}\" — *{s['filename']}, p. {s['page']}*"
                               + (f" [{ids[(s['filename'], s['page'])]}]" if (s["filename"], s["page"]) in ids else "") for s in sents)
            answer = (answer + "\n\n" if answer else "") + "**From your documents (quoted verbatim)**\n" + quotes
        else:
            answer = (answer + "\n\n" if answer else "") + "No passage in the selected documents answers this question."
    for s in steps:
        yield {"type": "status", "text": s}
    ctx_sources = getattr(tb, "ctx_sources", None)
    if ctx_sources:                     # single-company answers cite the context's own S-IDs
        tb.sources = ctx_sources + [s for s in tb.sources]
    yield {"type": "final", "text": answer, "meta": {"engine": "offline analyst (rule-based)", "grounding": None, "steps": len(steps)}}


def gather_for_local_model(question: str, symbol: str | None, tb: ToolBox, history: list[dict] | None = None) -> str:
    """Context for a local model (Ollama): the data the offline router would use, as cited blocks."""
    _offline_answer(question, symbol, tb, history)
    named = mentioned_companies(question) or ([symbol] if symbol else [])
    if named and not any(s["Content"].startswith(named[0]) for s in tb.sources):
        try:
            tb.run("company_research", {"symbol": named[0]})
        except ToolError:
            pass
    return tb.context_text()


def stream_answer(question: str, history: list[dict], symbol: str | None, doc_ids: list[int], uid: int, settings: dict,
                  api_key: str | None, doc_names: list[str]) -> Iterator[str]:
    """Server-sent events: status (tool steps), delta (answer text), interim (text before a tool call), final."""
    engine = settings.get("provider", "offline")
    tb = ToolBox(uid, doc_ids)
    started = time.time()
    final: dict | None = None
    try:
        if engine == "anthropic":
            if not api_key or not settings.get("consent"):
                raise P.ProviderError("Claude API is not configured (key + billing acknowledgement in Settings).")
            for ev in run_claude(question, history, symbol, tb, settings.get("model", "claude-opus-5-5"), api_key, doc_names,
                                 effort=settings.get("effort") or "medium"):
                if ev["type"] == "final":
                    final = ev
                else:
                    yield _sse(ev)
        elif engine == "ollama":
            yield _sse({"type": "status", "text": "Gathering data for the local model"})
            ctx_text = gather_for_local_model(question, symbol, tb, history)
            res = P.ask_ollama(ctx_text, history, question,
                               settings.get("ollama_model", "llama3.1:8b"), settings.get("ollama_host", "http://localhost:11434"))
            final = {"type": "final", "text": res.text, "meta": {"engine": res.model, "tokens": [res.input_tokens, res.output_tokens],
                                                                  "grounding": grounding_report(res.text, ctx_text, [x["ID"] for x in tb.sources])}}
        else:
            for ev in run_offline(question, symbol, tb, history):
                if ev["type"] == "final":
                    final = ev
                else:
                    yield _sse(ev)
    except P.ProviderError as exc:
        tb = ToolBox(uid, doc_ids)
        for ev in run_offline(question, symbol, tb, history):
            if ev["type"] == "final":
                final = ev
                final["meta"]["engine"] = "offline analyst (fallback)"
                final["meta"]["warning"] = str(exc)
    except Exception as exc:
        log.exception("assistant failed")
        name = type(exc).__name__
        msg = "The AI service could not be reached or returned an error." if "anthropic" in type(exc).__module__ else \
            "Something went wrong while researching this question."
        final = {"type": "final", "text": f"**{msg}** ({name}). Please try again.", "meta": {"engine": engine, "warning": name}}
    final = final or {"type": "final", "text": "", "meta": {}}
    final["meta"]["seconds"] = round(time.time() - started, 1)
    final["sources"] = tb.sources
    yield _sse(final)
