"""Dashboard: market overview, company search, watchlist, highlights, recent activity."""
from datetime import datetime

import pandas as pd
import streamlit as st

from equitypilot import config, db
from equitypilot import formatting as F
from equitypilot.analytics.screener import company_metrics
from equitypilot.data import repository as repo
from equitypilot.data import yahoo
from equitypilot.data.universe import DEFAULT_UNIVERSE
from equitypilot.ui import components as ui

ui.page_header("Market Overview", f"Indian equities · {datetime.now().strftime('%A, %d %B %Y')}")


@st.cache_data(ttl=900, show_spinner=False)
def load_indices() -> pd.DataFrame:
    try:
        return yahoo.fetch_index_snapshot(config.INDICES)
    except yahoo.ProviderError:
        return pd.DataFrame()


# ------------------------------------------------------------------ indices
st.subheader("Indices")
idx = pd.DataFrame() if config.OFFLINE else load_indices()
if idx.empty:
    ui.empty_state("Index data unavailable",
                   "Offline mode is on or the data provider could not be reached. No index values are shown "
                   "rather than showing stale or invented numbers.")
else:
    cols = st.columns(len(idx))
    for col, (_, r) in zip(cols, idx.iterrows()):
        col.metric(r["name"], f"{r['last']:,.2f}", f"{r['change']:+,.2f} ({r['change_pct']:+.2%})",
                   chart_data=r["spark"], chart_type="line", border=True,
                   delta_color="inverse" if "VIX" in r["name"] else "normal",
                   help=f"Close as of {F.fdate(r['as_of'])}. Sparkline: last ~1 month.")
    ui.source_footer([config.YAHOO_SOURCE + " - index levels (delayed / end-of-day)"],
                     fetched_at=db.utcnow(), extra="Cached for 15 minutes.")

# ------------------------------------------------------------------ search
st.subheader("Find a company")
left, right = st.columns([3, 2], gap="large")
with left:
    ui.symbol_input_add("dash_add")
with right:
    loaded = repo.list_companies()
    st.caption(f"{len(loaded)} companies in your local database "
               f"({int(loaded['is_sample'].sum()) if not loaded.empty else 0} fictional samples). "
               "Use the sidebar selector to open one.")
    real = loaded[~loaded["is_sample"].astype(bool)] if not loaded.empty else loaded
    if len(real) < 10 and not config.OFFLINE:
        with st.popover("Load default research universe", icon=":material/cloud_download:", width="stretch"):
            st.write(f"Fetches profile, quote, 4-5 years of statements and price history for "
                     f"{len(DEFAULT_UNIVERSE)} large NSE companies from Yahoo Finance. Takes about 2-4 minutes; "
                     "requests are paced to respect the provider.")
            if st.button("Start download", type="primary", key="load_univ"):
                bar = st.progress(0.0, "Starting…")
                res = repo.refresh_universe(progress=lambda p, m: bar.progress(min(p, 1.0), m))
                failed = [r for r in res if r.get("profile") != "OK"]
                st.success(f"Loaded {len(res) - len(failed)} companies." +
                           (f" {len(failed)} failed: {', '.join(r['symbol'] for r in failed)}" if failed else ""))
                st.rerun()

# ------------------------------------------------------------------ watchlist
st.subheader("Watchlist")
wl = repo.get_watchlist()
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
opts = [s for s in loaded["symbol"].tolist() if s not in wl] if not loaded.empty else []
names = dict(zip(loaded["symbol"], loaded["name"])) if not loaded.empty else {}
add = c1.selectbox("Add to watchlist", opts, index=None, format_func=lambda s: f"{names.get(s, s)} ({s})",
                   placeholder="Choose a company…")
if c2.button("Add", width="stretch", disabled=add is None):
    repo.add_to_watchlist(add)
    db.log_activity("Watchlist add", add)
    st.rerun()

if not wl:
    ui.empty_state("Your watchlist is empty", "Add companies above to track price, valuation and quality at a glance.")
else:
    rows = [company_metrics(s) for s in wl]
    wdf = pd.DataFrame(rows)
    view = pd.DataFrame({
        "Company": wdf["name"], "Symbol": wdf["symbol"], "Price (₹)": wdf["price"],
        "Day %": wdf["day_change"] * 100, "Mkt cap (₹ Cr)": wdf["market_cap"] / config.CRORE,
        "P/E": wdf["pe"], "ROE %": wdf["roe"] * 100, "Debt/Equity": wdf["debt_to_equity"],
        "Data": wdf["data_type"].map(lambda t: config.DATA_TYPES[t][0]),
    })
    event = st.dataframe(
        view, hide_index=True, placeholder="—", width="stretch", on_select="rerun", selection_mode="single-row",
        column_config={
            "Price (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
            "Day %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Mkt cap (₹ Cr)": st.column_config.NumberColumn(format="%,.0f"),
            "P/E": st.column_config.NumberColumn(format="%.1fx"),
            "ROE %": st.column_config.NumberColumn(format="%.1f%%"),
            "Debt/Equity": st.column_config.NumberColumn(format="%.2fx"),
        }, key="wl_table")
    sel = event.selection.rows if event and event.selection else []
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("Open selected", disabled=not sel, icon=":material/open_in_new:"):
        ui.set_symbol(view.iloc[sel[0]]["Symbol"])
        st.switch_page("views/company.py")
    if b2.button("Remove selected", disabled=not sel, icon=":material/delete:"):
        repo.remove_from_watchlist(view.iloc[sel[0]]["Symbol"])
        st.rerun()
    st.caption("Select a row to open or remove it. P/E uses trailing-twelve-month earnings where quarterly data "
               "exists, otherwise the latest fiscal year. ROE and D/E are from the latest fiscal year.")

# ------------------------------------------------------------------ highlights
st.subheader("Highlights from your universe")
qdf = db.read_df(db.select(db.quotes.c.symbol, db.quotes.c.price, db.quotes.c.prev_close, db.quotes.c.as_of,
                           db.quotes.c.data_type))
if not qdf.empty and not loaded.empty:
    qdf = qdf.merge(loaded[["symbol", "name", "sector", "is_sample"]], on="symbol")
    qdf = qdf[~qdf["is_sample"].astype(bool)]
    qdf["chg"] = qdf["price"] / qdf["prev_close"] - 1
    qdf = qdf.dropna(subset=["chg"])
if qdf.empty or len(qdf) < 4:
    ui.empty_state("Not enough market data yet",
                   "Load the default research universe (above) or add companies to see gainers, losers and sector moves.")
else:
    h1, h2, h3 = st.columns(3, gap="medium")

    def movers(frame, title, col):
        with col:
            st.markdown(f"**{title}**")
            t = frame[["name", "price", "chg"]].rename(columns={"name": "Company", "price": "Price (₹)", "chg": "Change"})
            t["Change"] = t["Change"] * 100
            st.dataframe(t, hide_index=True, placeholder="—", width="stretch", column_config={
                "Price (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                "Change": st.column_config.NumberColumn(format="%+.2f%%")})

    movers(qdf.nlargest(5, "chg"), "Top gainers", h1)
    movers(qdf.nsmallest(5, "chg"), "Top losers", h2)
    with h3:
        st.markdown("**Sector moves (average)**")
        sec = qdf.groupby("sector")["chg"].agg(["mean", "count"]).sort_values("mean", ascending=False).reset_index()
        sec.columns = ["Sector", "Avg change", "Companies"]
        sec["Avg change"] = sec["Avg change"] * 100
        st.dataframe(sec, hide_index=True, placeholder="—", width="stretch", column_config={
            "Avg change": st.column_config.NumberColumn(format="%+.2f%%")})
    ui.source_footer([config.YAHOO_SOURCE + " - delayed quotes"], fetched_at=None,
                     extra=f"Covers only the {len(qdf)} companies loaded in EquityPilot, not the whole market. "
                           f"Latest quote time: {F.ist(pd.to_datetime(qdf['as_of']).max())}.")

# ------------------------------------------------------------------ activity
st.subheader("Recent activity")
act = db.recent_activity(8)
if act.empty:
    st.caption("No activity yet - add a company, run a valuation or generate a report.")
else:
    act["When"] = act["ts"].map(F.ist)
    st.dataframe(act[["When", "action", "detail"]].rename(columns={"action": "Action", "detail": "Detail"}),
                 hide_index=True, placeholder="—", width="stretch")
