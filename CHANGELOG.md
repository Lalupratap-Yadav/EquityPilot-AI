# Changelog

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
