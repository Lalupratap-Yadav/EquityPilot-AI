"""Stock Screener: filter the local universe on quality, growth, leverage and valuation."""
import pandas as pd
import streamlit as st

from equitypilot import config, db
from equitypilot.analytics.screener import PRESETS, apply_filters, universe_metrics
from equitypilot.data import repository as repo
from equitypilot.ui import components as ui

ui.page_header("Stock Screener", "Filter your research universe on fundamentals and valuation")


@st.cache_data(ttl=600, show_spinner="Computing metrics for the universe…")
def load(version: str) -> pd.DataFrame:
    return universe_metrics()


ver = str(db.read_df(db.select(db.financials.c.fetched_at).order_by(db.financials.c.fetched_at.desc()).limit(1)).values.ravel()) \
      + str(len(repo.list_companies(universe_only=True)))
data = load(ver)
if data.empty:
    ui.empty_state("No companies in the universe", "Load the default universe on the Dashboard or add companies.")
    st.stop()

has_real = (~data["is_sample"]).any()
preset = st.pills("Preset screens", ["None"] + list(PRESETS), default="None", key="scr_preset")
c2, c3, _ = st.columns([1.4, 1.8, 2])
incl_sample = c2.toggle("Include sample companies", value=not has_real, key="scr_sample")
keep_missing = c3.toggle("Keep companies with missing data", value=False, key="scr_missing",
                         help="Off: a company is excluded if a filtered metric is unavailable. On: it is kept (shown as blank).")
base = data if incl_sample else data[~data["is_sample"]]

defaults = PRESETS.get(preset, {}) if preset and preset != "None" else {}
with st.expander("Custom filters" + (f" (preset: {preset})" if preset and preset != "None" else ""), expanded=False,
                 icon=":material/tune:"):
    def rng(col, label, lo, hi, step, pct=True, key=None):
        d = defaults.get(col, (None, None))
        a, b = st.columns(2)
        f = 100 if pct else 1
        mn = a.number_input(f"{label} min", value=None if d[0] is None else d[0] * f, step=step, key=f"{key}_min_{preset}",
                            placeholder="any")
        mx = b.number_input(f"{label} max", value=None if d[1] is None else d[1] * f, step=step, key=f"{key}_max_{preset}",
                            placeholder="any")
        return (None if mn is None else mn / f, None if mx is None else mx / f)

    g1, g2, g3 = st.columns(3, gap="large")
    with g1:
        st.markdown("**Quality**")
        f_roe = rng("roe", "ROE %", 0, 100, 1.0, key="roe")
        f_roce = rng("roce", "ROCE %", 0, 100, 1.0, key="roce")
        f_nm = rng("net_margin", "Net margin %", 0, 100, 1.0, key="nm")
        f_cfo = rng("cfo_to_net_income", "CFO / net profit (x)", 0, 5, 0.1, pct=False, key="cfo")
    with g2:
        st.markdown("**Growth**")
        f_rg = rng("revenue_growth", "Revenue growth YoY %", -50, 200, 1.0, key="rg")
        f_pg = rng("net_income_growth", "Profit growth YoY %", -100, 500, 1.0, key="pg")
        f_rc = rng("revenue_cagr_3y", "Revenue CAGR 3Y %", -50, 100, 1.0, key="rc")
        f_fcf = rng("fcf_margin", "FCF margin %", -50, 100, 1.0, key="fcf")
    with g3:
        st.markdown("**Leverage & valuation**")
        f_de = rng("debt_to_equity", "Debt / equity (x)", 0, 10, 0.1, pct=False, key="de")
        f_pe = rng("pe", "P/E (x)", 0, 200, 1.0, pct=False, key="pe")
        f_pb = rng("pb", "P/B (x)", 0, 50, 0.5, pct=False, key="pb")
        f_dy = rng("dividend_yield", "Dividend yield %", 0, 20, 0.25, key="dy")
    sectors = sorted(base["sector"].dropna().unique())
    sel_sectors = st.multiselect("Sectors", sectors, default=[], placeholder="All sectors")
    min_mcap = st.number_input("Minimum market cap (₹ Cr)", value=0.0, step=1000.0)

filters = {"roe": f_roe, "roce": f_roce, "net_margin": f_nm, "cfo_to_net_income": f_cfo, "revenue_growth": f_rg,
           "net_income_growth": f_pg, "revenue_cagr_3y": f_rc, "fcf_margin": f_fcf, "debt_to_equity": f_de,
           "pe": f_pe, "pb": f_pb, "dividend_yield": f_dy}
filters = {k: v for k, v in filters.items() if v != (None, None)}
if filters:
    st.caption("Active filters: " + " · ".join(
        f"{k.replace('_', ' ')} {'≥ ' + format(lo, '.2f') if lo is not None else ''}{' ' if lo is not None and hi is not None else ''}"
        f"{'≤ ' + format(hi, '.2f') if hi is not None else ''}" for k, (lo, hi) in filters.items()) +
        " (ratios as decimals, e.g. 0.15 = 15%)")
res = apply_filters(base, filters, keep_missing=keep_missing)
if sel_sectors:
    res = res[res["sector"].isin(sel_sectors)]
if min_mcap:
    res = res[pd.to_numeric(res["market_cap"], errors="coerce") >= min_mcap * config.CRORE]
if "debt_to_equity" in filters and not keep_missing:
    n_fin = int(base["is_financial"].sum())
    if n_fin:
        st.caption(f"Note: {n_fin} financial companies have no debt/equity (not meaningful for lenders) and are excluded by the D/E filter.")

st.markdown(f"##### {len(res)} of {len(base)} companies match")
if res.empty:
    ui.empty_state("No matches", "Relax a filter, or turn on 'Keep companies with missing data'.")
    st.stop()
view = pd.DataFrame({
    "Company": res["name"], "Symbol": res["symbol"], "Sector": res["sector"],
    "Mkt cap (₹ Cr)": pd.to_numeric(res["market_cap"], errors="coerce") / config.CRORE,
    "P/E": res["pe"], "P/B": res["pb"], "ROE %": res["roe"] * 100, "ROCE %": res["roce"] * 100,
    "D/E": res["debt_to_equity"], "Rev growth %": res["revenue_growth"] * 100,
    "Profit growth %": res["net_income_growth"] * 100, "Net margin %": res["net_margin"] * 100,
    "F-score": res["piotroski"], "Data": res["data_type"].map(lambda t: config.DATA_TYPES[t][0]),
}).sort_values("Mkt cap (₹ Cr)", ascending=False)
for col in view.columns[3:-1]:
    view[col] = pd.to_numeric(view[col], errors="coerce")   # None -> NaN so missing cells render blank
num = lambda f: st.column_config.NumberColumn(format=f)  # noqa: E731
event = st.dataframe(view, hide_index=True, width="stretch", height=min(42 + 35 * len(view), 640),
                     on_select="rerun", selection_mode="multi-row", key="scr_table",
                     column_config={"Mkt cap (₹ Cr)": num("%,.0f"), "P/E": num("%.1f"), "P/B": num("%.1f"),
                                    "ROE %": num("%.1f"), "ROCE %": num("%.1f"), "D/E": num("%.2f"),
                                    "Rev growth %": num("%.1f"), "Profit growth %": num("%.1f"),
                                    "Net margin %": num("%.1f"), "F-score": num("%d")})
sel = [view.iloc[i]["Symbol"] for i in (event.selection.rows if event and event.selection else [])]
b1, b2, b3, b4 = st.columns(4)
if b1.button("Open selected", disabled=len(sel) != 1, icon=":material/open_in_new:", width="stretch"):
    ui.set_symbol(sel[0])
    st.switch_page("views/company.py")
if b2.button("Compare selected", disabled=not 2 <= len(sel) <= 5, icon=":material/compare_arrows:", width="stretch"):
    st.session_state.compare_symbols = sel
    st.switch_page("views/compare.py")
if b3.button("Add to watchlist", disabled=not sel, icon=":material/bookmark_add:", width="stretch"):
    for s in sel:
        repo.add_to_watchlist(s)
    st.toast(f"Added {len(sel)} to watchlist")
b4.download_button("Export CSV", view.to_csv(index=False).encode(), "screener_results.csv", mime="text/csv",
                   icon=":material/download:", width="stretch")
st.caption("Click column headers to sort. Select 1 row to open, 2-5 to compare. Ratios use each company's latest fiscal "
           "year (Yahoo Finance, basis not stated); P/E uses TTM earnings where available. Financials show '—' for D/E.")
