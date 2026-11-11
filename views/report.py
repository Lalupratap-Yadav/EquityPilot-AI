"""Research Report Generator: professional PDF with tables, charts, assumptions and sources."""
import re

import streamlit as st

from equitypilot import config, db
from equitypilot import formatting as F
from equitypilot.reports.pdf_report import ReportOptions, build_report
from equitypilot.ui import components as ui

ctx = ui.require_company()
if not ctx:
    st.stop()
company, quote = ctx
sym = company["symbol"]
ui.page_header("Research Report Generator", "Create a downloadable PDF equity research report with sources and disclosures")
ui.company_header(company, quote)

SECTIONS = {"overview": "Company overview, segments & shareholding", "financials": "Financial performance (table + chart)",
            "ratios": "Ratio analysis (table + chart)", "valuation": "Valuation (multiples, saved DCF, scenarios, sensitivity)",
            "technicals": "Price & technical snapshot", "risk": "Risk assessment", "news": "Recent disclosures & headlines",
            "sources": "Sources & disclosures (always included)"}

saved_val = db.get_setting(f"valuation:{sym}")
notes = db.get_setting(f"notes:{sym}") or {}
risk_notes = db.get_setting(f"risk_notes:{sym}") or {}
c1, c2, c3 = st.columns(3)
c1.metric("Saved DCF", "Yes" if saved_val else "No", help="Save a DCF on the Valuation page to include assumptions and results.")
c2.metric("Business notes", "Yes" if any(notes.get(k) for k in ("business_model", "products", "moat")) else "No",
          help="Company Research → Business & segments")
c3.metric("Risk notes", "Yes" if risk_notes.get("text") else "No", help="Risk Analysis page")
if not saved_val:
    st.page_link("views/valuation.py", label="Build and save a DCF first (recommended)", icon=":material/calculate:")

with st.form("report_form"):
    a1, a2 = st.columns(2)
    analyst = a1.text_input("Prepared by", db.get_setting("report_author", "") or "", placeholder="Your name, e.g. MBA candidate, IIT Jodhpur")
    title = a2.text_input("Report title", f"{company['name']} - Equity Research Note")
    thesis = st.text_area("Analyst summary / thesis (your own words - printed as written)", height=120,
                          placeholder="Key points of your analysis: business quality, growth drivers, valuation context, key risks…")
    own_view = st.text_area("Optional: your personal view (clearly labelled as the author's, never generated)", height=70)
    chosen = st.multiselect("Sections", list(SECTIONS), default=list(SECTIONS), format_func=SECTIONS.get)
    go = st.form_submit_button("Generate PDF report", type="primary", icon=":material/picture_as_pdf:")

if go:
    if analyst:
        db.set_setting("report_author", analyst)
    if re.search(r"\b(strong buy|buy|sell|accumulate|target price)\b", (thesis + " " + own_view).lower()):
        st.info("Your text contains recommendation language. That is your own view and will be printed in a labelled "
                "section; remember that publishing recommendations in India requires SEBI registration.")
    with st.spinner("Building report - drawing charts and tables…"):
        try:
            pdf = build_report(sym, ReportOptions(analyst=analyst or "EquityPilot user", title=title, thesis=thesis,
                                                  own_view=own_view, sections=chosen + ["sources"]))
        except Exception as exc:  # report must never crash the page
            st.error(f"Report generation failed: {exc}")
            pdf = None
    if pdf:
        config.ensure_dirs()
        fname = f"{F.safe_filename(sym)}_research_{db.utcnow():%Y%m%d_%H%M}.pdf"
        (config.REPORT_DIR / fname).write_bytes(pdf)
        st.session_state["last_report"] = (fname, pdf)
        st.success(f"Report ready ({len(pdf) / 1024:,.0f} KB). A copy is saved in data/reports/{fname}.")

if st.session_state.get("last_report"):
    fname, pdf = st.session_state["last_report"]
    st.download_button("Download PDF", pdf, fname, mime="application/pdf", type="primary", icon=":material/download:")

past = sorted(config.REPORT_DIR.glob("*.pdf"), reverse=True) if config.REPORT_DIR.exists() else []
if past:
    with st.expander(f"Previously generated reports ({len(past)})"):
        for p in past[:15]:
            c1, c2 = st.columns([4, 1])
            c1.write(f"{p.name} · {p.stat().st_size / 1024:,.0f} KB")
            c2.download_button("Download", p.read_bytes(), p.name, mime="application/pdf", key=f"dl_{p.name}")
st.caption("Reports contain only data stored in EquityPilot with its sources, calculations with formulas, and your "
           "labelled assumptions and notes. Sample companies are watermarked as fictional.")
