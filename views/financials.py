"""Financial Analysis: statements, ratios, DuPont, trends, data-quality checks."""
import io

import pandas as pd
import streamlit as st

from equitypilot import config
from equitypilot import formatting as F
from equitypilot.analytics import ratios as R
from equitypilot.data import repository as repo
from equitypilot.data.schema import LINE_ITEMS, NON_MONETARY, STATEMENTS, items_for, label
from equitypilot.ui import charts as C
from equitypilot.ui import components as ui

ctx = ui.require_company()
if not ctx:
    st.stop()
company, quote = ctx
sym = company["symbol"]
ui.page_header("Financial Analysis", "Statements, ratios and historical performance")
ui.company_header(company, quote)

c1, c2, c3 = st.columns([1.3, 2, 3], vertical_alignment="bottom")
ptype = c1.segmented_control("Period", ["annual", "quarterly"], default="annual",
                             format_func=str.title, key="fin_ptype") or "annual"
bases = repo.available_bases(sym, ptype) or ["unspecified"]
basis = c2.selectbox("Statement basis", bases, format_func=lambda b: ui.BASIS_TEXT.get(b, b).split(" (")[0],
                     help="Consolidated = parent + subsidiaries; Standalone = the listed entity alone. "
                          "Yahoo data does not state its basis; uploads from filings do.")
fd = repo.get_financials(sym, ptype, basis)
if fd.empty:
    ui.empty_state(f"No {ptype} statements available",
                   "The provider returned nothing for this company/period. Upload statements from the annual "
                   "report or results in the Data Manager (CSV/Excel template provided).")
    st.page_link("views/data_manager.py", label="Open Data Manager", icon=":material/upload_file:")
    st.stop()

plabels = [F.fiscal_label(p) if ptype == "annual" else pd.Timestamp(p).strftime("%b %Y") for p in fd.periods]
c3.html(f"<div style='text-align:right'>{ui.badges(fd.data_types)}</div>")
if basis == "unspecified":
    ui.note("Basis not stated by the provider. Yahoo Finance generally shows consolidated figures for Indian "
            "listings, but verify material numbers against the company's filing.", "info")

DIV, UNIT = F.amount_unit(fd.currency)
rt = R.compute_ratios(fd)
issues = R.quality_checks(fd)
tab_st, tab_ratio, tab_trend, tab_quality = st.tabs(
    ["Statements", "Ratios & DuPont", "Trends", f"Data quality ({len(issues)})"])


def fmt_value(key, v):
    if key in ("eps_basic", "eps_diluted"):
        return F.inr(v) if fd.currency == "INR" else F.num(v)
    if key in NON_MONETARY:
        return F.MISSING if F.is_missing(v) else f"{v / config.CRORE:,.2f} Cr"  # share counts in crore
    return F.amount(v, fd.currency)


BOLD = {"revenue", "ebitda", "ebit", "net_income", "total_assets", "total_equity", "cfo", "fcf"}

with tab_st:
    st.caption(f"Values in {UNIT} (₹ 1 crore = 10 million) unless stated; EPS in reporting currency; share counts in crore. "
               "Negative values in red. '—' = not reported by the source.")
    export = {}
    for stmt, title in STATEMENTS.items():
        keys = [k for k in items_for(stmt) if k in fd.wide.index]
        if not keys:
            continue
        st.markdown(f"##### {title}")
        tbl = pd.DataFrame({pl: [fmt_value(k, fd.wide.at[k, p]) for k in keys] for pl, p in zip(plabels, fd.periods)},
                           index=[label(k) for k in keys])
        tbl.index.name = UNIT
        ui.fin_table(tbl, bold={label(k) for k in BOLD})
        raw = fd.wide.loc[keys].copy()
        raw.columns = plabels
        raw.index = [label(k) for k in keys]
        export[title[:31]] = raw
    ui.source_footer(fd.sources, fd.fetched_at, basis=fd.basis, urls=fd.source_urls,
                     period=f"{plabels[0]} to {plabels[-1]} ({ptype})")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, frame in export.items():
            frame.to_excel(xw, sheet_name=name)
        pd.DataFrame({"Source": fd.sources or ["—"]}).to_excel(xw, sheet_name="Sources", index=False)
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Excel (raw INR)", buf.getvalue(), f"{sym}_{ptype}_statements.xlsx", icon=":material/download:",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    ui_df = pd.concat(export.values()) if export else pd.DataFrame()
    d2.download_button("CSV (raw INR)", ui_df.to_csv().encode(), f"{sym}_{ptype}_statements.csv",
                       icon=":material/download:", mime="text/csv")

with tab_ratio:
    if ptype == "quarterly":
        ui.note("Quarterly ratios use quarterly flows against period-end balances (not annualised). "
                "Returns such as ROE are therefore roughly one quarter of annual levels.", "warn")
    for cat in R.CATEGORIES:
        keys = [k for k, d in R.RATIOS.items() if d.category == cat and k in rt.index]
        if R.is_financial(company) and cat in ("Liquidity", "Leverage"):
            ui.note(f"{cat} ratios are shown for completeness but are not meaningful for banks/financials.", "info")
        rows = {}
        for k in keys:
            d = R.RATIOS[k]
            rows[d.label] = [F.by_kind(v, d.kind) for v in rt.loc[k]]
        if not rows:
            continue
        st.markdown(f"##### {cat}")
        tbl = pd.DataFrame(rows, index=plabels).T
        tbl.index.name = "Ratio"
        ui.fin_table(tbl, negative_red=True)
    with st.expander("Formulas used", icon=":material/function:"):
        st.dataframe(pd.DataFrame([{"Ratio": d.label, "Formula": d.formula, "What it tells you": d.help}
                                   for d in R.RATIOS.values()]), hide_index=True, placeholder="—", width="stretch")
    if ptype == "annual":
        st.markdown("##### DuPont analysis")
        dp = R.dupont(fd)
        if not dp.empty:
            ui.formula("ROE = Net profit margin × Asset turnover × Equity multiplier (average assets / average equity)")
            t = pd.DataFrame({pl: [F.pct(dp.iloc[0, i]), F.mult(dp.iloc[1, i], 2), F.mult(dp.iloc[2, i], 2), F.pct(dp.iloc[3, i])]
                              for i, pl in enumerate(plabels)}, index=dp.index)
            ui.fin_table(t, bold={"ROE (product)"})
            st.caption("Rising ROE driven by margins or turnover is higher quality than ROE driven by leverage (equity multiplier).")
        f_score, tests = R.piotroski_f_score(fd)
        st.markdown("##### Piotroski F-score (latest year vs prior)")
        if f_score is None:
            st.caption("Not enough data to compute the F-score reliably.")
        else:
            st.metric("F-score", f"{f_score} / 9", help="8-9 strong, 0-2 weak fundamentals (Piotroski, 2000). "
                                                      "Designed for value stocks; interpret with care for financials.")
            st.dataframe(pd.DataFrame([{"Test": t, "Result": "Pass" if v else ("Fail" if v is False else "n/a")}
                                       for t, v in tests]), hide_index=True, placeholder="—", width="stretch")
    ui.source_footer(["Calculated by EquityPilot from the statements shown"] + fd.sources, fd.fetched_at, basis=fd.basis)

with tab_trend:
    def series(key, scale=DIV):
        s = fd.get(key) / scale
        s.index = plabels
        return s

    t1, t2 = st.columns(2, gap="large")
    with t1:
        st.plotly_chart(C.grouped_bars(pd.DataFrame({"Revenue": series("revenue"), "EBITDA": series("ebitda"),
                                                     "Net profit": series("net_income")}),
                                       f"Revenue, EBITDA and net profit ({UNIT})", ysuffix=""),
                        width="stretch", config=C.config())
        st.plotly_chart(C.lines(pd.DataFrame({"ROE": rt.loc["roe"].values * 100, "ROCE": rt.loc["roce"].values * 100},
                                             index=plabels), "Return ratios (%)", ysuffix="%"),
                        width="stretch", config=C.config())
    with t2:
        st.plotly_chart(C.lines(pd.DataFrame({"EBITDA margin": rt.loc["ebitda_margin"].values * 100,
                                              "Net margin": rt.loc["net_margin"].values * 100}, index=plabels),
                                "Margins (%)", ysuffix="%"), width="stretch", config=C.config())
        st.plotly_chart(C.grouped_bars(pd.DataFrame({"Cash from operations": series("cfo"),
                                                     "Net profit": series("net_income")}),
                                       f"Cash conversion: CFO vs net profit ({UNIT})", ysuffix=""),
                        width="stretch", config=C.config())
    if ptype == "annual":
        st.markdown("##### Compound annual growth")
        cg = []
        for key in ("revenue", "ebitda", "net_income", "eps_diluted", "total_equity"):
            cg.append({"Metric": label(key), "3-year CAGR": F.pct(R.cagr(fd.get(key), 3)),
                       f"Full period CAGR ({plabels[0]}-{plabels[-1]})": F.pct(R.cagr(fd.get(key)))})
        st.dataframe(pd.DataFrame(cg), hide_index=True, placeholder="—", width="stretch")
        ui.formula("CAGR = (Ending value / Beginning value)^(1 / years) - 1   (blank if either value ≤ 0)")

with tab_quality:
    if not issues:
        st.success("No consistency issues detected.")
    for it in issues:
        lvl = {"critical": "critical", "warning": "serious", "info": "na"}[it["level"]]
        st.html(f'<div class="ep-flag"><span class="ic {lvl}">{it["level"].upper()}</span><div>'
                f'<div class="t">{ui.esc(it["check"])}</div><div class="x">{ui.esc(it["detail"])}</div></div></div>')
    st.caption("EquityPilot never fills missing figures with estimates. Where a source is incomplete, upload the "
               "official statement in the Data Manager - uploaded figures are stored with their own source and basis.")
