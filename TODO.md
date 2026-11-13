# TODO

## Needs the owner (account access / personal details)
- [x] GitHub repository: https://github.com/Lalupratap-Yadav/EquityPilot-AI (public).
- [ ] Deploy v2 (Docker / container host, docs/DEPLOYMENT.md §2) with a persistent volume, or the classic workbench on Streamlit Community Cloud (§3), and add the live URL to README.md.
- [ ] Optional, paid: real-time prices. The Zerodha Kite Connect connector is built (docs/MARKET_DATA.md) and needs your own Kite Connect app (about ₹500/month; check kite.trade) plus a daily access token. It is tested only against mocked responses.
- [ ] Add your name and LinkedIn/GitHub links to the README (an "Author" section) if you want them public.
- [ ] Choose a licence (e.g. MIT) if you want others to reuse the code.
- [ ] Optional: enable the Claude API engine with your own key (paid; costs are shown in the app).

## Verification still open
- [ ] Observe the in-session behaviour on a live trading day: 20 s refresh, price flashes, Breaking news.
- [ ] Run the Claude research agent against the paid API with your key.
- [ ] Reduce the ~1 minute slow period after a server restart (the warm-up competes for CPU); for example, move the warm-up into a separate worker process.
- [ ] Better company tagging of media headlines (Yahoo's per-company headlines are loosely matched; publisher RSS items are not tagged to companies yet).
- [ ] Build and run the Dockerfile on a machine with Docker installed.
- [ ] Test `EQUITYPILOT_DATABASE_URL` against a real PostgreSQL server.
- [ ] Add frontend unit/interaction tests (e.g. Vitest + Testing Library or Playwright). Currently the frontend has only a type-check, a build and screenshot checks.

## Completed in v2.1 (see CHANGELOG.md)
- [x] Valuation summary, FCFE, margin of safety and historical multiple bands
- [x] Working-capital ratios, plain-English metric guide and benchmark ratings
- [x] Industry policy and regulation section, news source tiers, an official-sources directory and Compare strengths and risks

## Ideas not yet built
- [ ] Company investor-relations websites as a news source (needs a per-company list of IR pages / RSS feeds).
- [ ] Ministry of Finance / PIB English feed (the PIB RSS tested returned Hindi items for the region tried).
- [ ] Revenue segments and product mix: no free licensed source. This could be added as a user-entered table from the annual report, like shareholding.
- [ ] Historical shareholding trend chart in Compare (needs several quarters entered).

## Completed in v2 (see CHANGELOG.md)
- [x] FastAPI + React platform with 20 routes, accounts, watchlists and alerts, Virtual Invest, official feeds, 15 industries, document Q&A and shareholding entry

## Completed after v1
- [x] Quarterly results view (QoQ / YoY, margins, missing-quarter flags)
- [x] Screener and comparison export to formatted Excel
- [x] Bank-specific metrics (NIM, GNPA/NNPA, PCR, CRAR, CASA, cost-to-income, credit cost) with risk bands, AI context and report
- [x] Scheduled refresh via `python -m equitypilot refresh` (Task Scheduler / cron)

## Not done – needs infrastructure outside this project
- [ ] OCR for scanned PDFs (requires installing Tesseract on the machine/server).
- [ ] Persistent hosted database for cloud deployment (requires a database account, e.g. a managed Postgres).
