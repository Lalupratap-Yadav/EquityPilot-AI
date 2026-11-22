# EquityPilot AI – Test Report (v2.6.0, 15 Nov 2026)

Run on 15 Nov 2026 (a Sunday, market closed) on Windows 11. "Live" means the running server on `localhost:8000` with the
real NSE, RBI, SEBI, BSE, publisher RSS and Yahoo Finance data collected since 11-12 Nov 2026. Automated tests run offline.

## 1. Automated checks

| Check | Result |
|---|---|
| `python -m pytest -q` (offline, temporary database) | **277 passed, 0 failed** |
| of which new in `tests/test_trust_v26.py` | 39: 24 misleading-headline cases, company news API, provider headline split, results calendar, corporate actions, health, EPS checks, coverage, data quality, split accounting, leaderboard, search ranking, new search tools, cross-user privacy |
| `npm test` (Vitest + Testing Library, jsdom, fake API) | **19 passed** in 5 files |
| `npx tsc -b` | Passed |
| `npm run build` | Passed |
| `npx oxlint src tests` | 0 errors, 21 warnings (20 in files this release did not change, 1 in the test helper) |
| `ruff check api equitypilot tests --select F,E9` | Clean (3 unused imports removed) |

Changed existing tests, with the reason:
- `test_api.py::test_paper_split_and_dividend_adjustments` now expects 100 instead of 50: a dividend paid before a 2:1 split is
  restated by the provider at half the amount paid (checked on TCS history: 0.375 x 8 = the Rs 3 paid in 2004).
- `test_research_quality.py::test_unrated_headlines_hidden_by_default`: the sample "tip site" headline now names the company,
  because a headline that does not name the company is no longer company news at all.
- `test_live_ai.py`: version 2.6.0.

Negative check: with the split handling switched off, `test_performance_has_no_jump_on_a_split` fails (an 80% false jump on
the split day), so the test does detect the old behaviour.

## 2. Company identification in news (live data)

| Check | Result |
|---|---|
| TCS company news | Only stories naming TCS (2 in the last 14 days). The Microsoft/H-1B, Infosys and Rezolve AI stories from Yahoo's TCS stream are now general market news |
| Media RSS tagging | 218 of 1,125 publisher stories linked to tracked companies. A sample of 18 was reviewed by hand: 1 false link found ("ITC (HS) code" in a DGFT notice) and fixed; a later page review found "SBI Capital" (adviser) linked to SBI, also fixed |
| Speed | About 13 microseconds per headline; 5,000 headlines in 0.06 s |

## 3. Search across the full securities master (live database)

Every security with an NSE symbol (2,418) searched twice, by symbol and by full name; the right company must be first.

| | Before | After |
|---|---|---|
| By NSE symbol | 99.50% (12 misses) | **99.96%** (1 miss: KALYANI is two different companies on NSE and BSE) |
| By company name | 99.71% (7 misses) | **99.92%** (2 misses: DVR share classes with the same company name) |
| Time per search | 80-170 ms | 12-65 ms |

## 4. New pages (live server)

| Page | Live result |
|---|---|
| Earnings & Results | 13 confirmed upcoming result dates, 1,150 results filings since 12 Nov 2026; board-meeting feed and announcement merged per meeting; delay notices shown separately |
| Corporate Actions | 16 upcoming actions (14 dividends, 1 split, 1 buyback); split terms parsed ("Face value Rs 10 to Re 1, each share becomes 10"); interest payments on debt excluded |
| Data Quality | 20 of 20 feeds fresh; 120 of 120 tracked companies with 3+ years of statements; 1 EPS warning (HDFC Bank, Mar 2023: diluted 88.68 above basic 44.51), the issue already noted by hand in v2.5.1 |
| Financial Health | TCS: 6 of 6 areas rated; HDFC Bank: bank framework, asset quality / capital / funding "Insufficient data" until bank metrics are entered, debt and cash flow "Not applicable" |
| Endpoint timings (warm) | results 0.04-0.14 s, actions 0.3 s, health 0.4 s, data quality 0.3 s (first call after a restart about 3 s) |

Screenshots in headless Edge: Earnings (list, calendar, recently filed, company history), Corporate Actions (upcoming, company
history), Data Quality, Health (TCS, HDFC Bank) and News at 1440 px light; Earnings, Corporate Actions, Health and Data Quality at
390 px; Health and the Earnings calendar in dark mode. No horizontal page overflow and no "NaN" or "undefined" text on any of them.

## 5. Not tested

- Zerodha Kite Connect against the real API (needs your Kite Connect app and daily token).
- The Claude research agent against the paid API (needs your key).
- The Dockerfile (Docker is not installed here) and PostgreSQL (no test server).
- Behaviour during a live trading session (tested on a Sunday).
- Browser end-to-end tests: the frontend tests run in jsdom against a fake API; the live pages were checked with screenshots.

---

# Test Report (v2.5.2, 15 Nov 2026)

## 0. Premium visual refresh (v2.5.2, 15 Nov 2026)

Visual-only release. No new sections and no changes to data, APIs or calculations.

| Check | Result |
|---|---|
| `python -m pytest` (all backend tests, offline) | **238 passed, 0 failed** (version test updated to 2.5.2) |
| `npm run build` (includes the `tsc -b` type-check) | Passed, no errors |
| `npx oxlint src` | 0 errors; 5 warnings, all in code this release did not change |
| Screenshots in headless Edge against the live server | Light (1440 px): Home, Market Tracker, Company, Valuation Lab, Virtual Invest, News, advanced chart. Dark (1440 px): Home, Company. Phone (390 px): Home, Virtual Invest. No console errors, no horizontal overflow and no "NaN" or "undefined" text on any page |
| Simple chart with the gradient fill | Value, colour (green or red against the reference line) and the "as of" time are unchanged |
| Market clock pill on the dark Home banner | Readable in both themes |

Everything below this section is the v2.5.1 report.

---

# Test Report (v2.5.1, 13 Nov 2026)

Everything below was run on 13 Nov 2026 on Windows 11 against the code in this commit. "Live data" means the running server on
`localhost:8000` with the real Yahoo Finance, NSE, RBI, SEBI, BSE and publisher RSS feeds. Automated tests run offline on a
temporary database.

## 1. Automated tests

| Suite | Result |
|---|---|
| `python -m pytest` (all backend tests, offline) | **238 passed, 0 failed** (v2.5.1) |
| New in v2.5: `tests/test_search_news.py` | 17 passed: grouped search, topics, news sections, de-duplication, breaking window, filters, saved articles, explanations, daily summary, glossary coverage, request ids |
| `npx tsc -b` (frontend type-check) | Passed, no errors |
| `npm run build` | Passed |
| `npx oxlint src` | 0 errors; style warnings only (set-state-in-effect, the same pattern as existing pages) |

One failure appeared during the run (a test still expected version 2.4.0 after the bump to 2.5.0). The test was updated and re-run.

## 1b. Hardening pass (v2.5.1)

| Check | Result |
|---|---|
| Full suite after hardening | **238 passed, 0 failed** (ruff and tsc clean) |
| `ruff` (undefined names, syntax and runtime errors) | Clean. One false alarm reviewed: the loop-variable warning in `context.py` is safe because the lambda is called immediately |
| API sweep, fresh offline database: 71 paths × normal / missing / hostile inputs (1,505 calls) | No 5xx. Found and fixed: the chart endpoint called Yahoo in offline mode |
| API sweep, online on a copy of the real database (1,505 calls) | No 5xx. Found and fixed: an unknown symbol returned 502 instead of 404 |
| Browser sweep, 12 malformed URLs | No JavaScript errors; every page shows a clear message or recovery button |
| `start.bat` | Tested: starts the server and opens the browser; detects an already-running server. The first-run install and build path has not been run on a clean machine |
| Burst right after a restart: 15 simultaneous tile requests + 3 chart requests | Before: tiles took 105–139 s (every poll downloaded the same data). After: tiles 0.2–0.9 s; the 3 identical chart requests share one download |
| Steady state (live, curl) | Tiles 0.24 s, sectors 0.37 s, search 0.29–0.57 s, news 1.2–1.8 s, daily summary 0.42 s, company 1.2 s, charts 0.8–1.0 s, valuation 4.2 s |
| First chart in the first seconds after start | 15–21 s: yfinance's first connection to Yahoo (session cookie) happens then. Later charts take under 1 s |

Two chart tests failed after the offline fix because they fed fake Yahoo data while the suite runs offline. They now switch
offline mode off explicitly. One Streamlit page test timed out once while a stray background process used the CPU; it passes
on its own (17 s) and its limit was raised to 180 s.

## 2. Checklist from the brief

| # | Test | How | Result |
|---|---|---|---|
| 1 | Global search: names and symbols | Live API: Reliance, Reliance Industries, RELIANCE, TCS, Tata Consultancy Services, HDFC Bank | ✅ The correct company is first every time |
| 2 | Partial names and spelling mistakes | "Adani Enterprwses" → Adani Enterprises ("Showing results for adani enterprises"); "Tata Powr" → Tata Power; "Relaince" → Reliance; "hdfc" → HDFC Bank first | ✅ |
| 2b | Topics | "Indian banking sector" → Banking industry; "IT industry" → IT; "Nifty 50" / "bank nifty" / "sensex" → index; "Debt-to-equity ratio" → concept; "DCF valuation" → concept + Valuation Lab; "Companies with high ROE" → research tool | ✅ (unit tests + live) |
| 3 | Company profile navigation | TCS and HDFC Bank: Overview, Price & performance, Financials, Valuation, Shareholding, Competitors, News, Risks, Documents; Advanced adds Quarterly, Bank metrics, Technicals and Notes; switching modes keeps the company | ✅ screenshots |
| 4 | News filters and original links | Section, company, sector, source, date range, sort, tracked-only and search all tested; every item links to the publisher or filing | ✅ unit tests + live |
| 5 | News dates and sources | Publication time shown in IST; fetch time kept separately (tooltip); "Breaking" only includes items under 3 hours old (unit test); official vs media labelled | ✅ |
| 6 | Ticker and chart consistency | NIFTY 50: ticker, tile and chart header all 25,144.30 −155.05 (−0.61%), "as of 13 Nov, 15:29 IST"; while hovering, the header stays on the latest value and the hovered point is in the tag | ✅ live screenshots |
| 7 | Financial calculations | Existing ratio, valuation, DCF and portfolio tests pass. Reliance 0.00% was cross-checked against Yahoo directly: it closed at ₹1,339.70 on both 12 and 13 Nov (genuine) | ✅ |
| 8 | Responsive layouts | 1440 px light, 820 px tablet and 390 px phone (dark): Home, search, News, Company, Markets – no horizontal overflow on any page | ✅ |
| 9 | Navigation and buttons | Regression tour of 23 routes (all pages + company tabs + deep links); console errors, NaN/undefined text and overflow checked | ✅ 0 issues |
| 10 | Existing features and Virtual Invest | Invest, Portfolio, Watchlists, Reports, Documents, Learn and Settings pages load; existing tests for paper trading pass | ✅ |
| 11 | API failures and missing data | Feed failures keep cached items (tested in the existing suite); an expired Kite token falls back to delayed data (test); missing values show "—" or "n/a", never 0; unknown news section → 404 | ✅ |
| 12 | Performance | See §3 | ✅ steady state; ⚠ see cold start |

## 3. Performance (live server, HTTP, measured with curl)

| Endpoint | Steady state | Right after a restart |
|---|---|---|
| `/api/market/overview` (tiles, ticker) | 0.23–0.27 s | 0.25 s (served from the saved snapshot; it was 32 s before this fix) |
| `/api/search` | 0.24–0.35 s over HTTP; 65–100 ms inside the server (shown in the palette) | up to ~10 s during the first minute |
| `/api/news/feed` (top) | 0.38–0.51 s | 2–9 s during the first minute |
| `/api/news/summary` | 0.34–0.39 s | slow in the first minute (was 41 s before it switched to database counts) |
| `/api/companies/TCS.NS` | 1.1–1.4 s | – |

**After a restart (v2.5.1):** tiles, news, search and the summary answer within about 1–6 s while the warm-up runs (quotes for
about 140 symbols, universe metrics, 18 feeds), and under 2 s afterwards. The first chart in the opening seconds can take up to
about 20 s because of Yahoo's first-connection handshake.

## 4. Data-quality observations (not changed – shown as the source reports them)

- **HDFC Bank EPS:** basic and diluted EPS appear swapped between FY2023 and FY2024 in Yahoo Finance's data (likely
  bonus-issue adjustment). Shown as reported; verify with the annual report.
- **Peer P/E for INFY and HCLTECH is blank:** the provider did not return the inputs. Shown as "—", not estimated.
- **Yahoo company headlines are loosely matched:** for example, a Microsoft story appeared under TCS. They are labelled SECONDARY,
  and exchange filings remain the authoritative company news.
- **Consolidated/standalone basis:** Yahoo does not state the basis. The company page says so on every tab.

## 5. Not tested (needs credentials, paid services or infrastructure)

- Zerodha Kite Connect real-time quotes: tested only against mocked API responses, not a live account.
- Claude research agent: tested with a fake client; not run against the paid Anthropic API.
- Docker image build, PostgreSQL backend, and frontend unit/interaction tests (only type-check, build and screenshot checks exist).
- Market-hours behaviour on a live trading day: the in-session refresh (every 20 s) and price flashes were exercised by tests and
  by code review. This session ran after the close (17:00–17:30 IST), so the live tick-by-tick behaviour was not observed.
