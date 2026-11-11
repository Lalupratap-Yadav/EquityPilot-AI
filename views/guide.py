"""How to Use: interactive quick-start tour, module guides, data labels and FAQ."""
import streamlit as st

from equitypilot import config, db
from equitypilot.ui import components as ui

ui.page_header("How to Use EquityPilot", "A guided tour of every feature - start here if this is your first visit")

TOUR = [
    ("explore", "Open a sample company", "Choose 'Beta Infotech Ltd (Sample)' in the sidebar. Sample companies are fictional and work offline.", "views/company.py"),
    ("add", "Add a real company", "On the Dashboard, type an NSE symbol (e.g. INFY) and click 'Add & open'. Data comes from Yahoo Finance (delayed).", "views/dashboard.py"),
    ("fin", "Read the financials", "Financial Analysis → switch between Statements, Ratios & DuPont, Trends and Data quality.", "views/financials.py"),
    ("val", "Build a DCF", "Valuation → DCF tab. Adjust WACC and growth, then 'Save this valuation for the research report'.", "views/valuation.py"),
    ("screen", "Screen the universe", "Stock Screener → try the 'Quality compounders' preset, then select 2-5 rows and click 'Compare selected'.", "views/screener.py"),
    ("risk", "Review risks", "Risk Analysis → read each flag with its threshold; add your own risk notes.", "views/risk.py"),
    ("ask", "Ask the assistant", "AI Research Assistant → click a suggested question. Answers cite numbered sources.", "views/assistant.py"),
    ("report", "Generate a PDF report", "Report Generator → add your thesis and click 'Generate PDF report'.", "views/report.py"),
    ("learn", "Test yourself", "Learning Centre → pick a module and take its quiz.", "views/learning.py"),
]

done = set(db.get_setting("tour_done", []) or [])
st.progress(len(done & {t[0] for t in TOUR}) / len(TOUR), text=f"Quick-start tour: {len(done & {t[0] for t in TOUR})} of {len(TOUR)} steps done")
tab_tour, tab_mod, tab_data, tab_faq = st.tabs(["Quick-start tour", "Module guide", "Data & labels", "FAQ"])

with tab_tour:
    for key, title, text, page in TOUR:
        c1, c2, c3 = st.columns([0.6, 6, 2], vertical_alignment="center")
        checked = c1.checkbox(" ", value=key in done, key=f"tour_{key}", label_visibility="collapsed")
        c2.markdown(f"**{title}**  \n{text}")
        c3.page_link(page, label="Open", icon=":material/arrow_forward:")
        if checked != (key in done):
            done = (done | {key}) if checked else (done - {key})
            db.set_setting("tour_done", sorted(done))
            st.rerun()

with tab_mod:
    GUIDE = {
        "Dashboard": ("views/dashboard.py", ["Indices: NIFTY 50, SENSEX, sector indices and India VIX (delayed, cached 15 minutes).",
                                            "Find a company: enter an NSE symbol (INFY), 'NSE:TATAPOWER' or a numeric BSE code (500325).",
                                            "Load default research universe: fetches ~44 large NSE companies for the screener (2-4 minutes).",
                                            "Watchlist: add companies, select a row to open or remove it.",
                                            "Highlights: gainers, losers and sector moves among the companies you have loaded."]),
        "Company Research": ("views/company.py", ["Overview: key valuation and return metrics with formulas in the ⓘ tooltips.",
                                                 "Business & segments: write your business-model notes and enter segment revenue from the annual report.",
                                                 "Shareholding: enter the quarterly pattern from the exchange filing; pledges are flagged.",
                                                 "Peers: auto-suggested by industry - edit and save; open a full comparison.",
                                                 "Official sources: direct links to NSE, BSE and SEBI pages for verification."]),
        "Financial Analysis": ("views/financials.py", ["Choose annual/quarterly and the statement basis (consolidated, standalone or provider basis).",
                                                      "Statements: values in ₹ crore; download Excel/CSV.",
                                                      "Ratios & DuPont: 25 ratios with formulas, DuPont decomposition and the Piotroski F-score.",
                                                      "Data quality: balance-sheet checks, missing items, irregular periods, currency notes."]),
        "Valuation": ("views/valuation.py", ["Multiples: P/E, P/B, EV/EBITDA with history at each fiscal year-end.",
                                            "DCF: set CAPM inputs (risk-free rate, beta, ERP), operating assumptions and see every step from FCFF to value per share.",
                                            "Scenarios & sensitivity: bear/base/bull shifts, WACC × growth grid and reverse DCF (implied growth).",
                                            "Relative to peers: implied prices from peer median multiples.",
                                            "Banks: justified P/B = (ROE - g) / (Ke - g)."]),
        "Technical Analysis": ("views/technicals.py", ["Candlestick or line chart with SMA/EMA/Bollinger overlays and volume.",
                                                      "RSI and MACD panels; returns, volatility, drawdown, beta vs NIFTY 50.",
                                                      "Readings are descriptive, not trading signals."]),
        "Risk Analysis": ("views/risk.py", ["Composite score from transparent checks: debt, liquidity, profitability, cash flow, concentration, market.",
                                           "Altman Z'' with its components; sector considerations; your own risk notes."]),
        "News & Disclosures": ("views/news.py", ["Fetch third-party headlines (Yahoo aggregator) with publisher and time.",
                                               "Log exchange disclosures (results, board meetings, ratings) with the filing link.",
                                               "See documents uploaded for this company."]),
        "Stock Screener": ("views/screener.py", ["Presets or custom min/max filters on quality, growth, leverage and valuation.",
                                                "Missing data is excluded by default (toggle to keep).",
                                                "Select rows to open, compare (2-5) or add to the watchlist; export CSV."]),
        "Company Comparison": ("views/compare.py", ["Side-by-side table with ★ for the most favourable value; warnings when periods, bases or currencies differ.",
                                                    "Charts: returns, margins, revenue indexed to 100, 12-month price performance."]),
        "AI Research Assistant": ("views/assistant.py", ["Default engine is the free offline analyst - deterministic and fully sourced.",
                                                        "Optional: Claude API (paid, your own key) or Ollama (free, local). Costs are shown before you enable it.",
                                                        "Select uploaded PDFs to ask about annual reports; answers cite page numbers.",
                                                        "Recommendation requests are declined with an explanation."]),
        "Report Generator": ("views/report.py", ["Save a DCF and write notes first for a richer report.",
                                                "Add your thesis; choose sections; download the PDF (a copy is kept in data/reports)."]),
        "Portfolio Analysis": ("views/portfolio.py", ["Enter lots (quantity, cost, buy date) or import CSV; or load the sample portfolio.",
                                                     "Value, P&L, XIRR, allocation by stock and sector, concentration warnings.",
                                                     "Risk: volatility, Sharpe, drawdown, beta, diversification ratio, risk contribution, correlation."]),
        "Data Manager": ("views/data_manager.py", ["See every source, its access method and what is cached.",
                                                  "Upload statements (template provided) → review/correct → save with source reference.",
                                                  "Upload NSE/BSE price CSVs; upload PDFs for text search and the assistant.",
                                                  "Choose which companies are in the screener universe; refresh data."]),
        "Learning Centre": ("views/learning.py", ["Eight modules with formulas, live worked examples and quizzes; glossary search; progress tracking."]),
    }
    pick = st.selectbox("Module", list(GUIDE))
    page, steps = GUIDE[pick]
    for i, s in enumerate(steps, 1):
        st.markdown(f"{i}. {s}")
    st.page_link(page, label=f"Open {pick}", icon=":material/open_in_new:")

with tab_data:
    st.markdown("##### Every number carries a label")
    st.html("<div>" + "".join(f"<p style='margin:6px 0'>{ui.badge(k)} <span style='font-size:.88rem;color:#334155'>{ui.esc(v[1])}</span></p>"
                              for k, v in config.DATA_TYPES.items()) + "</div>")
    st.markdown("""##### Where data comes from
- **Yahoo Finance (via yfinance)** - delayed quotes, price history, summarised statements (4-5 years), headlines. Secondary source.
- **Your uploads** - figures from annual reports, results and exchange filings, stored with the source you cite.
- **Official websites** (NSE, BSE, SEBI, RBI, MOSPI, company IR) - linked for verification; not scraped.
- **Sample dataset** - four fictional companies so the app works offline and for demos.

##### Statement basis
*Consolidated* includes subsidiaries; *standalone* is the listed entity alone. Yahoo does not label its basis (generally consolidated), so EquityPilot shows "basis not stated" and never mixes bases in one table.""")

with tab_faq:
    FAQ = [
        ("Why isn't NSE data fetched live?", "NSE does not provide a public developer API and blocks automated access to its website. "
         "EquityPilot respects this: it links to NSE pages and lets you upload downloaded files instead."),
        ("Are prices real-time?", "No. Quotes come from Yahoo Finance and may be delayed by 15 minutes or more. Every price shows its timestamp."),
        ("Why are some values shown as '—'?", "The source did not report them, or a ratio is not meaningful (e.g. EV/EBITDA for banks, growth from a negative base). EquityPilot never fills gaps with estimates."),
        ("Why are Infosys/HCLTech multiples blank?", "The provider reports their statements in USD while prices are in INR. Ratios still work; upload INR statements from the annual report to enable P/E and DCF."),
        ("Does the AI cost money?", "The default offline analyst is free. The Claude API is optional and billed per use to your own Anthropic account (Claude Pro does not include API credits); costs are shown before you enable it. Ollama is free and runs locally."),
        ("Can the assistant tell me what to buy?", "No. It explains evidence and calculations. Issuing recommendations in India requires SEBI registration."),
        ("Where is my data stored?", f"In a local SQLite database ({config.DB_PATH.name}) in the project's data folder. API keys are never stored."),
        ("How do I reset everything?", "Stop the app and delete the data folder's equitypilot.db file; sample data reloads on the next start."),
    ]
    for q, a in FAQ:
        with st.expander(q):
            st.write(a)
