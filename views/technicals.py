"""Technical Analysis: price history, moving averages, RSI, MACD, Bollinger bands, volume, volatility, beta."""
import pandas as pd
import streamlit as st

from equitypilot import config
from equitypilot import formatting as F
from equitypilot.analytics import technicals as T
from equitypilot.data import repository as repo
from equitypilot.ui import charts as C
from equitypilot.ui import components as ui

ctx = ui.require_company()
if not ctx:
    st.stop()
company, quote = ctx
sym = company["symbol"]
ui.page_header("Technical Analysis", "Price trends, momentum and market risk from daily price history")
ui.company_header(company, quote)

px = repo.get_prices(sym)
if px.empty or len(px) < 30:
    ui.empty_state("Not enough price history",
                   "The provider returned too little data. You can upload a daily price CSV downloaded from NSE/BSE in the Data Manager.")
    st.page_link("views/data_manager.py", label="Open Data Manager", icon=":material/upload_file:")
    st.stop()

ind_full = T.indicator_frame(px)          # indicators on full history so long averages are warm
ranges = {"3M": 91, "6M": 182, "1Y": 365, "3Y": 1095, "5Y": 1826, "Max": None}
c1, c2, c3 = st.columns([2.6, 1.4, 2.6], vertical_alignment="bottom")
rng = c1.segmented_control("Range", list(ranges), default="1Y", key=f"ta_rng") or "1Y"
style = c2.segmented_control("Chart", ["Candles", "Line"], default="Candles", key="ta_style") or "Candles"
overlays = c3.multiselect("Overlays", ["SMA 20", "SMA 50", "SMA 200", "EMA 20", "Bollinger bands"],
                          default=["SMA 50", "SMA 200"], key="ta_ovl")
days = ranges[rng]
mask = px["date"] >= px["date"].max() - pd.Timedelta(days=days) if days else pd.Series(True, index=px.index)
view, ind = px[mask].reset_index(drop=True), ind_full[mask].reset_index(drop=True)

ov = {}
for o in overlays:
    if o == "Bollinger bands":
        ov["BB upper"], ov["BB lower"] = ind["BB Upper"], ind["BB Lower"]
    else:
        ov[o] = ind[o]
st.plotly_chart(C.price_chart(view, ov, candles=style == "Candles", height=500), width="stretch", config=C.config())
dtypes = px["data_type"].dropna().unique().tolist()
ui.source_footer(px["source"].dropna().unique(), pd.to_datetime(px["fetched_at"]).max(),
                 period=f"{F.fdate(px['date'].min())} to {F.fdate(px['date'].max())} (daily)",
                 extra="Prices are not adjusted for dividends; splits/bonus adjustments follow the provider." +
                       (" SAMPLE prices are simulated." if "sample" in dtypes else ""))

c1, c2 = st.columns(2, gap="large")
c1.plotly_chart(C.indicator_panel(ind["date"], {"RSI 14": ind["RSI 14"]}, "RSI (14) - Wilder", bands=(30, 70)),
                width="stretch", config=C.config())
c2.plotly_chart(C.indicator_panel(ind["date"], {"Histogram": ind["Histogram"], "MACD": ind["MACD"], "Signal": ind["Signal"]},
                                  "MACD (12, 26, 9)", bars="Histogram"), width="stretch", config=C.config())

# ------------------------------------------------------------------ statistics
st.markdown("##### Returns and risk")
close, dates = px["close"], px["date"]
last_year = px[px["date"] >= px["date"].max() - pd.Timedelta(days=365)]
beta_val, corr, nobs = None, None, 0
bench_note = ""
if company.get("is_sample"):
    bench_note = "Beta not computed for sample companies (no real benchmark relationship)."
else:
    bench = repo.get_prices(config.BENCHMARK)
    if not bench.empty:
        s = last_year.set_index("date")["close"]
        b = bench.set_index("date")["close"]
        beta_val, corr, nobs = T.beta(s, b)
        bench_note = f"Beta vs NIFTY 50 on {nobs} overlapping daily returns (last 12 months)."
    else:
        bench_note = "Benchmark prices unavailable (offline?) - beta not computed."
ui.kpis([
    {"label": "1M return", "value": F.pct(T.period_return(close, dates, 30), signed=True)},
    {"label": "3M return", "value": F.pct(T.period_return(close, dates, 91), signed=True)},
    {"label": "1Y return", "value": F.pct(T.period_return(close, dates, 365), signed=True)},
    {"label": "3Y return", "value": F.pct(T.period_return(close, dates, 1095), signed=True)},
    {"label": "Volatility (1Y, ann.)", "value": F.pct(T.annualised_volatility(last_year["close"])),
     "help": "Standard deviation of daily returns × √252"},
    {"label": "Max drawdown (1Y)", "value": F.pct(T.max_drawdown(last_year["close"])), "help": "Largest peak-to-trough fall"},
    {"label": "Beta vs NIFTY 50", "value": F.num(beta_val), "help": "Cov(stock, index) / Var(index) of daily returns"},
    {"label": "ATR (14)", "value": F.inr(ind_full["ATR 14"].iloc[-1]), "help": "Average true range - typical daily price movement"},
])
st.caption(bench_note + " Returns are price returns (excluding dividends).")

c1, c2 = st.columns(2, gap="large")
dd = pd.DataFrame({"Drawdown": ind["Drawdown"].values * 100}, index=ind["date"])
c1.plotly_chart(C.lines(dd, "Drawdown from previous peak (%)", ysuffix="%", markers=False, height=260),
                width="stretch", config=C.config())
vv = pd.DataFrame({"20-day volatility": ind["Volatility 20D"].values * 100}, index=ind["date"])
c2.plotly_chart(C.lines(vv, "Rolling 20-day annualised volatility (%)", ysuffix="%", markers=False, height=260),
                width="stretch", config=C.config())

st.markdown("##### Indicator readings (latest)")
rd = T.readings(ind_full)
st.dataframe(pd.DataFrame(rd).drop(columns="tone"), hide_index=True, width="stretch")
ui.note("Technical indicators summarise past price behaviour. They are descriptive readings, not buy/sell signals, "
        "and should be considered alongside fundamentals and risk.", "info")
with st.expander("Indicator formulas", icon=":material/function:"):
    for f in ["SMA(n) = average of the last n closing prices; EMA gives more weight to recent prices (α = 2/(n+1))",
              "RSI = 100 - 100 / (1 + RS), RS = Wilder-smoothed average gain / average loss over 14 days",
              "MACD = EMA(12) - EMA(26); Signal = EMA(9) of MACD; Histogram = MACD - Signal",
              "Bollinger bands = SMA(20) ± 2 × standard deviation(20)",
              "ATR = Wilder average of true range = max(High-Low, |High-prev close|, |Low-prev close|)",
              "Beta = Cov(r_stock, r_index) / Var(r_index) on daily returns"]:
        ui.formula(f)
