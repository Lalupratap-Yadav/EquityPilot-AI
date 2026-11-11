"""Company Comparison: 2-5 companies side by side on financial, operating and valuation metrics."""
import pandas as pd
import streamlit as st

from equitypilot import config
from equitypilot import formatting as F
from equitypilot.analytics import ratios as R
from equitypilot.analytics.screener import METRIC_COLUMNS, company_metrics
from equitypilot.data import repository as repo
from equitypilot.ui import charts as C
from equitypilot.ui import components as ui

ui.page_header("Company Comparison", "Compare two to five companies on growth, profitability, balance sheet and valuation")

comps = repo.list_companies()
if comps.empty:
    ui.empty_state("No companies", "Add companies on the Dashboard first.")
    st.stop()
names = dict(zip(comps["symbol"], comps["name"]))
default = st.session_state.get("compare_symbols")
if not default:
    active = ui.current_symbol()
    default = ([active] if active else []) + [p for p in (repo.get_peers(active) if active else []) if p in names][:2]
    if len(default) < 2:
        default = comps["symbol"].tolist()[:3]
chosen = st.multiselect("Companies (2-5)", comps["symbol"].tolist(), default=[d for d in default if d in names][:5],
                        format_func=lambda s: f"{names.get(s, s)} ({s})", max_selections=5, key="cmp_sel")
st.session_state.compare_symbols = chosen
if len(chosen) < 2:
    ui.empty_state("Select at least two companies", "Pick companies from the list above.")
    st.stop()

rows = pd.DataFrame([company_metrics(s) for s in chosen])
short = {r["symbol"]: (r["name"].replace(" Limited", "").replace(" Ltd", "")[:26]) for _, r in rows.iterrows()}
if rows["is_sample"].any() and not rows["is_sample"].all():
    ui.note("You are comparing fictional SAMPLE companies with real companies. The sample figures are generated "
            "and not meaningful against real data.", "warn")
if rows["is_financial"].any() and not rows["is_financial"].all():
    ui.note("The selection mixes financial and non-financial companies. Leverage, liquidity and EV-based metrics "
            "are not comparable across the two (shown as '—' for financials).", "info")
fys = rows["latest_fy"].dropna().map(lambda d: pd.Timestamp(d).strftime("%b %Y")).unique()
if len(fys) > 1:
    ui.note("Latest fiscal year-ends differ (" + ", ".join(fys) + "). Ratios compare different periods.", "info")
non_inr = rows[rows.get("currency", pd.Series("INR", index=rows.index)).fillna("INR") != "INR"]
if len(non_inr):
    ui.note(", ".join(non_inr["name"]) + ": the provider reports statements in "
            + ", ".join(non_inr["currency"].unique()) + " while prices are in INR, so price multiples and rupee "
            "amounts are not shown (ratios such as ROE and margins are currency-neutral and remain valid).", "info")
bases = rows["basis"].unique()
if len(bases) > 1:
    ui.note("Statement bases differ (" + ", ".join(bases) + ") - consolidated and standalone figures are not directly comparable.", "info")

# ------------------------------------------------------------------ table
groups = {
    "Valuation": ["price", "market_cap", "pe", "pb", "ev_ebitda", "dividend_yield"],
    "Growth": ["revenue_growth", "net_income_growth", "revenue_cagr_3y", "profit_cagr_3y"],
    "Profitability & returns": ["ebitda_margin", "net_margin", "roe", "roce"],
    "Balance sheet & cash flow": ["debt_to_equity", "interest_coverage", "current_ratio", "cfo_to_net_income", "fcf_margin"],
    "Scale": ["revenue", "net_income"],
    "Quality score": ["piotroski"],
}
higher_better = {"pe": False, "pb": False, "ev_ebitda": False, "debt_to_equity": False}
table, sections = {}, []
for g, keys in groups.items():
    table[g] = [""] * len(rows)
    sections.append(g)
    for k in keys:
        lbl, kind = METRIC_COLUMNS[k]
        vals = rows[k]
        cells = [F.by_kind(v, kind) for v in vals]
        num = pd.to_numeric(vals, errors="coerce")
        if num.notna().sum() >= 2 and k not in ("price", "market_cap", "revenue", "net_income"):
            best = num.idxmax() if higher_better.get(k, True) else num[num > 0].idxmin() if (num > 0).any() else None
            if best is not None:
                cells[best] = cells[best] + " ★"
        table[lbl] = cells
t = pd.DataFrame(table, index=[short[s] for s in rows["symbol"]]).T
t.index.name = "Metric"
ui.fin_table(t, sections=sections, negative_red=True)
st.caption("★ = most favourable value in the group (lowest for valuation multiples and leverage, highest otherwise). "
           "A favourable number is a prompt for investigation, not a conclusion.")
export = rows.set_index("symbol")[list(METRIC_COLUMNS)].T
ui.download_csv(export, "comparison.csv", "Download comparison (CSV)")

# ------------------------------------------------------------------ charts
st.markdown("##### Visual comparison")
c1, c2 = st.columns(2, gap="large")
with c1:
    df = pd.DataFrame({"ROE": rows["roe"] * 100, "ROCE": rows["roce"] * 100}).set_axis([short[s] for s in rows["symbol"]])
    st.plotly_chart(C.grouped_bars(df, "Return ratios (latest FY, %)", ysuffix="%", yfmt=".0f", hover_fmt=".1f"),
                    width="stretch", config=C.config())
with c2:
    df = pd.DataFrame({"EBITDA margin": rows["ebitda_margin"] * 100, "Net margin": rows["net_margin"] * 100}).set_axis(
        [short[s] for s in rows["symbol"]])
    st.plotly_chart(C.grouped_bars(df, "Margins (latest FY, %)", ysuffix="%", yfmt=".0f", hover_fmt=".1f"),
                    width="stretch", config=C.config())

c1, c2 = st.columns(2, gap="large")
with c1:
    rev = {}
    for s in chosen:
        fd = repo.get_financials(s, auto_refresh=False)
        if not fd.empty:
            r = fd.get("revenue")
            base = r.dropna()
            if len(base) and base.iloc[0] > 0:
                rev[short[s]] = pd.Series((r / base.iloc[0] * 100).values,
                                          index=[pd.Timestamp(p).year for p in r.index])
    if rev:
        df = pd.DataFrame(rev).sort_index()
        df.index = [f"FY{y}" if y else y for y in df.index]
        st.plotly_chart(C.lines(df, "Revenue indexed to 100 (first available year)", height=340),
                        width="stretch", config=C.config())
        st.caption("Indexing puts companies of different size on one scale. Index labels use the calendar year of each fiscal year-end.")
with c2:
    px = {}
    for s in chosen:
        p = repo.get_prices(s, auto_refresh=False)
        if not p.empty:
            p = p[p["date"] >= p["date"].max() - pd.Timedelta(days=365)]
            px[short[s]] = pd.Series(p["close"].values / p["close"].iloc[0] * 100, index=p["date"].values)
    if px:
        df = pd.DataFrame(px).sort_index().ffill()
        st.plotly_chart(C.lines(df, "Price performance, last 12 months (rebased to 100)", markers=False, height=340),
                        width="stretch", config=C.config())
        st.caption("Price return only (dividends excluded).")

src = sorted({config.DATA_TYPES[t][0] for t in rows["data_type"]})
ui.source_footer(["Calculated by EquityPilot", config.YAHOO_SOURCE if "THIRD-PARTY" in src else None,
                  config.SAMPLE_SOURCE if "SAMPLE" in src else None],
                 extra="Each company uses its own latest fiscal year; P/E uses TTM earnings where available.")
