# TODO

## Needs the owner (account access / personal details)
- [ ] Create the GitHub repository and push (commands in docs/DEPLOYMENT.md §1).
- [ ] Deploy on Streamlit Community Cloud (docs/DEPLOYMENT.md §2) and add the live URL to README.md.
- [ ] Add your name and LinkedIn/GitHub links to the README (an "Author" section) if you want them public.
- [ ] Choose a licence (e.g. MIT) if you want others to reuse the code.
- [ ] Optional: enable the Claude API engine with your own key (paid; costs are shown in the app).

## Completed after v1
- [x] Quarterly results view (QoQ / YoY, margins, missing-quarter flags)
- [x] Screener and comparison export to formatted Excel
- [x] Bank-specific metrics (NIM, GNPA/NNPA, PCR, CRAR, CASA, cost-to-income, credit cost) with risk bands, AI context and report
- [x] Scheduled refresh via `python -m equitypilot refresh` (Task Scheduler / cron)

## Not done – needs infrastructure outside this project
- [ ] OCR for scanned PDFs (requires installing Tesseract on the machine/server).
- [ ] Persistent hosted database for cloud deployment (requires a database account, e.g. a managed Postgres).
