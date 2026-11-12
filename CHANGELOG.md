# Changelog

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
