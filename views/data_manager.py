"""Data Manager: sources & status, refresh, statement/price uploads with review, PDF documents."""
import io

import pandas as pd
import streamlit as st

from equitypilot import config, db
from equitypilot import formatting as F
from equitypilot.data import repository as repo
from equitypilot.data import uploads as U
from equitypilot.data.official import OFFICIAL_SOURCES
from equitypilot.data.schema import label
from equitypilot.data.universe import DEFAULT_UNIVERSE
from equitypilot.ui import components as ui

ui.page_header("Data Manager", "Where every number comes from - refresh, upload, review and correct")

comps = repo.list_companies()
names = dict(zip(comps["symbol"], comps["name"])) if not comps.empty else {}
active = ui.current_symbol()

tab_src, tab_fin, tab_px, tab_doc = st.tabs(["Sources & status", "Upload statements", "Upload prices", "Documents (PDF)"])

# ------------------------------------------------------------------ sources & status
with tab_src:
    st.markdown("##### Data sources used by EquityPilot")
    st.dataframe(pd.DataFrame(OFFICIAL_SOURCES).rename(columns={"name": "Source", "url": "Website", "use": "Used for",
                                                                "access": "How EquityPilot accesses it"}),
                 hide_index=True, width="stretch", column_config={"Website": st.column_config.LinkColumn()})
    st.markdown("##### Data labels")
    st.html("<div>" + " ".join(f"{ui.badge(k)} <span style='font-size:.82rem;color:#475569;margin-right:14px'>{ui.esc(v[1])}</span><br>"
                               for k, v in config.DATA_TYPES.items()) + "</div>")

    st.markdown("##### Cached data by company")
    status = repo.data_status()
    if status.empty:
        ui.empty_state("No data yet", "Add companies on the Dashboard.")
    else:
        view = pd.DataFrame({
            "Symbol": status["symbol"], "Company": status["name"],
            "Type": status["data_type"].map(lambda t: config.DATA_TYPES.get(t, (t,))[0]),
            "In screener": status["in_universe"].astype(bool),
            "FY years": status.get("years"), "Latest FY": status.get("latest_fy").map(F.fiscal_label) if "latest_fy" in status else None,
            "Statements retrieved": status.get("fin_fetched").map(F.ist) if "fin_fetched" in status else None,
            "Price days": status.get("price_days"), "Last price date": status.get("last_price_date").map(F.fdate) if "last_price_date" in status else None,
            "Quote retrieved": status.get("quote_fetched").map(F.ist) if "quote_fetched" in status else None,
        })
        edited = st.data_editor(view, hide_index=True, width="stretch", disabled=[c for c in view.columns if c != "In screener"],
                                key="status_editor")
        changed = edited[edited["In screener"] != view["In screener"]]
        if len(changed) and st.button(f"Save screener-universe changes ({len(changed)})", type="primary"):
            for _, r in changed.iterrows():
                repo.set_in_universe(r["Symbol"], bool(r["In screener"]))
            st.cache_data.clear()
            st.rerun()

    st.markdown("##### Refresh from Yahoo Finance")
    if config.OFFLINE:
        st.info("Offline mode is on (EQUITYPILOT_OFFLINE=1) - refreshing is disabled.")
    else:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            real = [s for s in comps["symbol"] if not s.startswith("SAMPLE-")] if not comps.empty else []
            target = st.selectbox("Company", real, index=real.index(active) if active in real else None,
                                  format_func=lambda s: f"{names.get(s, s)} ({s})", placeholder="Choose…")
            if st.button("Refresh this company", disabled=target is None, icon=":material/refresh:"):
                with st.spinner("Refreshing…"):
                    for fn in (repo.refresh_company, repo.refresh_financials, repo.refresh_prices, repo.refresh_news):
                        ok, msg = fn(target)
                        (st.success if ok else st.warning)(msg)
                db.log_activity("Refreshed company", target)
                st.cache_data.clear()
        with c2:
            st.caption(f"Refresh every company in the screener universe (default list: {len(DEFAULT_UNIVERSE)} large NSE "
                       "companies). Requests are paced; allow 2-4 minutes.")
            if st.button("Refresh entire universe", icon=":material/cloud_sync:"):
                univ = [s for s in repo.list_companies(universe_only=True)["symbol"] if not s.startswith("SAMPLE-")] or DEFAULT_UNIVERSE
                bar = st.progress(0.0)
                res = repo.refresh_universe(univ, progress=lambda p, m: bar.progress(min(p, 1.0), m))
                st.dataframe(pd.DataFrame(res), hide_index=True, width="stretch")
                st.cache_data.clear()

# ------------------------------------------------------------------ statements upload
with tab_fin:
    st.write("Upload figures taken from an **annual report or quarterly results** (official source). They are stored "
             "as OFFICIAL (UPLOADED) with your source link and the basis you choose, and take priority over provider "
             "data for that basis.")
    t = U.statement_template()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        t.to_excel(xw, index=False, sheet_name="Statements")
    c1, c2, _ = st.columns([1, 1, 2])
    c1.download_button("Template (Excel)", buf.getvalue(), "equitypilot_statement_template.xlsx", icon=":material/download:",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    c2.download_button("Template (CSV)", t.to_csv(index=False).encode(), "equitypilot_statement_template.csv",
                       icon=":material/download:", mime="text/csv")
    st.caption("Rows: use the template's line_item keys or common statement captions (e.g. 'Revenue from operations', "
               "'Profit after tax', 'Finance costs'). Columns: periods such as FY2025, Mar-2025 or 2025-03-31.")

    c1, c2, c3, c4 = st.columns(4)
    sym = c1.selectbox("Company", comps["symbol"].tolist() if not comps.empty else [],
                       index=comps["symbol"].tolist().index(active) if active in names else None,
                       format_func=lambda s: f"{names.get(s, s)} ({s})", key="up_sym", placeholder="Choose…")
    basis = c2.selectbox("Basis", ["consolidated", "standalone"], key="up_basis")
    ptype = c3.selectbox("Period type", ["annual", "quarterly"], key="up_ptype")
    unit_name = c4.selectbox("Units in the file", list(U.UNITS), key="up_unit")
    src_doc = st.text_input("Source document (e.g. 'Annual Report FY2025, Consolidated Statement of Profit and Loss, p. 212')", key="up_src")
    src_url = st.text_input("Source URL (company IR / NSE / BSE link)", key="up_url")
    up = st.file_uploader("Statement file (CSV or Excel)", type=["csv", "xlsx", "xls"], key="up_file")
    start_blank = st.toggle("Or enter values manually in a blank template", key="up_blank")

    wide = pd.DataFrame()
    if up is not None:
        try:
            raw = U.read_table(up.getvalue(), up.name)
            wide, warns = U.parse_statements(raw)
            for w in warns:
                st.warning(w)
        except Exception as exc:  # malformed file - show a clear message
            st.error(f"Could not read the file: {exc}")
    elif start_blank:
        wide = pd.DataFrame(index=[k for k in U.LINE_ITEMS], columns=[pd.Timestamp("2026-03-31").date(), pd.Timestamp("2025-03-31").date()])

    if not wide.empty:
        st.markdown("##### Review and correct before saving")
        rev = wide.copy()
        rev.columns = [pd.Timestamp(c).strftime("%Y-%m-%d") for c in rev.columns]
        rev.insert(0, "Line item", [label(k) for k in rev.index])
        rev.index.name = "key"
        edited = st.data_editor(rev, width="stretch", num_rows="fixed", disabled=["Line item"], key="up_review",
                                column_config={c: st.column_config.NumberColumn(format="%.2f") for c in rev.columns[1:]})
        st.caption(f"Values in {unit_name}; EPS in ₹ per share; share counts as absolute numbers. Edit any cell, "
                   "then save. Capex and dividends are stored as outflows (negative) automatically.")
        save_ok = sym is not None and bool(src_doc.strip())
        if not save_ok:
            st.info("Choose a company and enter the source document to enable saving.")
        if st.button("Save to database", type="primary", disabled=not save_ok, icon=":material/save:"):
            vals = edited.drop(columns=["Line item"]).apply(pd.to_numeric, errors="coerce")
            vals.columns = [pd.Timestamp(c).date() for c in vals.columns]
            rows = U.to_rows(vals, sym, basis, ptype, U.UNITS[unit_name], f"Official filing (uploaded): {src_doc.strip()}", src_url)
            if not rows:
                st.error("No values to save.")
            else:
                n = repo.save_financial_rows(rows)
                db.log_activity("Uploaded statements", f"{sym} · {basis} · {n} values")
                st.cache_data.clear()
                st.success(f"Saved {n} values for {names.get(sym, sym)} ({basis}, {ptype}). Select the '{basis}' basis on "
                           "the Financial Analysis page to use them.")

# ------------------------------------------------------------------ prices upload
with tab_px:
    st.write("Upload daily prices exported from NSE ('Historical data' on the quote page) or BSE ('Archives'). "
             "Columns are detected automatically (Date, Open, High, Low, Close, Volume).")
    c1, c2 = st.columns(2)
    psym = c1.selectbox("Company", comps["symbol"].tolist() if not comps.empty else [],
                        index=comps["symbol"].tolist().index(active) if active in names else None,
                        format_func=lambda s: f"{names.get(s, s)} ({s})", key="px_sym", placeholder="Choose…")
    psrc = c2.text_input("Source", "NSE India - historical data download", key="px_src")
    pf = st.file_uploader("Price file (CSV or Excel)", type=["csv", "xlsx", "xls"], key="px_file")
    if pf is not None:
        try:
            parsed, warns = U.parse_prices(U.read_table(pf.getvalue(), pf.name))
        except Exception as exc:
            parsed, warns = pd.DataFrame(), [f"Could not read the file: {exc}"]
        for w in warns:
            st.warning(w)
        if not parsed.empty:
            st.caption(f"{len(parsed)} rows · {F.fdate(parsed['date'].min())} to {F.fdate(parsed['date'].max())}")
            st.dataframe(parsed.tail(10), hide_index=True, width="stretch")
            if st.button("Save prices", type="primary", disabled=psym is None):
                n = repo.save_prices(psym, parsed, psrc)
                db.log_activity("Uploaded prices", f"{psym} · {n} rows")
                st.success(f"Saved {n} daily prices for {psym}.")

# ------------------------------------------------------------------ documents
with tab_doc:
    st.write("Upload annual reports, results or investor presentations (PDF). Text and tables are extracted so you "
             "can search them, copy figures into the statement upload, and ask the AI assistant about them "
             "with page references.")
    c1, c2, c3 = st.columns([2, 1.3, 1])
    dsym = c1.selectbox("Company", comps["symbol"].tolist() if not comps.empty else [],
                        index=comps["symbol"].tolist().index(active) if active in names else None,
                        format_func=lambda s: f"{names.get(s, s)} ({s})", key="doc_sym", placeholder="Choose…")
    dtype = c2.selectbox("Document type", ["Annual Report", "Quarterly Results", "Investor Presentation",
                                           "Earnings Call Transcript", "Credit Rating Report", "Other"], key="doc_type")
    dper = c3.text_input("Period", "FY2025", key="doc_per")
    durl = st.text_input("Source URL", key="doc_url")
    pdf = st.file_uploader("PDF file", type=["pdf"], key="doc_file")
    if pdf is not None and st.button("Extract and save", type="primary", disabled=dsym is None, icon=":material/upload_file:"):
        with st.spinner(f"Extracting text from {pdf.name}… large annual reports can take a minute."):
            try:
                ext = U.extract_pdf(pdf.getvalue())
            except Exception as exc:
                ext = None
                st.error(f"Could not read this PDF: {exc}")
        if ext:
            if ext["scanned"]:
                st.warning("Little or no text was found - this looks like a scanned (image) PDF. OCR is not included; "
                           "download a text-based PDF from the company/exchange website instead.")
            doc_id = U.save_document(dsym, pdf.name, dtype, dper, durl, ext)
            st.session_state["last_doc_tables"] = (doc_id, ext["tables"])
            st.success(f"Saved {pdf.name}: {ext['n_pages']} pages, {len(ext['tables'])} tables detected"
                       + (" (first 600 pages only)" if ext["truncated"] else "") + ".")

    docs = U.list_documents()
    st.markdown("##### Stored documents")
    if docs.empty:
        ui.empty_state("No documents yet", "Upload a PDF above.")
    else:
        dv = docs.assign(uploaded=docs["uploaded_at"].map(F.ist))[["id", "symbol", "filename", "doc_type", "period", "pages", "uploaded", "source_url"]]
        st.dataframe(dv, hide_index=True, width="stretch", column_config={"source_url": st.column_config.LinkColumn("Source")})
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        pick = c1.selectbox("Open document", docs["id"].tolist(),
                            format_func=lambda i: f"#{i} · {docs.set_index('id').loc[i, 'filename']}", key="doc_pick")
        if c2.button("Delete", icon=":material/delete:", key="doc_del"):
            U.delete_document(int(pick))
            st.rerun()
        d = U.get_document(int(pick))
        if d:
            pages = U.text_to_pages(d["text"])
            q = st.text_input("Search inside this document", placeholder="e.g. revenue from operations, contingent liabilities, segment",
                              key="doc_q")
            if q:
                hits = U.search_pages(pages, q)
                st.caption(f"{len(hits)} match(es)")
                for h in hits:
                    st.html(f"<div class='ep-note'><b>Page {h['page']}</b> · {ui.esc(h['snippet'])}</div>")
            pg = st.number_input("View page", 1, max(1, len(pages)), 1, key="doc_pg")
            if pages:
                st.text_area(f"Page {pg} text", pages[pg - 1]["text"], height=260, key=f"doc_txt_{pick}_{pg}")
        last = st.session_state.get("last_doc_tables")
        if last and last[1]:
            with st.expander(f"Tables detected in the last upload ({len(last[1])})", icon=":material/table:"):
                idx = st.selectbox("Table", range(len(last[1])), format_func=lambda i: f"Table {i + 1} (page {last[1][i]['page']})")
                hdr = [f"{(str(c).strip() if c else 'col')} [{i + 1}]" for i, c in enumerate(last[1][idx]["rows"][0])]
                tb = pd.DataFrame(last[1][idx]["rows"][1:], columns=hdr)
                st.dataframe(tb, width="stretch")
                st.download_button("Download this table as CSV", tb.to_csv(index=False).encode(), f"table_{idx + 1}.csv",
                                   mime="text/csv")
                st.caption("Table detection is automatic and can split or merge columns - check against the PDF. "
                           "Clean the CSV into the template layout, then upload it in 'Upload statements'.")
