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
- [x] Reduce the ~1 minute slow period after a server restart (v2.7: requests no longer wait for providers; bulk quotes, metrics and news rebuilds run in a worker process - first-burst Home 10.8 s → 0.6 s, see docs/PERFORMANCE.md).
- [ ] Run the v2.7 Claude path against the paid API once (prefetch, refusal fallback handling, cost per attempt): it is tested only with a fake client.
- [ ] Observe a live trading session with v2.7: the bulk quote refresh now runs in the worker process every 90 s; check request latency during it.
- [ ] Measure the restart behaviour on a slower machine or a 1-vCPU container (the worker process helps less there and uses ~150 MB of memory; `EQUITYPILOT_WORKER_PROCESS=0` turns it off).
- [x] Better company tagging of media headlines (v2.6: strict company matching for Yahoo and publisher RSS items).
- [ ] Extend the curated company aliases when new companies are tracked (new companies match on their full name and NSE symbol only).
- [ ] Observe the Earnings & Results and Corporate Actions pages over a full results season: the NSE feeds are rolling, so history builds up only while EquityPilot runs.
- [ ] Build and run the Dockerfile on a machine with Docker installed.
- [ ] Test `EQUITYPILOT_DATABASE_URL` against a real PostgreSQL server.
- [x] Frontend interaction tests (v2.6: Vitest + Testing Library, `npm test`). Browser end-to-end tests (Playwright) are not added.
- [ ] Decide whether to keep or remove the company "My notes" tab, watchlist item notes and the Reports "thesis" field (privacy review, v2.6).
- [ ] Optional: store the PDF tables found at upload in their own structure (v2.7 appends their rows to the page text for question answering; there is no table view).
- [ ] Learning Centre (v2.8): re-check the regulatory lessons against SEBI, exchange and RBI pages every few months and update `REVIEWED` in `equitypilot/content/curriculum/core.py`. Next items to watch: the RBI inflation-target framework, SEBI's research-analyst rules and equity-derivatives measures, and exchange price-band rules.
- [ ] Learning Centre: open the NSE, BSE, NSDL, MCA, IEPF and Union Budget source links in a browser once; they refuse automated checks, so only their addresses (not their pages) were verified.
- [ ] Learning Centre: optional "Go deeper" detail text for more lessons (the field is supported; ratio cards and key terms already fill it).
- [ ] Learning Centre: run the assistant's learning mode with the paid Claude engine once (tested offline and with a fake client only).

## Completed in v2.1 (see CHANGELOG.md)
- [x] Valuation summary, FCFE, margin of safety and historical multiple bands
- [x] Working-capital ratios, plain-English metric guide and benchmark ratings
- [x] Industry policy and regulation section, news source tiers, an official-sources directory and Compare strengths and risks

## Ideas not yet built
- [ ] Company investor-relations websites as a news source (needs a per-company list of IR pages / RSS feeds).
- [ ] Ministry of Finance / PIB English feed (the PIB RSS tested returned Hindi items for the region tried).
- [ ] Revenue segments and product mix: no free licensed source. This could be added as a user-entered table from the annual report, like shareholding.
- [ ] Earnings surprises: need a licensed analyst-estimate source (none connected, so none are shown).
- [ ] Payment dates for dividends: not in the NSE corporate-actions feed; would need parsing of each company's filing PDF.
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
