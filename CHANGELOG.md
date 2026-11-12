# Changelog

## [2.3.0] – 13 Nov 2026 – One source of truth for prices
### Fixed
- **Index tiles and charts showed different numbers** (e.g. SENSEX tile 81,879.40 +0.95% "as of 11 Nov" against the chart's 81,911.01 +0.04%). After midnight Yahoo's daily row for the last session has an empty close until it is finalised. The tiles dropped that row and showed the day before, while the chart used intraday data.
  - Tiles now take the latest value and previous close from the shared quote cache, the same one the charts, company headers and quote board use.
  - The daily history is used only for the sparkline, with today's value appended.
- **Charts end on the same price as the tiles.** The chart endpoint merges the shared quote into its last point: it updates the current intraday bar, appends today's point when the daily row is missing, or updates the current weekly bar. The page also passes the quote it already shows into the chart header, so the two numbers are identical even between refreshes.
- **Bad ticks from the provider** (seen on SENSEX and INDIA VIX in the 15:20–15:30 closing-price window: a 0.9% drop and recovery within 5 minutes):
  - Bars that jump away and straight back by far more than normal are removed.
  - The bar after such a spike has its open and wick corrected, and only extreme wicks are capped elsewhere.
  - The latest value and daily data are never altered, and the chart footer states how many bars were filtered.

### Improved
- **1D chart:** the time axis spans the whole session, 09:15–15:30, as on Groww and Kite. The cards show Open, Previous close, Day high and Day low.
- **Other ranges** always show four cards: period high, period low, largest fall, and yearly volatility or the start-of-period value.
- **Market Tracker:** skeleton tiles while loading, the index name shown instead of the raw symbol, and the "As of" subtitle removed (the chart header shows the session).
- Long index names on the Home tiles are truncated instead of wrapping.

### Tests
- 5 new tests: merging a quote into daily, weekly and intraday bars; index tiles using the shared quote; and the bad-tick filter, which removes a spike but keeps a genuine sustained move.
- Live check: all 17 index tiles matched their 1D and 1Y chart values and 1D change exactly, as did the headers and charts for TCS, RELIANCE and HDFCBANK.

## [2.2.0] – 12 Nov 2026 – Price charts rebuilt
### Fixed
- **Daily charts were one day early for every company and index.** Daily bars were converted to UTC (IST midnight is 18:30 UTC the day before) and then cut to a date, so a 12 Nov close was plotted on 11 Nov. Daily and weekly bars now carry the exchange (IST) date, and intraday bars stay UTC and are shown in IST.
- Sample companies ignored the selected range (1M, 6M and 1Y all showed 3 years).
- The 1D change for indices was measured from the first bar because index quotes have no previous close. It now uses the previous session's daily close, so the chart matches the index tiles.
- Yearly volatility on the "All" range used √252 on weekly bars, which overstated it by about 2.2×. Volatility is now annualised by the actual bar spacing.
- Moving averages, RSI, MACD and Bollinger bands on 3M–3Y charts are computed on 5 years of closes and then trimmed, so a 200-day average spans the whole 1Y chart instead of starting 200 days in.

### New chart (`web/src/components/StockChart.tsx`), used on company pages and the Market Tracker
- **Simple mode** (default):
  - A large header shows the price and its change for the period. Hovering or dragging shows the price, change and date at that point.
  - One line coloured green or red against a single labelled dashed reference line: previous close on 1D, start of period otherwise.
  - No grid clutter or confusing last-price line, and the page scroll wheel is never captured by the chart.
- **Advanced mode:**
  - Candles, line or area; SMA 20/50/200, EMA 20, Bollinger bands, volume, and RSI (with 70/30 lines) and MACD panels.
  - An O/H/L/C/Vol readout on hover, plus drag-to-pan and pinch or axis zoom.
- Ranges 1D, 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y and All. Daily bars are now used up to 5 years and weekly bars for All (previously weekly and monthly).
- Smooth range switching: the previous chart stays visible, faded, while the new range loads, and the chart is not rebuilt. Bars are cached for 60 seconds (intraday) or 15 minutes (daily).
- **Every line is named** in a legend with an explanation, and a "How to read this chart" panel explains the line, colours, reference line, volume, candles and each indicator in plain English.
- Period high, period low, largest fall and yearly volatility are shown, with volatility hidden for intraday ranges.
- The TradingView logo no longer overlaps the price. Attribution is a "Charts by TradingView" link under each chart, as the library licence allows.
- The old `PriceChart` component was removed.

### Tests
- 11 new tests (`tests/test_charts.py`): IST dates for daily bars (regression), UTC for intraday bars, sample range slicing, baseline and change arithmetic, the previous close on 1D, weekly volatility annualisation and the range alias.

## [2.1.0] – 12 Nov 2026 – Research depth, plain-English explanations and source trust
### Valuation
- **Summary tab** in the Valuation Lab: an estimated-value range chart that compares DCF (FCFF, with the bear-to-bull range), DCF (FCFE), peer-median P/E, P/B and EV/EBITDA, and the company's own median P/E and P/B against the market price. A permanent notice says these are model estimates, not the stock's true or exact value.
- **FCFE model** (Damodaran's target-debt-ratio form): FCFE = Net profit − (Capex − D&A + ΔNWC) × (1 − debt-funded share), discounted at the cost of equity. It shares growth and reinvestment assumptions with the FCFF tab, and defaults come from the 3-year net margin and the book debt ratio.
- **Margin of safety** = (estimated value − price) / estimated value. It appears on both DCF tabs, in the summary (with a slider that shows the price giving a chosen cushion) and in the PDF report.
- **Historical multiple bands:** current P/E and P/B against their fiscal-year-end median, low and high, plus the implied value at the median multiple.
- Labels changed from "intrinsic value" to "estimated value" in the web app, the classic workbench and the PDF.

### Financial analysis
- **Working-capital ratios:** payable days, cash conversion cycle and net working capital / revenue. A new `payables` line item is mapped from the provider. The cycle stays blank unless all three inputs are reported, and missing values are never treated as zero.
- **Plain-English metric guide** (`equitypilot/content/metrics_guide.py`) with four parts for 33 metrics: what it means, why it matters, how to read it, and an example.
  - Click any ratio, or a key stat on the company overview or in Compare, to open the explanation with the company's value and a history chart.
- **Benchmark ratings** (Strong / Moderate / Weak, always with a text label) for annual figures only, and only where a widely used rule of thumb exists: ROE, ROCE, D/E, interest coverage, net debt/EBITDA, current ratio, CFO/net profit and growth.
  - Valuation multiples are never rated.
  - Leverage, liquidity and cash-flow ratings are skipped for banks and NBFCs.
- **"Financial health at a glance"** card on the Ratios view.

### Industries
- A **Government policy & regulation** section for all 15 industries (`equitypilot/content/policies.py`). It covers 53 long-standing laws, schemes and regulators, each with the official website. Every link was checked to respond, and unreachable ones were replaced with the current official domain.

### News and source trust
- **Source tiers** (`equitypilot/data/source_tiers.py`):
  - OFFICIAL: exchange, regulator or government.
  - SECONDARY: an established news organisation or wire.
  - UNRATED: tip sites, blogs and aggregators.
- Unrated headlines are hidden by default, with a "show them" toggle and a count, and they are excluded from the AI assistant's evidence and the industry news panel.
- The News page has a source-label legend and an **Official sources** directory (NSE, BSE, SEBI, RBI, MOSPI, PIB). It explains that only publisher-offered feeds are fetched and other official sites are linked, not scraped.

### Compare
- New rows: 1-year price return and the latest entered shareholding (promoter, FII/FPI, DII). Rows are shown only when data exists.
- A **Strengths and points to check** card for each company, built from the benchmark ratings, plus the three main risks of each company's industry.

### Tests
- 23 new tests (`tests/test_research_quality.py`): the FCFE hand calculation (₹97.50 per share) and error cases, margin of safety, multiple bands, working-capital ratios (blank when payables are missing), benchmark ratings, guide coverage of every ratio, source tiers, hiding unrated headlines including from the AI context, and the new API fields.

## [2.0.0] – 12 Nov 2026 – Platform upgrade
### Architecture
- FastAPI backend (`api/`) and React 19 / TypeScript / Vite / Tailwind v4 frontend (`web/`), served from one process. The tested Python core (`equitypilot/`) is reused unchanged, and the Streamlit app remains as the "classic workbench".
- Guest sessions (signed cookie) and optional accounts (scrypt). All user data is stored per user.
- Security: rate limiting, input validation, security headers (pure ASGI middleware) and PDF-only uploads with size and magic-byte checks. Documents are readable only by their owner, including in search and the assistant.
- Dockerfile (two-stage, non-root, health check) and `.dockerignore`.

### Data
- Securities master with 5,552 NSE securities: the AMFI large/mid/small-cap list plus NSE `EQUITY_L.csv`, with search.
- Official feeds: NSE announcements and results RSS (mapped to companies), RBI and SEBI RSS, and Yahoo market headlines. A failed download backs off for 10 minutes, and one download runs per feed at a time.
- Market-data provider interface (Yahoo, delayed): quote cache, intraday bars, 17 indices, corporate actions, and WebSocket quote push.
- Tracked universe expanded to 121 real companies across 15 industries.

### Features
- Pages:
  - **Discover:** Home, Explore, Industry Intelligence Centre (15 industries), Market Tracker.
  - **Company:** Company page with 11 tabs.
  - **Research:** Equity Research workspace, Valuation Lab, Screener (saved screens), Compare, News & Market Intelligence, AI Assistant, Documents, Reports.
  - **My space:** Watchlists (multiple, with notes and price alerts), Portfolio, Virtual Invest.
  - **Learn:** Learning Centre (quizzes with saved progress, glossary), How to Use, Settings.
- **Virtual Invest:**
  - ₹10,00,000 of virtual money per user.
  - Checks against overspending and overselling.
  - Split and dividend adjustments.
  - Performance vs NIFTY 50.
  - Achievements, educational tips, an opt-in leaderboard and reset.
- Document question-answering: BM25 passage retrieval with page numbers, and answers cite numbered document sources.
- Shareholding-pattern entry, validated to a total of 100% and labelled user-entered.
- Search palette (Ctrl+K or /), dark/light theme, and mobile layout with no horizontal scrolling.

### Fixes and hardening
- Universe metrics are now stale-while-revalidate and persisted to disk. A cold start serves Explore and Screener in under 0.5 s (previously up to minutes).
- Market movers no longer fail when some quotes are missing (numeric coercion).
- Creating a paper account is idempotent, so parallel first requests no longer cause a 500.
- The frontend establishes the session before its parallel queries, so a first visit creates one guest instead of several.
- A server-wide `ANTHROPIC_API_KEY` is used only when `EQUITYPILOT_SHARED_AI_KEY=1`. Otherwise each user supplies their own key.

## [1.1.0] – 12 Nov 2026
- Quarterly results view; bank metrics (NIM, GNPA/NNPA, PCR, CRAR, CASA, cost-to-income, credit cost);
  sample bank; formatted Excel exports; `python -m equitypilot` CLI refresh.

## [1.0.0] – 11 Nov 2026
- Streamlit research platform: dashboard, company research, financials, valuation (DCF, scenarios,
  sensitivity, reverse DCF, justified P/B), screener, comparison, technicals, risk, news & disclosures,
  grounded AI assistant, PDF reports, portfolio, learning centre, guide, data manager; 106 tests.
