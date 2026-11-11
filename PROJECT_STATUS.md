# EquityPilot AI – Project Status

_Source of truth for what is built and tested. Updated at the end of every phase._

**Last updated:** 11 Nov 2026 · **Current phase:** 4 (Valuation & comparison)

## Architecture (fixed – do not restructure)

```
app.py                     entry point: page config, theme, st.navigation, global company picker
equitypilot/
  config.py                paths, constants, data-type labels, freshness rules
  db.py                    SQLite schema (SQLAlchemy Core) + helpers; every table carries provenance
  formatting.py            ₹ / crore / % / x formatting, IST timestamps, FY labels
  data/
    schema.py              canonical line items (all providers map into these keys)
    universe.py            default research universe + symbol normalisation
    yahoo.py               Yahoo Finance provider (yfinance) – third-party, delayed
    official.py            NSE/BSE/SEBI/RBI/MOSPI deep links (no scraping)
    sample.py              FICTIONAL sample companies (offline mode + tests)
    repository.py          single data-access layer used by all pages (cache-first)
  analytics/
    ratios.py              ratios, CAGR, TTM, DuPont, Piotroski, data-quality checks
    valuation.py           multiples, WACC/CAPM, DCF, scenarios, sensitivity, reverse DCF, justified P/B
    screener.py            per-company metric snapshot, presets, filters
  ui/ theme.py · components.py · charts.py
views/                     one file per page
tests/                     pytest (unit + Streamlit AppTest page smoke tests, offline)
```

## Phase progress

| Phase | Scope | Status |
|---|---|---|
| 1 | Environment, architecture, DB, design system, navigation | ✅ Done · tested |
| 2 | Dashboard, company search, company research | ✅ Done · tested |
| 3 | Financial statements, ratios, historical analysis | ✅ Done · tested |
| 4 | Valuation, DCF, company comparison | 🔄 In progress |
| 5 | Screener, technical analysis, risk analysis | ⏳ Pending |
| 6 | Data manager, uploads (CSV/Excel/PDF), news & disclosures | ⏳ Pending |
| 7 | AI research assistant, PDF report generator | ⏳ Pending |
| 8 | Portfolio, learning centre, how-to-use guide | ⏳ Pending |
| 9 | Full testing, security, UI polish | ⏳ Pending |
| 10 | README, screenshots, deployment, recruiter demo | ⏳ Pending |

## Tested features (evidence: `pytest` – 26 passing)

- Sample data generation and storage; Yahoo fetch verified live for TCS.NS (profile, quote, 4 FY + 5 quarters, 1,236 daily prices, 10 headlines).
- Ratios (growth, margins, ROE/ROCE/ROA with average balances, leverage, liquidity, efficiency, cash-flow), CAGR, DuPont, balance-sheet consistency check – hand-calculated unit tests.
- Multiples, WACC, DCF (hand-calculated), WACC≤g guard, reverse DCF, sensitivity monotonicity, justified P/B.
- Pages render without exceptions for all 4 sample companies: Dashboard, Company Research, Financial Analysis.
- Visual check via headless Edge screenshots (dashboard shows live NIFTY/SENSEX/VIX).

## Known limitations (by design / external)

- NSE blocks automated access (HTTP 403 verified); no official public API → deep links + uploads.
- Yahoo Finance does not state consolidated vs standalone → labelled "basis not stated".
- Yahoo typically provides 4–5 fiscal years of statements.
