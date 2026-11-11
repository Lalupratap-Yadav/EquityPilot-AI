"""News & Disclosures: third-party headlines, user-logged official disclosures, documents, official links."""
from datetime import date

import pandas as pd
import streamlit as st

from equitypilot import config, db
from equitypilot import formatting as F
from equitypilot.data import repository as repo
from equitypilot.data import uploads as U
from equitypilot.data.official import official_links
from equitypilot.ui import components as ui

CATEGORIES = ["Results", "Board Meeting", "Dividend / Corporate Action", "AGM / EGM", "Credit Rating",
              "Acquisition / Merger", "Insider Trading / SAST", "Shareholding", "Management Change", "Regulatory / Legal",
              "Investor Presentation", "Other"]
AUTO_TAGS = [("Results", ["result", "quarter", "q1", "q2", "q3", "q4", "profit", "earnings", "revenue"]),
             ("Dividend / Corporate Action", ["dividend", "bonus", "split", "buyback", "rights issue"]),
             ("Acquisition / Merger", ["acquir", "merger", "acquisition", "stake", "demerger"]),
             ("Credit Rating", ["rating", "crisil", "icra", "care ratings", "moody", "fitch", "s&p"]),
             ("Management Change", ["ceo", "cfo", "appoint", "resign", "chairman", "managing director"]),
             ("Regulatory / Legal", ["sebi", "rbi", "penalty", "court", "tribunal", "probe", "regulator", "tax demand"])]


def auto_tag(title: str) -> str:
    t = title.lower()
    for cat, words in AUTO_TAGS:
        if any(w in t for w in words):
            return cat
    return "General news"


ctx = ui.require_company()
if not ctx:
    st.stop()
company, quote = ctx
sym = company["symbol"]
ui.page_header("News & Disclosures", "Headlines, exchange disclosures, results and documents - each with its source")
ui.company_header(company, quote)

tab_news, tab_disc, tab_docs, tab_links = st.tabs(["News headlines", "Disclosures & announcements", "Documents", "Official sources"])
allrows = repo.get_disclosures(sym)
news = allrows[allrows["category"] == "News"] if not allrows.empty else allrows
disc = allrows[allrows["category"] != "News"] if not allrows.empty else allrows

# ------------------------------------------------------------------ news
with tab_news:
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    q = c1.text_input("Filter headlines", placeholder="keyword, e.g. results, order, rating", key="news_q")
    if company.get("is_sample"):
        c2.button("Fetch latest", disabled=True, width="stretch", help="Sample companies have no real news.")
    elif c2.button("Fetch latest", icon=":material/refresh:", width="stretch", disabled=config.OFFLINE):
        with st.spinner("Fetching headlines…"):
            ok, msg = repo.refresh_news(sym)
        (st.success if ok else st.warning)(msg)
        st.rerun()
    if news.empty:
        ui.empty_state("No headlines stored", "Click 'Fetch latest' to retrieve recent headlines from the Yahoo Finance aggregator."
                       if not company.get("is_sample") else "Sample companies are fictional and have no news.")
    else:
        n = news.copy()
        n["tag"] = n["title"].map(auto_tag)
        if q:
            n = n[n["title"].str.contains(q, case=False, regex=False)]
        tags = st.pills("Topic (auto-tagged by keywords)", sorted(n["tag"].unique()), selection_mode="multi", key="news_tags")
        if tags:
            n = n[n["tag"].isin(tags)]
        for _, r in n.iterrows():
            link = f'<a href="{ui.esc(r["url"])}" target="_blank" rel="noopener">{ui.esc(r["title"])}</a>' if r["url"] else ui.esc(r["title"])
            st.html(f'<div class="ep-flag"><span class="ic na">{ui.esc(r["tag"])}</span><div><div class="t">{link}</div>'
                    f'<div class="x">{ui.esc(r["publisher"] or "Unknown publisher")} · {F.ist(r["date"])}</div></div></div>')
        ui.source_footer([config.YAHOO_SOURCE + " news aggregator (third-party publishers)"],
                         pd.to_datetime(news["fetched_at"]).max(),
                         extra="Headlines link to the original publisher. EquityPilot does not write or alter news. "
                               "Topic tags are keyword-based and may be imperfect.")

# ------------------------------------------------------------------ disclosures
with tab_disc:
    st.caption("Exchange disclosures (results, board meetings, corporate actions) are published on NSE/BSE. They cannot "
               "be fetched automatically, so log the ones that matter to your research here, with the filing link.")
    if disc.empty:
        ui.empty_state("No disclosures logged", "Use the form below to record an announcement from NSE/BSE.")
    else:
        cats = st.multiselect("Category", sorted(disc["category"].dropna().unique()), key="disc_cat")
        d = disc[disc["category"].isin(cats)] if cats else disc
        view = pd.DataFrame({"Date": d["date"].map(F.fdate), "Category": d["category"], "Title": d["title"],
                             "Link": d["url"], "Type": d["data_type"].map(lambda t: config.DATA_TYPES.get(t, (t,))[0]),
                             "Source": d["source"]})
        st.dataframe(view, hide_index=True, placeholder="—", width="stretch",
                     column_config={"Link": st.column_config.LinkColumn(display_text="open filing")})
    with st.form("add_disc", clear_on_submit=True):
        st.markdown("**Log a disclosure**")
        c1, c2 = st.columns([1, 2])
        ddate = c1.date_input("Date", value=date.today(), format="DD/MM/YYYY")
        dcat = c2.selectbox("Category", CATEGORIES)
        title = st.text_input("Title / summary (as filed)")
        url = st.text_input("Link to the filing (NSE/BSE/company)")
        if st.form_submit_button("Add disclosure", type="primary"):
            if not title.strip():
                st.error("Enter a title.")
            elif company.get("is_sample"):
                st.error("Disclosures cannot be added to fictional sample companies.")
            else:
                repo.add_disclosure(sym, ddate, title, dcat, url, "Exchange filing" if url else "User entry")
                db.log_activity("Logged disclosure", f"{sym}: {title[:60]}")
                st.rerun()

# ------------------------------------------------------------------ documents
with tab_docs:
    docs = U.list_documents(sym)
    if docs.empty:
        ui.empty_state("No documents for this company", "Upload annual reports or results PDFs in the Data Manager.")
    else:
        st.dataframe(docs.assign(uploaded=docs["uploaded_at"].map(F.ist))[["filename", "doc_type", "period", "pages", "uploaded", "source_url"]],
                     hide_index=True, placeholder="—", width="stretch", column_config={"source_url": st.column_config.LinkColumn("Source")})
    st.page_link("views/data_manager.py", label="Upload or search documents in the Data Manager", icon=":material/upload_file:")

# ------------------------------------------------------------------ links
with tab_links:
    links = official_links(sym)
    if not links:
        st.info("Sample companies have no official filings.")
    else:
        cols = st.columns(2)
        for i, (lbl, url) in enumerate(links.items()):
            cols[i % 2].link_button(lbl, url, icon=":material/open_in_new:", width="stretch")
        st.caption("These open the official websites in a new tab. Search for the company there, download the filing, "
                   "and log or upload it here.")
