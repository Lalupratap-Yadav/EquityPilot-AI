"""Portfolio Analysis: holdings, value, returns (incl. XIRR), allocation, diversification and risk."""
import pandas as pd
import streamlit as st

from equitypilot import config, db
from equitypilot import formatting as F
from equitypilot.analytics import portfolio as PF
from equitypilot.data import repository as repo
from equitypilot.data import sample
from equitypilot.ui import charts as C
from equitypilot.ui import components as ui

ui.page_header("Portfolio Analysis", "Track holdings, returns, allocation, diversification and risk")

comps = repo.list_companies()
names = dict(zip(comps["symbol"], comps["name"])) if not comps.empty else {}
h = repo.get_holdings()

# ------------------------------------------------------------------ holdings editor
with st.expander("Edit holdings", expanded=h.empty, icon=":material/edit_note:"):
    st.caption("One row per purchase lot. Average cost and quantity are what you paid; buy date enables XIRR. "
               "Companies must exist in EquityPilot (add new ones on the Dashboard).")
    base = h[["symbol", "quantity", "avg_cost", "buy_date", "notes"]] if not h.empty else \
        pd.DataFrame({"symbol": pd.Series(dtype=str), "quantity": pd.Series(dtype=float), "avg_cost": pd.Series(dtype=float),
                      "buy_date": pd.Series(dtype="datetime64[ns]"), "notes": pd.Series(dtype=str)})
    base = base.assign(buy_date=pd.to_datetime(base["buy_date"]))
    edited = st.data_editor(base, num_rows="dynamic", width="stretch", key="hold_editor", column_config={
        "symbol": st.column_config.SelectboxColumn("Company", options=list(names), required=True),
        "quantity": st.column_config.NumberColumn("Quantity", min_value=0.0, step=1.0, required=True),
        "avg_cost": st.column_config.NumberColumn("Avg cost (₹)", min_value=0.0, format="₹%.2f", required=True),
        "buy_date": st.column_config.DateColumn("Buy date", format="DD/MM/YYYY"),
        "notes": st.column_config.TextColumn("Notes")})
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Save holdings", type="primary", icon=":material/save:", width="stretch"):
        n = repo.replace_holdings(edited)
        db.log_activity("Updated portfolio", f"{n} holdings")
        st.rerun()
    if c2.button("Load sample portfolio", icon=":material/science:", width="stretch",
                 help="Adds four fictional SAMPLE holdings to explore the features."):
        sample.load_sample_portfolio()
        st.rerun()
    up = c3.file_uploader("Import CSV", type=["csv"], label_visibility="collapsed",
                          help="Columns: symbol, quantity, avg_cost, buy_date (DD/MM/YYYY), notes")
    if up is not None:
        try:
            imp = pd.read_csv(up)
            imp.columns = [c.strip().lower() for c in imp.columns]
            if "buy_date" in imp:
                imp["buy_date"] = pd.to_datetime(imp["buy_date"], dayfirst=True, errors="coerce")
            missing = sorted(set(imp["symbol"].str.upper()) - set(names))
            if missing:
                st.warning("Not in EquityPilot yet (add them on the Dashboard first): " + ", ".join(missing))
            imp = imp[imp["symbol"].str.upper().isin(names)]
            if st.button(f"Replace holdings with {len(imp)} imported rows"):
                repo.replace_holdings(imp)
                st.rerun()
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
    if not h.empty:
        c4.download_button("Export CSV", h.drop(columns=["id"]).to_csv(index=False).encode(), "portfolio.csv",
                           mime="text/csv", icon=":material/download:", width="stretch")

if h.empty:
    ui.empty_state("No holdings yet", "Add holdings above, import a CSV, or load the sample portfolio to explore.")
    st.stop()

v = PF.value_holdings(h)
if (v["data_type"] == "sample").any():
    ui.note("This portfolio includes fictional SAMPLE holdings - their prices are simulated.", "sample")
missing = v[v["price"].isna()]
if len(missing):
    ui.note("No current price for: " + ", ".join(missing["symbol"]) + " - they are excluded from value-based metrics.", "warn")

invested, value = v["invested"].sum(), v["value"].sum(skipna=True)
xr = PF.portfolio_xirr(v)
conc = PF.concentration(v.groupby("symbol")["weight"].sum())
ui.kpis([
    {"label": "Current value", "value": F.inr(value, 0)},
    {"label": "Invested", "value": F.inr(invested, 0)},
    {"label": "Unrealised P&L", "value": F.inr(value - invested, 0), "delta": F.pct(value / invested - 1, signed=True) if invested else "",
     "sign": 1 if value >= invested else -1},
    {"label": "XIRR (annualised)", "value": F.pct(xr), "help": "Money-weighted annual return using each lot's buy date and today's value."
     + ("" if xr is not None else " Needs a buy date for every lot.")},
    {"label": "Holdings", "value": str(v["symbol"].nunique())},
    {"label": "Effective no. of stocks", "value": F.num(conc["effective_n"], 1), "help": "1 / Σ(weight²). Lower = more concentrated."},
])

# ------------------------------------------------------------------ holdings table
agg = v.groupby(["symbol", "name", "sector"], as_index=False).agg(
    quantity=("quantity", "sum"), invested=("invested", "sum"), value=("value", "sum"), price=("price", "first"),
    data_type=("data_type", "first"))
agg["avg_cost"] = agg["invested"] / agg["quantity"]
agg["pnl"] = agg["value"] - agg["invested"]
agg["return"] = agg["value"] / agg["invested"] - 1
agg["weight"] = agg["value"] / agg["value"].sum()
st.dataframe(pd.DataFrame({
    "Company": agg["name"], "Qty": agg["quantity"], "Avg cost": agg["avg_cost"], "Price": agg["price"],
    "Invested": agg["invested"], "Value": agg["value"], "P&L": agg["pnl"], "Return %": agg["return"] * 100,
    "Weight %": agg["weight"] * 100, "Data": agg["data_type"].map(lambda t: config.DATA_TYPES.get(t, ("NO PRICE",))[0])}),
    hide_index=True, placeholder="—", width="stretch", column_config={
        "Avg cost": st.column_config.NumberColumn(format="₹%,.2f"), "Price": st.column_config.NumberColumn(format="₹%,.2f"),
        "Invested": st.column_config.NumberColumn(format="₹%,.0f"), "Value": st.column_config.NumberColumn(format="₹%,.0f"),
        "P&L": st.column_config.NumberColumn(format="₹%,.0f"), "Return %": st.column_config.NumberColumn(format="%+.1f%%"),
        "Weight %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)})
st.caption(f"Prices: latest stored quotes (delayed). Latest quote time: {F.ist(pd.to_datetime(v['price_time']).max())}.")

c1, c2 = st.columns(2, gap="large")
c1.plotly_chart(C.donut(agg["name"].str.replace(" Limited", ""), agg["value"], "Allocation by holding", hover_suffix=" ₹"),
                width="stretch", config=C.config())
sec = agg.groupby("sector")["value"].sum().sort_values(ascending=False)
c2.plotly_chart(C.donut(sec.index, sec.values, "Allocation by sector", hover_suffix=" ₹"), width="stretch", config=C.config())
sconc = PF.concentration(sec / sec.sum())
notes = []
if conc["top_weight"] and conc["top_weight"] > 0.25:
    notes.append(f"Largest holding is {conc['top_weight']:.0%} of the portfolio (above 25%).")
if sconc["top_weight"] and sconc["top_weight"] > 0.40:
    notes.append(f"Largest sector is {sconc['top_weight']:.0%} of the portfolio (above 40%).")
if conc["effective_n"] and conc["effective_n"] < 5:
    notes.append(f"Effective number of holdings is {conc['effective_n']:.1f} - diversification is limited.")
for n in notes:
    ui.note(n, "warn")

# ------------------------------------------------------------------ risk
st.markdown("##### Risk (last 12 months, current weights)")
bench = repo.get_prices(config.BENCHMARK, auto_refresh=False)
bench_s = bench.set_index("date")["close"] if not bench.empty and not (v["data_type"] == "sample").all() else None
rf = st.number_input("Risk-free rate for Sharpe ratio (%)", 0.0, 15.0, 6.5, 0.25,
                     help="Assumption - e.g. a 1-year T-bill or 10-year G-sec yield on your valuation date.") / 100
rm = PF.risk_metrics(v, rf, bench_s)
if not rm:
    ui.empty_state("Not enough price history", "Risk metrics need about two months of overlapping daily prices for the holdings.")
else:
    ui.kpis([
        {"label": "Return (1Y, current weights)", "value": F.pct(rm["annual_return"], signed=True)},
        {"label": "Volatility (ann.)", "value": F.pct(rm["volatility"])},
        {"label": "Sharpe ratio", "value": F.num(rm["sharpe"]), "help": "(Return - risk-free) / volatility"},
        {"label": "Max drawdown", "value": F.pct(rm["max_drawdown"])},
        {"label": "Beta vs NIFTY 50", "value": F.num(rm.get("beta")), "help": "Not computed for sample-only portfolios."},
        {"label": "Diversification ratio", "value": F.num(rm["diversification_ratio"]),
         "help": "Weighted average of stock volatilities / portfolio volatility. Higher = more diversification benefit."},
    ])
    c1, c2 = st.columns(2, gap="large")
    rc = rm["risk_contribution"].rename(index=lambda s: names.get(s, s).replace(" Limited", "")[:28]) * 100
    c1.plotly_chart(C.hbar(rc.index, rc.values, "Share of portfolio risk (%)", suffix="%"), width="stretch", config=C.config())
    corr = rm["correlation"].rename(index=lambda s: s.replace(".NS", ""), columns=lambda s: s.replace(".NS", ""))
    c2.plotly_chart(C.heatmap(corr, "Correlation of daily returns", diverging=True, zmid=0, height=max(300, 60 * len(corr))),
                    width="stretch", config=C.config())
    st.plotly_chart(C.lines(pd.DataFrame({"Portfolio (rebased 100)": rm["series"]}), "Growth of ₹100 at current weights",
                            markers=False, height=280), width="stretch", config=C.config())
    st.caption(f"{rm['observations']} daily returns from {F.fdate(rm['start'])} to {F.fdate(rm['end'])}. These statistics apply "
               "today's weights to past returns - they describe the current mix, not your actual historical experience.")
