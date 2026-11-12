# EquityPilot AI – Upgrade audit (12 Nov 2026)

## 1. What exists

| Layer | State | Verdict |
|---|---|---|
| `equitypilot/` core: data (Yahoo provider, repository, uploads, sample), analytics (ratios, valuation, technicals, risk, bank, portfolio, screener), AI (grounded context, offline analyst, providers), reports (PDF, Excel), content (learning, glossary), CLI | ~6,000 lines, 130 tests passing, framework-independent | **Retain** – reuse as the backend domain layer |
| Streamlit UI (`app.py`, `views/`, `equitypilot/ui/`) | 17 working pages, consistent styling | **Replace progressively** – keep running as the "Classic workbench" until the new UI reaches parity |
| SQLite DB | 49 companies (44 real + 5 fictional samples), 11k statement values, 59k prices, quotes, bank metrics | **Retain**, extend schema (users, multiple watchlists, alerts, paper trading, securities master, feeds, corporate actions, document chunks) |
| Single-user design (global watchlist/holdings/settings) | Works locally | **Redesign** – per-user data with guest sessions + optional accounts |

## 2. Gaps against the upgrade brief

- UI: Streamlit cannot deliver a fintech-grade experience: command-palette search, carousels/discovery rows, smooth navigation, dark/light theme toggle, keyboard shortcuts, per-user state.
- Discovery: only 44 tracked companies; no master list of listed securities; no market-cap categories; no industry intelligence.
- Market tracking: no intraday charts; no push updates; no data-freshness indicators per widget.
- News: Yahoo headlines only; no exchange announcements, results feed or RBI/SEBI updates.
- Users: no multiple watchlists, alerts, saved screens, recently viewed, preferences, virtual trading.
- AI documents: keyword page ranking, not passage-level retrieval.

## 3. Verified legitimate data sources (probed 12 Nov 2026)

| Source | Access | Use |
|---|---|---|
| NSE RSS – corporate announcements, financial results (`nsearchives.nseindia.com/content/RSS/…`) | HTTP 200, public RSS feeds published for subscription | Exchange disclosures & results with links to the original filing PDFs |
| NSE equity list `EQUITY_L.csv` | HTTP 200, published download | Master list: symbol, name, ISIN, listing date |
| AMFI average market-cap list (31 Dec 2025, xlsx) | HTTP 200 | Official large/mid/small-cap categorisation (SEBI circular Oct 2017); 5,372 companies with ISIN, NSE & BSE symbols |
| RBI press releases & notifications RSS | HTTP 200 | Economic / monetary-policy updates |
| SEBI RSS | HTTP 200 | Regulatory updates |
| Yahoo Finance via yfinance | Works | Delayed quotes, intraday (1m–1h, delayed), history, statements, splits/dividends, headlines (third-party) |
| nseindia.com web pages / APIs | HTTP 403 to automated clients | **Not used** (no scraping) |

## 4. Real-time data – findings

True real-time NSE/BSE data requires either a licensed vendor or a broker API tied to the user's own trading account (daily login token). Reported costs (third-party sources, Nov 2026 – confirm with the broker):
Zerodha Kite Connect ≈ ₹500/month; Angel One SmartAPI free for clients; Upstox/Fyers free for clients with conditions; Dhan data API ≈ ₹499/month.
Decision: implement a **pluggable market-data provider interface** with Yahoo (DELAYED) as default and WebSocket push from the backend; a broker adapter can be added once the owner chooses a broker and supplies credentials. No live prices are ever invented.

## 5. Architecture decision

**Migrate to FastAPI + React (TypeScript, Vite, Tailwind)**, reusing the Python core unchanged.
Justification: required UX (search palette, discovery rows, theming, routing, real-time push, per-user sessions) is natural in React; FastAPI exposes the existing, tested analytics as a REST/WebSocket API; one process serves both API and built frontend, so deployment stays simple.
Not adopted: Next.js SSR (no SEO need; SPA is simpler to serve from FastAPI), Redis (in-process TTL cache is sufficient at this scale), PostgreSQL by default (SQLite locally; SQLAlchemy keeps a Postgres path open).

## 6. Plan

1. Schema extensions + securities master + feeds + intraday + corporate actions + users.
2. FastAPI API (routers per domain), guest sessions, rate limiting, logging, tests.
3. React design system and app shell (sidebar, global search, theme, notifications).
4. Pages: Home, Explore & Industry Intelligence, Search, Company, Market Tracker, Watchlists & Alerts, Portfolio, Virtual Invest, Research workspace, Valuation Lab, Screener, Compare, News Intelligence, AI Assistant (RAG), Reports, Learning, Guide, Settings.
5. Test (pytest API + TypeScript build + visual checks), document, deploy (Dockerfile), recruiter demo.
