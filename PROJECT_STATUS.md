# EquityPilot AI – Project Status

_Source of truth for what is built and tested. Updated at the end of every phase._

**Last updated:** 12 Nov 2026 · **Status:** Phases 1–10 complete. Remaining items needing the owner's action are listed in TODO.md.

## Architecture (fixed – do not restructure)

```
app.py                     entry point: page config, theme, st.navigation (17 pages), global company picker
equitypilot/
  config.py · db.py · formatting.py
  data/      schema · universe · yahoo · official · sample · uploads · repository
  analytics/ ratios · valuation · screener · technicals · risk · portfolio
  ai/        context · offline · providers
  reports/   pdf_report
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

## Testing evidence (what was actually run)

- **pytest: 106 tests passing** (offline, temporary DB). These cover:
  - Hand-calculated ratio, DCF, WACC, reverse-DCF, sensitivity, justified P/B, technical indicator, Altman Z″, XIRR and concentration checks.
  - Upload parsers (periods, aliases, units, outflow signs, NSE price CSV), PDF extraction and search, and security helpers.
  - AI grounding (all offline facts traceable to sources; recommendations declined; missing info admitted).
  - PDF reports for sample companies.
  - AppTest render of all 17 pages for all 4 sample companies, plus interactions (assistant chat input, portfolio, quiz).
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
- No OCR for scanned PDFs (detected and reported).
- The free cloud tier has an ephemeral SQLite database.
