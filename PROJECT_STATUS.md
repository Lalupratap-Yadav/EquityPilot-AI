# EquityPilot AI – Project Status

## v2.2 PRICE CHARTS – complete (12 Nov 2026)
| Item | State |
|---|---|
| Daily charts shifted one day early (UTC conversion) – fixed for all companies and indices | ✅ regression test |
| Sample ranges, index 1D previous close, weekly volatility, indicator warm-up – fixed | ✅ tests |
| New Simple / Advanced chart with hover readout, labelled reference line, legend and "How to read this chart" | ✅ screenshots: 1440 px light (incl. hover) and 390 px dark |
| Probe of the chart API: TCS, IRCTC, NIFTY 50, SENSEX, NIFTY BANK, NIFTY IT, INDIA VIX and a sample company × every range | ✅ no empty, duplicate, unsorted or null bars |

Tests: **182 passing**.

## v2.1 RESEARCH DEPTH & TRUST – complete (12 Nov 2026)
Built in response to the "professional financial intelligence platform" brief. An audit against its 17 sections showed most items already existed in v2; this release fills the gaps listed below. Details: CHANGELOG.md [2.1.0].

| Item | State |
|---|---|
| Valuation Lab: Summary tab (estimated-value range across 7 methods vs price), FCFE model, margin of safety, historical P/E and P/B bands | ✅ unit tests (hand-calculated FCFE) + API tests + screenshots |
| Working-capital ratios (payable days, cash conversion cycle, NWC/revenue) | ✅ tested; payables fill in when a company's statements are next refreshed (verified on TCS) |
| Plain-English metric guide (33 metrics) + benchmark ratings + clickable explanations with history charts | ✅ tested (every ratio has a guide entry) + screenshots |
| Industry policy & regulation (15 industries, 53 items, official links checked to respond) | ✅ tested |
| Source tiers (official / secondary / unrated); unrated hidden by default and excluded from AI evidence | ✅ tested incl. AI context |
| Compare: 1-year return, shareholding, strengths and points to check, industry risks | ✅ API test + screenshots |
| Visual check (headless Edge): changed pages at 1440 px light and 390 px dark | ✅ no console errors, no horizontal overflow, no NaN/undefined text |

Tests: **171 passing** (`python -m pytest -q`).

Not changed, by design: no real-time prices (needs a paid broker API or licensed vendor, ≈ ₹500/month via Kite Connect, owner's choice); no BSE/MOSPI automatic feeds (linked, not scraped); shareholding and bank metrics are still entered from filings, because no free licensed source provides them.

## v2 PLATFORM UPGRADE – complete (12 Nov 2026)
Architecture: FastAPI backend `api/` (reuses the `equitypilot/` core) + React/TS/Tailwind frontend `web/` (Vite), served together on port 8000. The Streamlit app (`app.py`) still works as the classic workbench.
Audit: docs/AUDIT.md. Changelog: CHANGELOG.md.

| Step | State |
|---|---|
| Schema v2 (users, watchlists, alerts, notifications, paper trading, securities, news_items, doc_chunks, corporate actions) | ✅ migrates the existing DB |
| Securities master (AMFI Dec-2025 + NSE EQUITY_L, 5,552) + search | ✅ tested live |
| Feeds (NSE announcements/results, RBI, SEBI, Yahoo market) with failure back-off | ✅ tested |
| Market data provider (Yahoo delayed), intraday, 17 indices, corporate actions, WebSocket | ✅ |
| Virtual Invest engine + page | ✅ tested |
| Industries (15) + universe of 121 real companies | ✅ |
| RAG (BM25 passages with page refs) + Documents page | ✅ tested (incl. owner-only access) |
| API routers: market, company, explore, user, invest, research | ✅ API tests |
| Frontend: all 20 routes (no placeholders) | ✅ `tsc -b` clean, production build OK |
| Visual check (headless Edge): every route in light, key routes in dark, every route at 390 px | ✅ no console errors, no horizontal overflow, no NaN/undefined text |
| Performance: universe metrics stale-while-revalidate + disk snapshot | ✅ cold-start Explore 0.36 s (was up to 162 s) |
| Docs: README v2, DEPLOYMENT (Docker), DEMO_SCRIPT v2, CHANGELOG, screenshots | ✅ |
| Dockerfile | ⚠️ written, **not build-tested** (Docker not installed on this machine) |
| PostgreSQL path (`EQUITYPILOT_DATABASE_URL`) | ⚠️ implemented, **not tested** against a live server |
| Frontend unit tests | ❌ none: the frontend is covered by the type-check, the build and the visual checks only |

Tests: **148 passing** (`python -m pytest -q`), all offline against a temporary DB.

Run: `python -m uvicorn api.main:app --port 8000` (after `cd web && npm run build`). Frontend dev: `cd web && npm run dev`.

---|---|
| Backend: schema v2 (users, watchlists, alerts, notifications, paper trading, securities, news_items, doc_chunks, corporate actions) | ✅ done, migrates existing DB |
| Securities master (AMFI Dec-2025 + NSE EQUITY_L, 5,552) + search | ✅ |
| Feeds (NSE announcements/results, RBI, SEBI, Yahoo market) | ✅ |
| Market data provider (Yahoo delayed), intraday, indices (17), corporate actions, WebSocket | ✅ |
| Virtual Invest engine | ✅ tested |
| Industries content (15) + universe 121 real companies | ✅ |
| RAG (BM25 passages with page refs) | ✅ tested |
| API routers: market, company, explore, user, invest, research | ✅ 14 API tests; 144 total passing |
| Frontend (web/) | ⏳ next: design system, shell, pages |
| Docs, Dockerfile, demo script v2 | ⏳ |

Run backend: `.venv/Scripts/python -m uvicorn api.main:app --port 8000` · frontend dev: `cd web && npm run dev` (proxy /api → 8000).

---


_Source of truth for what is built and tested. Updated at the end of every phase._

**Last updated:** 12 Nov 2026 · **Status:** Phases 1–10 complete, plus post-v1 enhancements (quarterly results, bank metrics, Excel exports, CLI refresh). Remaining items need the owner's action – see TODO.md.

## Architecture (fixed – do not restructure)

```
app.py                     entry point: page config, theme, st.navigation (17 pages), global company picker
equitypilot/
  config.py · db.py · formatting.py
  data/      schema · universe · yahoo · official · sample · uploads · repository
  analytics/ ratios · valuation · screener · technicals · risk · bank · portfolio
  ai/        context · offline · providers
  reports/   pdf_report · excel_export
  cli.py · __main__.py   python -m equitypilot status | refresh
  content/   glossary · learning
  ui/        theme · components · charts
views/       dashboard company financials valuation technicals risk news screener compare
             assistant report portfolio data_manager learning guide
tests/       conftest · test_analytics · test_uploads · test_ai_report · test_pages
docs/        DEPLOYMENT.md · DEMO_SCRIPT.md · screenshots/ · sample_report_SAMPLE-ALPHA.pdf
```

## Phase progress

| Phase | Scope | Status |
|---|---|---|
| 1 | Environment, architecture, DB, design system, navigation | ✅ Done · tested |
| 2 | Dashboard, company search, company research | ✅ Done · tested |
| 3 | Financial statements, ratios, historical analysis | ✅ Done · tested |
| 4 | Valuation, DCF, company comparison | ✅ Done · tested |
| 5 | Screener, technical analysis, risk analysis | ✅ Done · tested |
| 6 | Data manager, uploads (CSV/Excel/PDF), news & disclosures | ✅ Done · tested |
| 7 | AI research assistant, PDF report generator | ✅ Done · tested |
| 8 | Portfolio, learning centre, how-to-use guide | ✅ Done · tested |
| 9 | Full testing, security checks, UI polish, mobile check | ✅ Done · tested |
| 10 | README, screenshots, deployment guide, demo script | ✅ Done (GitHub push and cloud deploy need the owner's account – see TODO) |

## Post-v1 enhancements (all tested)

| Feature | Where | Tests |
|---|---|---|
| Quarterly results (QoQ/YoY, margins, missing-quarter flags) | Financial Analysis → Quarterly results | quarterly_summary maths, quarter labels, page render |
| Bank metrics (NIM, GNPA, NNPA, PCR, CRAR, CASA, cost-to-income, credit cost) | Company Research → Bank metrics; risk checks; AI context; PDF risk table | bands incl. RBI 11.5% CRAR floor, sample bank flags, grounded assistant answer, bank report |
| Fictional sample bank (Epsilon Bank Ltd) | Sample dataset | all pages render; DCF disabled, justified P/B shown |
| Formatted Excel export | Stock Screener, Company Comparison | number formats, frozen panes, notes sheet |
| CLI refresh / status for scheduling | `python -m equitypilot` | status output; offline refresh refusal; live run verified for TCS/INFY |

## Testing evidence (what was actually run)

- **pytest: 130 tests passing** (offline, temporary DB). These cover:
  - Hand-calculated ratio, DCF, WACC, reverse-DCF, sensitivity, justified P/B, technical indicator, Altman Z″, XIRR and concentration checks.
  - Upload parsers (periods, aliases, units, outflow signs, NSE price CSV), PDF extraction and search, and security helpers.
  - AI grounding (all offline facts traceable to sources; recommendations declined; missing info admitted).
  - PDF reports for sample companies.
  - AppTest render of all 17 pages for all 5 sample companies (incl. the sample bank), plus interactions (assistant chat input, portfolio, quiz).
- **Real-data render check**: every company page rendered for all 44 real companies against the real local DB, with no exceptions. This found and fixed one bug (Nestlé ROE above an input maximum).
- **Visual checks**: headless-Edge screenshots of every page at 1440px, and a phone check at 390px. PDF reports were rendered to images and inspected.
- **Live data verified**: Yahoo fetch for 44 NSE companies (profile, quote, 4–5 FY plus quarterly statements, about 5 years of daily prices, news), and live NIFTY/SENSEX/VIX tiles.

## Data-quality issues found in real data and handled

- INFY and HCLTECH statements reported in USD by the provider → currency recorded; multiples and DCF disabled; ratios kept.
- NESTLEIND fiscal-year change (Dec→Mar) → stub periods dropped; YoY growth blank across non-12-month gaps; averages use closing balances.
- Banks → EV/EBITDA, D/E, current ratio, Piotroski and FCFF DCF marked not meaningful; justified P/B offered instead.
- Provider equity figures can differ from filings (e.g. HDFC Bank post-merger) → labelled THIRD-PARTY with a "verify with filings" note; uploads take a separate basis.

## Known limitations (by design / external)

- NSE blocks automated access (HTTP 403 verified); there is no official public API → deep links plus uploads.
- Yahoo data is delayed, gives 4–5 fiscal years, and does not state its basis.
- No OCR for scanned PDFs (detected and reported) – needs a system install (Tesseract).
- Yahoo sometimes omits a quarter (e.g. TCS Sep-2025) – flagged in the Quarterly results view.
- The free cloud tier has an ephemeral SQLite database.
