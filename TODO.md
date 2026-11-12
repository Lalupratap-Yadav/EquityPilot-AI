# TODO

## Needs the owner (account access / personal details)
- [ ] Create the GitHub repository and push (commands in docs/DEPLOYMENT.md §1).
- [ ] Deploy v2 (Docker / container host, docs/DEPLOYMENT.md §2) with a persistent volume, or the classic workbench on Streamlit Community Cloud (§3), and add the live URL to README.md.
- [ ] Optional, paid: real-time prices via a broker API on your own trading account (e.g. Kite Connect ≈ ₹500/month) or a licensed vendor. The `MarketDataProvider` interface is ready for an adapter, which needs your broker choice and credentials.
- [ ] Add your name and LinkedIn/GitHub links to the README (an "Author" section) if you want them public.
- [ ] Choose a licence (e.g. MIT) if you want others to reuse the code.
- [ ] Optional: enable the Claude API engine with your own key (paid; costs are shown in the app).

## Verification still open
- [ ] Build and run the Dockerfile on a machine with Docker installed.
- [ ] Test `EQUITYPILOT_DATABASE_URL` against a real PostgreSQL server.
- [ ] Add frontend unit/interaction tests (e.g. Vitest + Testing Library or Playwright). Currently the frontend has only a type-check, a build and screenshot checks.

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
