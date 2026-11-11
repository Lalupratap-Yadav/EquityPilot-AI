"""Risk Analysis: debt, liquidity, profitability, cash flow, concentration, market, business and regulatory risks."""
import pandas as pd
import streamlit as st

from equitypilot import db
from equitypilot import formatting as F
from equitypilot.analytics import risk as K
from equitypilot.data import repository as repo
from equitypilot.ui import components as ui

ctx = ui.require_company()
if not ctx:
    st.stop()
company, quote = ctx
sym = company["symbol"]
ui.page_header("Risk Analysis", "Transparent rule-based checks - every threshold is shown")
ui.company_header(company, quote)

fd = repo.get_financials(sym)
px = repo.get_prices(sym, auto_refresh=False)
flags = K.assess(company, fd, px, repo.get_shareholding(sym), repo.get_segments(sym))
summary = K.summarise(flags)
score = K.overall_score(flags)

lvl_txt = lambda l: K.LEVEL_LABEL.get(l, l)  # noqa: E731
c1, c2 = st.columns([1, 3], gap="large")
with c1:
    band = "Low" if score is not None and score < 25 else "Moderate" if score is not None and score < 45 else "Elevated" if score is not None and score < 65 else "High"
    st.metric("Composite risk score", f"{score:.0f} / 100" if score is not None else F.MISSING,
              help="Average of the assessed checks (Low=0, Moderate=33, Elevated=67, High=100). Lower is better. "
                   "A summary device only - read the individual checks.", border=True)
    st.caption(f"Overall: **{band if score is not None else 'n/a'}** across {sum(1 for f in flags if f['level'] != 'na')} quantitative checks.")
with c2:
    chips = "".join(
        f'<div class="ep-flag" style="padding:8px 10px"><span class="ic {r["Level"]}">{lvl_txt(r["Level"])}</span>'
        f'<div><div class="t">{ui.esc(r["Category"])}</div><div class="x">{r["Checks"]} check(s) · '
        f'{r["Elevated or high"]} elevated or high</div></div></div>'
        for _, r in summary.iterrows())
    st.html(f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px">{chips}</div>')

st.markdown("##### Quantitative checks")
for cat in summary["Category"]:
    with st.expander(cat, expanded=cat in ("Debt", "Cash flow", "Profitability")):
        for f in [x for x in flags if x["category"] == cat]:
            st.html(f'<div class="ep-flag"><span class="ic {f["level"]}">{lvl_txt(f["level"])}</span><div>'
                    f'<div class="t">{ui.esc(f["title"])}: {ui.esc(f["value"])}</div>'
                    f'<div class="x">{ui.esc(f["detail"])}</div>'
                    f'<div class="x" style="color:#8A8F98">Thresholds: {ui.esc(f["rule"])}</div></div></div>')
z, zone, xs = K.altman_z_double_prime(fd)
if xs:
    with st.expander("Altman Z'' calculation", icon=":material/function:"):
        ui.formula("Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4")
        st.dataframe(pd.DataFrame({"Component": ["X1 = Working capital / Total assets", "X2 = Retained earnings / Total assets",
                                                 "X3 = EBIT / Total assets", "X4 = Book equity / Total liabilities"],
                                   "Value": [f"{v:.3f}" for v in xs.values()]}), hide_index=True, width="stretch")
        st.caption(f"Z'' = {z:.2f} → {zone} zone. Not applicable to banks/financials.")
ui.source_footer(["Calculated by EquityPilot"] + fd.sources, fd.fetched_at, basis=fd.basis,
                 period=f"Latest FY: {F.fiscal_label(fd.periods[-1])}" if not fd.empty else None)

# ------------------------------------------------------------------ qualitative
st.markdown("##### Business and regulatory considerations")
sector = company.get("sector")
items = K.SECTOR_CONSIDERATIONS.get(sector, [])
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown(f"**General risks for the {sector or 'company'} sector**")
    if items:
        for it in items:
            st.markdown(f"- {it}")
    else:
        st.caption("No sector template available.")
    st.caption("These are general industry considerations, not findings about this specific company.")
with c2:
    st.markdown("**Regulatory and disclosure checklist**")
    for it in K.GENERAL_REGULATORY:
        st.markdown(f"- {it}")

st.markdown("##### Your company-specific risk notes")
key = f"risk_notes:{sym}"
saved = db.get_setting(key, {}) or {}
with st.form("risk_notes"):
    txt = st.text_area("Key risks identified from the annual report, results and disclosures (with page references)",
                       saved.get("text", ""), height=120)
    src = st.text_input("Source", saved.get("source", ""))
    if st.form_submit_button("Save risk notes", type="primary"):
        db.set_setting(key, {"text": txt, "source": src, "updated": F.ist(db.utcnow())})
        db.log_activity("Saved risk notes", sym)
        st.success("Saved - included in the research report and available to the AI assistant.")
