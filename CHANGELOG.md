# Changelog

## [2.6.0] – 15 Nov 2026 – Accuracy, official events and transparency
### Fixed
- **Wrong company news (the Microsoft story under TCS).** Yahoo's per-company headline stream carries stories about other
  companies and the whole sector. A headline is now attached to a company only when the company is clearly named in the
  headline or the publisher's summary (new `equitypilot/data/entities.py`):
  - group words never match on their own ("Tata", "Reliance", "HDFC", "Bajaj", "Mahindra", "Adani", ...);
  - foreign parents never stand in for the Indian company ("Nestle", "Suzuki", "Unilever", "Colgate", "Vodafone");
  - the longest name wins and other listed entities block shorter matches ("Tech Mahindra" is not M&M, "HDFC Life" is not
    HDFC Bank, "ITC Hotels" is not ITC, "Bajaj Housing Finance" is not Bajaj Finance, "SBI Capital" is not SBI);
  - subsidiaries count only where the relationship is public record (Jio Platforms and Reliance Retail → Reliance Industries,
    Novelis → Hindalco, Royal Enfield → Eicher Motors), and the item says it was matched through the subsidiary.
  Headlines that do not name the company are kept as general market news. Older stored headlines are re-checked the same
  way, and the AI assistant and PDF reports see only verified company headlines.
- **Virtual Invest and splits.** The data provider restates history for every later split (bonus issues appear as splits):
  - dividends paid before a split were credited at the restated, smaller amount (verified on TCS: Yahoo lists ₹0.375 for
    the ₹3 dividend actually paid in 2004); they are now converted back to the amount paid on the day;
  - the performance chart valued pre-split holdings at split-adjusted prices, and could count a split twice when the price
    history had not caught up yet; each day's price is now expressed in that day's share units.
- **Search.** An exact symbol could be cut off when hundreds of names contained it ("TRU"); exact symbol, ISIN and
  name-prefix matches are now fetched first. Companies listed twice under an old and new ISIN (after a split) are merged,
  preferring the NSE listing. Matches inside another word no longer pad the list ("tcs" no longer shows West Coast
  Paper). Typo matching runs only when nothing matches. Common short names work ("l&t", "hul", "ril", "sbi").
- The Virtual Invest leaderboard no longer shows how many stocks a user holds - only the chosen display name and return.
- Prompts that asked why you are watching a company or what your thesis is were reworded (privacy).

### Added
- **Earnings & Results** (`/earnings`): confirmed result dates from companies' board-meeting intimations (NSE board-meetings
  feed and announcements, merged per meeting), results as they are filed ("Outcome of board meeting", delay notices shown
  separately), list and calendar views, company / sector / tracked filters, and each company's quarterly history with
  QoQ and YoY growth. Dates are never estimated; no earnings surprise is shown because no estimate source is connected.
- **Corporate Actions** (`/corporate-actions`): dividends, splits, bonus, rights, buybacks and schemes from the NSE
  corporate-actions feed with exchange ex-date and record date (payment dates are not in the feed and are never guessed),
  board announcements whose dates are still to come, a company dividend/split history (provider data, labelled
  THIRD-PARTY), and plain-English explanations.
- **Data Quality & Sources** (`/data-quality`): status of every feed (label, refresh interval, last success, failures,
  items kept), market-data provider and quote freshness, statement coverage, EPS consistency warnings, the label glossary
  (OFFICIAL, SECONDARY, THIRD-PARTY, DELAYED, HISTORICAL, CALCULATED, ASSUMPTION, SAMPLE, USER-ENTERED) and a per-company
  coverage table. Company pages show a "Data coverage n/m" link.
- **EPS consistency checks** in the statement quality checks: diluted EPS above basic EPS, and reported EPS far from net
  profit / diluted shares. It flags the known HDFC Bank FY2023 issue.
- **Financial Health** tab on company pages: growth, profitability, debt, liquidity, cash flow, capital efficiency and
  valuation context, each with its metrics, formulas, period and documented rating rule. Banks and NBFCs use asset
  quality, capital and funding instead. Missing data shows "Insufficient data"; there is no overall score.
- Global search lists the new pages as research tools.
- **Frontend interaction tests** (Vitest + Testing Library, 19 tests; `npm test` in `web/`).
- 39 backend tests (`tests/test_trust_v26.py`): company identification with misleading headlines, earnings and actions
  parsing, health, coverage, quality, split accounting, search ranking and cross-user privacy.

### Changed
- Endpoints: `/api/events/results`, `/api/events/actions`, `/api/events/company/{symbol}`, `/api/data/quality`,
  `/api/companies/{symbol}/health`, `/api/companies/{symbol}/coverage`.
- Faster: Data Quality 8 s → 0.3 s (one query instead of one per company), company search 80-170 ms → 12-65 ms.

## [2.5.2] – 15 Nov 2026 – Premium visual refresh
Visual changes only. No new sections, and no changes to data, calculations or behaviour.

### Changed
- **Typography:** Inter's optical-size version, so large headings and prices use sharper display letterforms, with tighter heading spacing.
- **Surfaces:** a softer page background. Cards have layered shadows and lighter borders, with a subtle top highlight in dark mode.
- **Hover feedback:** index tiles, company cards, heat-map tiles and the Virtual Invest card lift slightly on hover. Market-mover rows highlight.
- **Hero banners** (Home summary and Virtual Invest): a deep gradient with a soft glow and a faint grid texture. The market clock pill reads clearly on the dark banner in both themes.
- **Navigation:**
  - The active item in the sidebar and the News section list is a soft brand tint with a brand-coloured icon, replacing the heavy black pill.
  - The phone tab bar shows a small indicator above the active tab.
- **Header:** frosted-glass bar, a softer search field with a key-cap shortcut hint, and a gradient profile avatar.
- **Logo:** gradient tile with a light sheen.
- **Controls:**
  - Primary buttons have a subtle gradient and inner highlight. Outline buttons and inputs have a hairline shadow.
  - Inputs show a softer, wider focus ring.
  - Segmented switches and tabs are refined.
  - Empty states have a tinted background.
- **Simple price chart:** the line now has a soft gradient fill underneath. The data, colours and hover readout are unchanged.
- **README screenshots** were regenerated from the current app: Home (light and dark), Company, Valuation Lab, Virtual Invest (desktop and phone) and the advanced chart.

## [2.5.1] – 13 Nov 2026 – Hardening
### Fixed
- **No crash screen:** a rendering error anywhere used to blank the whole site. Error boundaries now contain it to the page (or widget), with Reload / Try again / Home. After an update, an open tab that requests old page code reloads itself once.
- **Unknown `/api/...` addresses** returned the web page with status 200; they are now JSON 404s.
- **Offline mode still called Yahoo** from the chart endpoint; offline now never touches the network.
- **Unknown company symbols** returned 502 ("upstream error") when added; now 404 with the provider's message.
- **The ticker cut the last index in half** at some widths; indices are now shown whole or not at all.
- **News table growth:** NSE files about 9,000 announcements a day. Filings of untracked companies are pruned after 30 days and everything else after a year (daily, automatic). New database indexes speed up news queries.
- **Windows consoles:** log lines with ₹ or accented names can no longer raise encoding errors.
- **Requests piling up after a restart (index tiles took up to 139 s):** every page poll downloaded the same Yahoo data in parallel.
  - The quote cache now shares work per symbol: a symbol with a cached value answers at once; one never fetched waits only for the same symbol's fetch.
  - Index tiles are stale-while-revalidate: stored values come back instantly and refresh in the background.
  - Identical chart requests share one download, and the NIFTY 1D chart is pre-loaded at start-up.
  - Result: 15 simultaneous tile requests take under 1 s, and all page APIs answer in 0.2–1.9 s.

### Added
- **`start.bat`:** one-click Windows start (creates the environment, installs packages, builds the web app on the first run, opens the browser, detects an already-running server).
- A friendly page at `/` when the web app has not been built yet.

### Tests
- 15 new robustness tests: offline never uses the network; hostile inputs never cause a server error; unknown API path → 404; prune keeps tracked and recent items; concurrent requests share one provider call; stale tiles are served without waiting; an unrelated symbol never waits behind a big download.
- **API sweep (not in the suite):** every one of the 71 API paths was called with normal, missing and hostile inputs, 1,505 calls offline on a fresh database and 1,505 online on a copy of the real database. Result: no server errors.
- **Browser sweep:** 12 malformed addresses (unknown company, garbage symbol, unknown tab, section, industry or preset). Result: no JavaScript errors, and each shows a helpful message.
- The Streamlit page-test time limit was raised from 60 s to 180 s, so slow machines don't fail the suite.

## [2.5.0] – 13 Nov 2026 – Premium UI, intelligent search, trusted news
### Added
- **Global search (Ctrl+K or /):** one box for companies, indices, sectors, financial concepts, research tools and news. Results are grouped and ranked by match strength.
  - Typo tolerant ("Adani Enterprwses"), with aliases (SBI, L&T, HUL, Zomato).
  - Company preview: price, change, market cap, P/E and industry.
  - Recent searches and recently viewed companies; full keyboard navigation; an "Ask AI" fallback.
  - Database-backed, no AI involved; 65–100 ms inside the server.
- **News & Market Intelligence rebuilt:**
  - 13 sections: top, breaking (under 3 h only), Indian market, company, announcements, results, banking, economy & RBI, SEBI, sector, global, commodities & currency, IPO & corporate actions.
  - New sources: BSE notices, plus publisher RSS feeds from The Economic Times, Mint and Business Standard. Headline, short description and link only; switch off with `EQUITYPILOT_MEDIA_RSS=0`.
  - De-duplication: the earliest copy is kept and the other publishers are listed.
  - Filters by company, sector, source and date, sorted by latest or relevance; saved articles; related news.
  - A fact-only daily market summary.
  - "What this means" explanations that separate confirmed filings from media reports and flag tentative headlines.
- **Company page:** Valuation tab (multiples against the company's own history, implied prices, peer multiples) and Documents tab (your PDFs plus official filing links). Sections renamed to match investor language. A data-provenance line shows price time, source, statement basis, unit and latest fiscal year.
- **Simple / Advanced switch** in the header, for the whole app; switching keeps the page and company you are on.
- **Layout:** collapsible, regrouped sidebar; breadcrumbs; a compact Home hero; a ticker that never scrolls sideways.
- **Server:** request id (`X-Request-ID`) and timing logs for every API call, slow-request warnings and optional JSON logs (`EQUITYPILOT_LOG_JSON=1`). Feeds refresh in parallel and never block a page view.
- The glossary now includes every metric-guide concept, so every concept search result has an explanation page.

### Fixed
- **NIFTY header vs ticker:** the chart's big number showed the hovered point, so it could differ from the ticker. It now always shows the latest value with an "as of" time; the hovered point appears in the small tag with its own change.
- **Top news flooded by filings from small untracked companies:** it now ranks results, deals and dividends of tracked companies, mixed with market news and RBI/SEBI releases.
- **Older media and SEBI items vanished from news:** about 9,000 daily NSE filings crowded them out of the query window. Filings now load separately.
- **"&" deleted and "nbsp;" left in RSS headlines:** entities are now decoded properly.
- **Index tiles took 32 s after a restart:** the last tiles are now saved and served immediately while fresh data loads.
- **Daily summary took 41 s cold:** it now uses database counts.
- Change pills and data badges no longer wrap next to long company names.

## [2.4.1] – 13 Nov 2026 – Smarter company recognition, typo-tolerant search, Groww-style chart
### Fixed
- **AI did not recognise companies** such as "Compare Adani and Tata Power" and showed the help text. A new resolver understands:
  - names, brands, everyday names (SBI, L&T, HUL, Zomato) and symbols
  - multi-word names that contain common words ("State Bank of India", "HDFC Bank")
  - typos ("Relaince")
  - ambiguous brands: "Tata" uses the largest tracked company and lists the others
- **Search found nothing for typos** ("Adani Enterprwses"). It now corrects spelling against the company-name list and shows "Showing results for …".
- Compare works for companies that are not yet in the universe table, hides rows with no data and signs the day change.

### Improved
- **Simple chart redesigned** to the clean look of Groww and Kite: a single green or red line with no axes or grid, a faint dashed previous-close line, a floating "value | time" tag while hovering, and range buttons under the chart. Charts open on **1D** by default.
- Single-company answers start with a key-numbers table.

## [2.4.0] – 13 Nov 2026 – Live layer, research agent, premium UI
### Added
- **Market clock:** pre-open (09:00–09:15), open and closed phases, with "closes in" / "opens in" countdowns. Exchange holidays are detected from data: NIFTY 50 has not traded today 20 minutes after the open.
- **Auto-updating prices in session:** every index and every symbol someone has on screen is refreshed every 20 s, with one shared provider request for all viewers. The WebSocket now sends a snapshot and then only the quotes that changed.
- **Optional real-time quotes:** a Zerodha Kite Connect connector (your own paid app and daily token), off unless configured. If Kite fails, quotes fall back to delayed data. See docs/MARKET_DATA.md.
- **Research agent:**
  - Claude now plans its own research with 9 grounded tools (find company, research pack, price performance, compare, screen, market overview, news, documents, metric guide).
  - Answers stream into the page, citing tool results as [T#], with every figure checked against the data.
  - Uses adaptive thinking and prompt caching.
- **Much stronger free assistant:** answers market, comparison, screening, news and concept questions without an API key, and understands company names in the question ("Compare TCS and Infosys").
- **Premium UI:**
  - Live index ticker under the header; prices flash green or red when they change.
  - Market clock pill; phone tab bar (Home, Markets, Explore, Invest, Ask AI).
  - An "Ask AI" box on Home.
  - Assistant: research steps shown live, source chips, stop and copy buttons.
- `/api/health` reports the market-data provider, whether it is real-time, any errors and the number of watchers.
- Hashed static assets are cached for a year; `index.html` is never cached.

### Changed
- Home puts your watchlist and virtual portfolio right after the indices on phones.
- Index tiles refresh every 15 s in session (2 minutes otherwise) and read the shared quote cache.

### Tests
- 18 new tests:
  - market clock and holidays
  - Kite parsing, mapping, expired token and provider selection
  - hot set
  - WebSocket snapshot-then-diff
  - offline router
  - company-name matching
  - screen validation
  - Claude tool loop: tool results, tool errors, truncated tool input never run

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
