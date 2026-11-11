"""Company Research: profile, business model, segments, shareholding, peers, official sources."""
import pandas as pd
import streamlit as st

from equitypilot import config, db
from equitypilot import formatting as F
from equitypilot.analytics import ratios as R
from equitypilot.analytics import valuation as V
from equitypilot.analytics.screener import company_metrics
from equitypilot.data import repository as repo
from equitypilot.data.official import official_links
from equitypilot.ui import charts as C
from equitypilot.ui import components as ui

ctx = ui.require_company()
if not ctx:
    st.stop()
company, quote = ctx
sym = company["symbol"]
ui.page_header("Company Research", "Profile, business model, segments, ownership and peers")
ui.company_header(company, quote)

fd = repo.get_financials(sym)
fq = repo.get_financials(sym, "quarterly", basis=fd.basis if not fd.empty else None, auto_refresh=False)
snap = V.market_snapshot(quote, fd, fq)
rt = R.compute_ratios(fd) if not fd.empty else pd.DataFrame()
fin = R.is_financial(company)

b1, b2, b3, _ = st.columns([1.2, 1.2, 1.2, 3])
in_wl = sym in repo.get_watchlist()
if b1.button("Remove from watchlist" if in_wl else "Add to watchlist", icon=":material/bookmark:", width="stretch"):
    repo.remove_from_watchlist(sym) if in_wl else repo.add_to_watchlist(sym)
    st.rerun()
if not company.get("is_sample") and b2.button("Refresh data", icon=":material/refresh:", width="stretch",
                                              disabled=config.OFFLINE):
    with st.spinner("Refreshing from Yahoo Finance…"):
        msgs = [repo.refresh_company(sym), repo.refresh_financials(sym), repo.refresh_prices(sym)]
    for ok, m in msgs:
        (st.success if ok else st.warning)(m)
    db.log_activity("Refreshed company", sym)
b3.page_link("views/financials.py", label="Financials →", icon=":material/table_chart:")

tab_over, tab_biz, tab_share, tab_peers, tab_src = st.tabs(
    ["Overview", "Business & segments", "Shareholding", "Peers", "Official sources"])

# ------------------------------------------------------------------ overview
with tab_over:
    latest = rt.iloc[:, -1] if not rt.empty else pd.Series(dtype=float)
    fy = F.fiscal_label(fd.periods[-1]) if not fd.empty else "—"
    ui.kpis([
        {"label": "Market cap", "value": F.big_inr(snap.get("market_cap")), "help": "Price × shares outstanding (provider figure)."},
        {"label": "P/E", "value": F.mult(snap.get("pe")), "delta": snap["basis"].get("earnings") or "",
         "help": V.MULTIPLE_FORMULAS["pe"]},
        {"label": "P/B", "value": F.mult(snap.get("pb")), "help": V.MULTIPLE_FORMULAS["pb"]},
        {"label": "EV/EBITDA", "value": "n.m." if fin else F.mult(snap.get("ev_ebitda")),
         "help": "Not meaningful for banks/financials." if fin else V.MULTIPLE_FORMULAS["ev_ebitda"]},
        {"label": f"ROE ({fy})", "value": F.pct(latest.get("roe")), "help": R.RATIOS["roe"].formula},
        {"label": f"ROCE ({fy})", "value": F.pct(latest.get("roce")), "help": R.RATIOS["roce"].formula},
        {"label": f"Debt/Equity ({fy})", "value": "n.m." if fin else F.mult(latest.get("debt_to_equity"), 2),
         "help": R.RATIOS["debt_to_equity"].formula},
        {"label": "Dividend yield", "value": F.pct(snap.get("dividend_yield")), "help": V.MULTIPLE_FORMULAS["dividend_yield"]},
    ])
    if fin:
        ui.note("This is a financial-sector company. EV/EBITDA, debt/equity and current ratio are not meaningful "
                "for lenders, whose borrowings are their raw material. Focus on P/B, ROE and asset quality "
                "(GNPA/NNPA, CASA, capital adequacy - available in the company's filings).", "info")

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("##### Revenue and net profit")
        if fd.empty:
            ui.empty_state("No financial statements", "The provider returned none. Upload statements in the Data Manager.")
        else:
            div, unit = F.amount_unit(fd.currency)
            chart = pd.DataFrame({"Revenue": fd.get("revenue") / div, "Net profit": fd.get("net_income") / div})
            chart.index = [F.fiscal_label(p) for p in chart.index]
            st.plotly_chart(C.grouped_bars(chart, f"In {unit}", height=300), width="stretch", config=C.config())
            ui.source_footer(fd.sources, fd.fetched_at, basis=fd.basis, urls=fd.source_urls)
    with right:
        st.markdown("##### Business description")
        desc = company.get("description")
        st.write(desc if desc else "No description available from the provider.")
        facts = {"Sector": company.get("sector"), "Industry": company.get("industry"),
                 "Exchange": company.get("exchange"), "ISIN": company.get("isin"),
                 "Employees": f"{int(company['employees']):,}" if company.get("employees") and not pd.isna(company.get("employees")) else None,
                 "Website": company.get("website")}
        st.html("<table class='ep-table' style='border:1px solid #E3E8F0;border-radius:8px'>" + "".join(
            f"<tr><td>{k}</td><td style='text-align:left'>{ui.esc(v) if v else F.MISSING}</td></tr>" for k, v in facts.items())
            + "</table>")
        ui.source_footer([company.get("source")], company.get("fetched_at"), urls=[company.get("source_url")])

# ------------------------------------------------------------------ business & segments
with tab_biz:
    notes_key = f"notes:{sym}"
    notes = db.get_setting(notes_key, {}) or {}
    st.markdown("##### Business model & qualitative notes")
    st.caption("Your own research notes (labelled USER-ENTERED). They feed the AI assistant and the PDF report. "
               "Cite the annual report page or presentation you took them from.")
    with st.form("biz_notes"):
        bm = st.text_area("Business model - how the company makes money", notes.get("business_model", ""), height=90)
        prod = st.text_area("Key products / services / brands", notes.get("products", ""), height=70)
        moat = st.text_area("Competitive position & moat", notes.get("moat", ""), height=70)
        mgmt = st.text_area("Management & governance observations", notes.get("management", ""), height=70)
        src = st.text_input("Source reference (e.g. Annual Report FY2025, p. 34 - with URL)", notes.get("source", ""))
        if st.form_submit_button("Save notes", type="primary"):
            db.set_setting(notes_key, {"business_model": bm, "products": prod, "moat": moat, "management": mgmt,
                                       "source": src, "updated": F.ist(db.utcnow())})
            db.log_activity("Saved research notes", sym)
            st.success("Notes saved.")
    if notes.get("updated"):
        st.caption(f"{ui.badge('user_entered')} Last saved {notes['updated']}", unsafe_allow_html=True)

    st.markdown("##### Revenue segments")
    seg = repo.get_segments(sym)
    if seg.empty:
        ui.empty_state("No segment data",
                       "Segment revenue is not provided by the market-data provider. Enter it below from the "
                       "segment note of the annual report / quarterly results (Ind AS 108).")
    else:
        for period in sorted(seg["period"].unique(), reverse=True)[:1]:
            s = seg[seg["period"] == period]
            c1, c2 = st.columns([2, 3], gap="large")
            c1.plotly_chart(C.donut(s["segment"], s["revenue"] / config.CRORE, hover_suffix=" Cr", height=280),
                            width="stretch", config=C.config())
            tbl = pd.DataFrame({"Segment": s["segment"], "Revenue": s["revenue"].map(F.crore),
                                "Share": (s["revenue"] / s["revenue"].sum()).map(F.pct)}).set_index("Segment")
            with c2:
                st.markdown(f"**{period}** {ui.badges(s['data_type'])}", unsafe_allow_html=True)
                ui.fin_table(tbl)
                top = (s["revenue"].max() / s["revenue"].sum())
                if top > 0.6:
                    ui.note(f"Concentration: the largest segment is {top:.0%} of revenue.", "warn")
        ui.source_footer(seg["source"].unique(), pd.to_datetime(seg["fetched_at"]).max(), urls=seg["source_url"].dropna().unique())
    with st.expander("Enter / update segment data", icon=":material/edit:"):
        period = st.text_input("Period", "FY2025", key="seg_period")
        basis = st.radio("Basis", ["consolidated", "standalone"], horizontal=True, key="seg_basis")
        url = st.text_input("Source URL (annual report / results PDF)", key="seg_url")
        edit = st.data_editor(pd.DataFrame({"Segment": [""], "Revenue (₹ Cr)": [None]}), num_rows="dynamic",
                              width="stretch", key="seg_editor")
        if st.button("Save segments", key="seg_save"):
            e = edit.dropna(subset=["Revenue (₹ Cr)"])
            e = e[e["Segment"].astype(str).str.strip() != ""]
            if e.empty:
                st.error("Enter at least one segment with revenue.")
            else:
                db.execute(db.delete(db.segments).where(db.segments.c.symbol == sym).where(db.segments.c.period == period))
                db.execute(db.insert(db.segments), [{
                    "symbol": sym, "period": period, "segment": r["Segment"].strip(),
                    "revenue": float(r["Revenue (₹ Cr)"]) * config.CRORE, "ebit": None, "basis": basis,
                    "source": "User-entered from company filing", "source_url": url or None,
                    "data_type": "user_entered", "fetched_at": db.utcnow()} for _, r in e.iterrows()])
                db.log_activity("Saved segments", f"{sym} {period}")
                st.rerun()

# ------------------------------------------------------------------ shareholding
with tab_share:
    sh = repo.get_shareholding(sym)
    if sh.empty:
        ui.empty_state("No shareholding data",
                       "Quarterly shareholding patterns are filed with the exchanges (SEBI LODR Reg. 31). "
                       "Open the official page from the 'Official sources' tab and enter the figures below.")
    else:
        latest_p = sorted(sh["period"].unique())[-1]
        s = sh[sh["period"] == latest_p]
        c1, c2 = st.columns([2, 3], gap="large")
        c1.plotly_chart(C.donut(s["category"], s["pct"], hover_suffix="%", height=280), width="stretch", config=C.config())
        with c2:
            st.markdown(f"**Quarter ended {latest_p}** {ui.badges(s['data_type'])}", unsafe_allow_html=True)
            t = pd.DataFrame({"Category": s["category"], "Holding": s["pct"].map(lambda v: f"{v:.2f}%"),
                              "Pledged (of promoter holding)": s["pledged_pct"].map(lambda v: f"{v:.2f}%" if pd.notna(v) else F.MISSING)}).set_index("Category")
            ui.fin_table(t)
            total = s["pct"].sum()
            if abs(total - 100) > 0.5:
                ui.note(f"Categories add up to {total:.2f}%, not 100% - check the entry.", "warn")
            pledge = s["pledged_pct"].dropna()
            if len(pledge) and pledge.max() > 10:
                ui.note(f"Promoter pledge of {pledge.max():.1f}% - pledged shares can be sold by lenders if prices fall.", "warn")
        if sh["period"].nunique() > 1:
            trend = sh.pivot_table(index="period", columns="category", values="pct")
            st.plotly_chart(C.lines(trend, "Shareholding trend", ysuffix="%"), width="stretch", config=C.config())
        ui.source_footer(sh["source"].unique(), pd.to_datetime(sh["fetched_at"]).max(), urls=sh["source_url"].dropna().unique())
    with st.expander("Enter shareholding pattern", icon=":material/edit:"):
        q = st.text_input("Quarter end (YYYY-MM-DD)", "2025-09-30", key="sh_q")
        url = st.text_input("Source URL (NSE/BSE filing)", key="sh_url")
        default = pd.DataFrame({"Category": ["Promoter & Promoter Group", "FII/FPI", "DII", "Public & Others"],
                                "Holding %": [None] * 4, "Pledged % (promoter only)": [None] * 4})
        ed = st.data_editor(default, num_rows="dynamic", width="stretch", key="sh_editor")
        if st.button("Save shareholding", key="sh_save"):
            e = ed.dropna(subset=["Holding %"])
            if e.empty:
                st.error("Enter at least one holding percentage.")
            elif not 99.0 <= e["Holding %"].sum() <= 101.0:
                st.error(f"Holdings add up to {e['Holding %'].sum():.2f}% - they should total 100%.")
            else:
                db.execute(db.delete(db.shareholding).where(db.shareholding.c.symbol == sym).where(db.shareholding.c.period == q))
                db.execute(db.insert(db.shareholding), [{
                    "symbol": sym, "period": q, "category": r["Category"], "pct": float(r["Holding %"]),
                    "pledged_pct": float(r["Pledged % (promoter only)"]) if pd.notna(r["Pledged % (promoter only)"]) else None,
                    "source": "User-entered from exchange filing", "source_url": url or None,
                    "data_type": "user_entered", "fetched_at": db.utcnow()} for _, r in e.iterrows()])
                db.log_activity("Saved shareholding", f"{sym} {q}")
                st.rerun()

# ------------------------------------------------------------------ peers
with tab_peers:
    peers = repo.get_peers(sym)
    allc = repo.list_companies()
    allc = allc[allc["symbol"] != sym]
    names = dict(zip(allc["symbol"], allc["name"]))
    chosen = st.multiselect("Peer group (auto-suggested from industry/sector - edit as needed)",
                            allc["symbol"].tolist(), default=[p for p in peers if p in names],
                            format_func=lambda s: f"{names.get(s, s)} ({s})", max_selections=8)
    if st.button("Save peer group"):
        repo.set_peers(sym, chosen)
        st.success("Peer group saved.")
    if not chosen:
        ui.empty_state("No peers", "Add companies from the same industry to your database, then select them here.")
    else:
        rows = pd.DataFrame([company_metrics(s) for s in [sym] + chosen])
        view = pd.DataFrame({
            "Company": rows["name"], "Mkt cap (₹ Cr)": rows["market_cap"] / config.CRORE, "P/E": rows["pe"],
            "P/B": rows["pb"], "ROE %": rows["roe"] * 100, "ROCE %": rows["roce"] * 100,
            "Rev growth %": rows["revenue_growth"] * 100, "Net margin %": rows["net_margin"] * 100})
        st.dataframe(view, hide_index=True, width="stretch", column_config={
            "Mkt cap (₹ Cr)": st.column_config.NumberColumn(format="%,.0f"),
            **{c: st.column_config.NumberColumn(format="%.1f") for c in ["P/E", "P/B", "ROE %", "ROCE %", "Rev growth %", "Net margin %"]}})
        st.caption("Ratios use each company's latest fiscal year; check that fiscal year-ends are comparable.")
        if st.button("Open full comparison →"):
            st.session_state.compare_symbols = [sym] + chosen[:4]
            st.switch_page("views/compare.py")

# ------------------------------------------------------------------ official sources
with tab_src:
    links = official_links(sym)
    if not links:
        st.info("Sample companies have no official filings.")
    else:
        st.write("Primary sources for verifying the data shown in EquityPilot. These open the official websites; "
                 "EquityPilot does not scrape them.")
        cols = st.columns(2)
        for i, (label, url) in enumerate(links.items()):
            cols[i % 2].link_button(label, url, icon=":material/open_in_new:", width="stretch")
        if company.get("website"):
            st.link_button("Company website / investor relations", company["website"], icon=":material/language:")
        ui.note("Tip: download the latest annual report and results PDF from these pages, then upload them in "
                "the Data Manager. The AI assistant can then summarise them with page references.", "info")
