"""Reusable UI building blocks shared by all pages."""
from __future__ import annotations

import html
from typing import Iterable

import pandas as pd
import streamlit as st

from .. import config
from .. import formatting as F
from ..data import repository as repo
from ..data.universe import normalise_symbol

BASIS_TEXT = {
    "consolidated": "Consolidated",
    "standalone": "Standalone",
    "unspecified": "Basis not stated by provider (Yahoo generally reports consolidated figures - verify with filings)",
}


def esc(x) -> str:
    return html.escape(str(x)) if x is not None else ""


# ------------------------------------------------------------------ headers & badges
def badge(data_type: str) -> str:
    label, tip = config.DATA_TYPES.get(data_type, (data_type.upper(), ""))
    return f'<span class="ep-badge ep-b-{esc(data_type)}" title="{esc(tip)}">{esc(label)}</span>'


def badges(data_types: Iterable[str]) -> str:
    return "".join(badge(t) for t in dict.fromkeys(data_types) if t)


def page_header(title: str, subtitle: str | None = None, data_types: Iterable[str] = ()) -> None:
    b = badges(data_types)
    st.html(f'<div class="ep-header"><h1>{esc(title)} {b}</h1>'
            + (f'<div class="ep-sub">{esc(subtitle)}</div>' if subtitle else "") + "</div>")


def note(text: str, kind: str = "info", allow_html: bool = False) -> None:
    body = text if allow_html else esc(text)
    st.html(f'<div class="ep-note {kind}">{body}</div>')


def sample_notice() -> None:
    note("<b>SAMPLE DATA.</b> This is a fictional company created for demonstration and testing. "
         "Its numbers are generated and do not describe any real business.", "sample", allow_html=True)


def empty_state(title: str, body: str) -> None:
    st.html(f'<div class="ep-empty"><div class="t">{esc(title)}</div><div>{esc(body)}</div></div>')


def formula(text: str) -> None:
    st.html(f'<div class="ep-formula">{esc(text)}</div>')


# ------------------------------------------------------------------ KPIs
def kpis(items: list[dict]) -> None:
    """items: {label, value, delta (str, optional), sign (+1/-1/0 for colour), help (tooltip)}"""
    cells = []
    for it in items:
        tip = f' <span class="i" title="{esc(it["help"])}">ⓘ</span>' if it.get("help") else ""
        sign = it.get("sign")
        cls = "pos" if sign and sign > 0 else "neg" if sign and sign < 0 else ""
        delta = f'<div class="d {cls}">{esc(it["delta"])}</div>' if it.get("delta") else ""
        cells.append(f'<div class="ep-kpi"><div class="l" title="{esc(it["label"])}">{esc(it["label"])}{tip}</div>'
                     f'<div class="v" title="{esc(it["value"])}">{esc(it["value"])}</div>{delta}</div>')
    st.html(f'<div class="ep-kpis">{"".join(cells)}</div>')


# ------------------------------------------------------------------ provenance
def source_footer(sources: Iterable[str] = (), fetched_at=None, period: str | None = None,
                  basis: str | None = None, urls: Iterable[str] = (), extra: str | None = None) -> None:
    parts = []
    srcs = [s for s in dict.fromkeys(sources) if s]
    if srcs:
        parts.append("<b>Source:</b> " + "; ".join(esc(s) for s in srcs))
    if period:
        parts.append(f"<b>Period:</b> {esc(period)}")
    if basis:
        parts.append(f"<b>Basis:</b> {esc(BASIS_TEXT.get(basis, basis))}")
    if fetched_at is not None and not (isinstance(fetched_at, float) and pd.isna(fetched_at)):
        parts.append(f"<b>Retrieved:</b> {F.ist(fetched_at)}")
    links = [u for u in dict.fromkeys(urls) if u]
    if links:
        parts.append(" ".join(f'<a href="{esc(u)}" target="_blank" rel="noopener">link {i + 1}</a>'
                              for i, u in enumerate(links[:4])))
    if extra:
        parts.append(esc(extra))
    if parts:
        st.html('<div class="ep-source">' + " &nbsp;·&nbsp; ".join(parts) + "</div>")


# ------------------------------------------------------------------ tables
def fin_table(df: pd.DataFrame, bold: Iterable[str] = (), sections: Iterable[str] = (),
              negative_red: bool = True) -> None:
    """Render a pre-formatted (string) DataFrame as a readable financial table.
    Row labels are the index; rows listed in `sections` are rendered as section headers."""
    bold, sections = set(bold), set(sections)
    head = "<tr><th>" + esc(df.index.name or "") + "</th>" + "".join(f"<th>{esc(c)}</th>" for c in df.columns) + "</tr>"
    body = []
    for idx, row in df.iterrows():
        if idx in sections:
            body.append(f'<tr class="section"><td colspan="{len(df.columns) + 1}">{esc(idx)}</td></tr>')
            continue
        cls = ' class="bold"' if idx in bold else ""
        tds = []
        for v in row:
            s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
            neg = negative_red and (s.startswith("-") or s.startswith("₹-") or s.startswith("(")) and s != F.MISSING
            tds.append(f'<td{" class=neg" if neg else ""}>{esc(s) if s else F.MISSING}</td>')
        body.append(f"<tr{cls}><td>{esc(idx)}</td>{''.join(tds)}</tr>")
    st.html(f'<div class="ep-table-wrap"><table class="ep-table"><thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def download_csv(df: pd.DataFrame, filename: str, label: str = "Download CSV", key: str | None = None) -> None:
    st.download_button(label, df.to_csv(index=True).encode("utf-8"), file_name=filename, mime="text/csv",
                       icon=":material/download:", key=key)


# ------------------------------------------------------------------ company context
def current_symbol() -> str | None:
    if "symbol" not in st.session_state:
        qp = st.query_params.get("symbol")
        st.session_state.symbol = qp if qp else None
    return st.session_state.symbol


def set_symbol(symbol: str | None) -> None:
    st.session_state.symbol = symbol
    if symbol:
        st.query_params["symbol"] = symbol
    elif "symbol" in st.query_params:
        del st.query_params["symbol"]


def company_label(row) -> str:
    tag = " · SAMPLE" if row.get("is_sample") else ""
    return f"{row['name']} ({row['symbol']}){tag}"


def sidebar_company_picker() -> None:
    """Global company selector shared by every research page."""
    comps = repo.list_companies()
    sym = current_symbol()
    with st.sidebar:
        st.caption("ACTIVE COMPANY")
        if comps.empty:
            st.caption("No companies loaded yet.")
            return
        options = comps["symbol"].tolist()
        labels = {r["symbol"]: company_label(r) for _, r in comps.iterrows()}
        idx = options.index(sym) if sym in options else None
        choice = st.selectbox("Active company", options, index=idx, format_func=lambda s: labels.get(s, s),
                              placeholder="Search company…", label_visibility="collapsed", key="sb_company")
        if choice != sym:
            set_symbol(choice)
            st.rerun()


def require_company() -> tuple[dict, dict | None] | None:
    """Return (company, quote) for the active company, or render an empty state and return None."""
    sym = current_symbol()
    company = repo.get_company(sym) if sym else None
    if not company:
        empty_state("No company selected",
                    "Choose a company from the sidebar, or search on the Dashboard to add any NSE/BSE company.")
        st.page_link("views/dashboard.py", label="Go to Dashboard", icon=":material/dashboard:")
        return None
    msg = repo.refresh_quote_if_stale(sym)
    if msg and not msg[0]:
        st.toast(f"Live refresh failed - showing cached data. {msg[1]}", icon=":material/cloud_off:")
    return company, repo.get_quote(sym)


def company_header(company: dict, quote: dict | None) -> None:
    sample = bool(company.get("is_sample"))
    meta = " · ".join(x for x in [company["symbol"], company.get("exchange"), company.get("sector"),
                                  company.get("industry")] if x)
    right = ""
    if quote and not F.is_missing(quote.get("price")):
        price, prev = quote["price"], quote.get("prev_close")
        chg = (price - prev) if prev else None
        cls = "pos" if chg and chg > 0 else "neg" if chg and chg < 0 else ""
        chg_txt = f"{'+' if chg >= 0 else ''}{chg:,.2f} ({chg / prev * 100:+.2f}%)" if chg is not None else ""
        dtype = quote.get("data_type") or "delayed"
        right = (f'<div><div class="px">{F.inr(price)}</div><div class="chg {cls}">{chg_txt}</div>'
                 f'<div class="asof">{badge(dtype)} Price as of {F.ist(quote.get("as_of") or quote.get("fetched_at"))}</div></div>')
    st.html(f'<div class="ep-co"><div><div class="name">{esc(company["name"])} '
            f'{badge("sample") if sample else ""}</div><div class="meta">{esc(meta)}</div></div>{right}</div>')
    if sample:
        sample_notice()


def symbol_input_add(key: str = "add_symbol") -> None:
    """Search box that adds any NSE/BSE company by symbol via the data provider."""
    with st.form(key, clear_on_submit=False, border=False):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        raw = c1.text_input("Add a company by NSE symbol or BSE code",
                            placeholder="e.g. INFY, NSE:TATAPOWER, 500325",
                            help="NSE symbols get the '.NS' suffix automatically; numeric BSE scrip codes get '.BO'.")
        go = c2.form_submit_button("Add & open", width="stretch", type="primary")
    if go and raw.strip():
        if config.OFFLINE:
            st.error("Offline mode is on - adding real companies needs internet access.")
            return
        with st.spinner(f"Fetching {normalise_symbol(raw)} from Yahoo Finance…"):
            ok, msg, sym = repo.add_company(raw)
        if ok:
            set_symbol(sym)
            st.success(msg)
            st.rerun()
        else:
            st.error(f"Could not add '{raw}': {msg}")
