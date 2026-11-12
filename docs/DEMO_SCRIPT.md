# EquityPilot AI: 7-minute interview demo

**Goal:** show research judgement, not just coding, in 7 minutes. Each step says what to click and what to say.

**Company:** TCS, or any company the interviewer names. Press `Ctrl+K` and type its name.

**Before the interview**
- Start the server (`python -m uvicorn api.main:app --port 8000`) 10 minutes early so quotes, feeds and metrics are warm.
- Open http://localhost:8000.
- Save a DCF for TCS in the Valuation Lab.
- Buy a few shares in Virtual Invest.
- Upload one annual-report PDF in Documents.
- Keep a generated PDF report as a backup.

---

### 1. The problem (30 s): Home
> "Retail and student analysts juggle exchange filings, screeners, spreadsheets and chatbots that invent numbers. I built one platform where every number has a source, a timestamp and a label, and where the AI may only cite those sources."

Point at the index tiles and the **DELAYED** badge: "Real-time NSE data needs a licensed vendor or a broker API, so I label every price honestly instead of pretending."

### 2. Discovery (45 s): Explore → Industries → Banking
> "Over 5,500 listed securities are searchable, and the cap categories come from AMFI's official list. Each of the 15 industries explains its drivers and risks and the metrics that matter. For banks that's NIM, GNPA and CASA rather than EBITDA."

### 3. Company and fundamentals (1 min): Company → Financials, then Quarterly
> "TCS: ROE near 49% with almost no debt. DuPont shows it comes from margins and asset turnover, not leverage."

Hover over a source note: "Every block says where the data came from and when it was retrieved."

### 4. Valuation (1.5 min): Valuation Lab
> "WACC from CAPM, FCFF DCF with every step shown, then bear, base and bull scenarios."

Point at the **terminal value share**: "Most of the value is terminal, so I never rely on one number."

Show the **sensitivity grid** and the **reverse DCF**: "The price implies about X% growth versus a 3-year CAGR of about 6%. That's the question to debate."

### 5. Market intelligence (45 s): News & Intelligence
> "Exchange announcements and results come from NSE's official RSS feeds, with links to the filing PDFs and mapped to companies. RBI and SEBI updates sit alongside. I don't scrape anything: nseindia.com blocks bots, so I use what the exchange publishes for subscription."

### 6. AI assistant with documents (1 min): AI Assistant → tick the uploaded annual report
Ask **"What does the report say about risks?"**
> "Answers cite numbered sources and page numbers. It's free and offline by default. Claude is optional, the cost per question is shown first, and figures are checked against the sources."

Then type **"Should I buy TCS?"**
> "It declines. In India, recommendations need SEBI registration, so it shows the evidence instead."

### 7. Virtual Invest (45 s)
> "Everyone gets ₹10 lakh of virtual money. Orders fill at the latest delayed price with that price's timestamp, and the app blocks overspending and overselling. Splits and dividends are applied automatically, and performance is compared with the NIFTY 50. The tips are educational: diversification and concentration, not trade ideas. Leaderboard participation is opt-in."

### 8. Deliverable (30 s): Reports → Generate PDF
> "A research note with tables, charts, my DCF assumptions, a source list and SEBI-aware disclosures."

**Close:**
> "A FastAPI backend reuses a tested Python analytics core, with a React/TypeScript frontend on top. Automated tests cover hand-calculated DCF and ratio checks and per-user data isolation, and everything works offline with labelled sample data."

---

## Likely interview questions

| Question | Answer pointers |
|---|---|
| Why not scrape NSE? | There's no public API, access is blocked and the terms matter. I use NSE's published RSS feeds and equity list, AMFI's list, and user uploads. |
| How do you stop the AI hallucinating? | It sees only numbered source blocks and must cite them. Document passages carry page numbers. The offline engine is deterministic, LLM answers get a grounding check, and recommendation requests are refused. |
| Why FCFF and not FCFE? | FCFF is independent of capital structure and pairs with WACC. For banks I use justified P/B, because debt is operating capital. |
| How would you get real-time prices? | Through a broker API on the user's own account (for example Kite Connect at about ₹500/month) or a licensed vendor. The market-data provider interface is pluggable, so it's an adapter, not a rewrite. |
| Why FastAPI + React instead of Streamlit? | Per-user sessions, a search palette, routing, theming and WebSocket push. The analytics core was kept unchanged, so the tests still apply. |
| How would you scale it? | Postgres (already supported through SQLAlchemy), a job queue for refreshes, and Redis only once there are several server processes. |
| What did you learn? | Data quality dominates: currencies, fiscal-year changes, statement basis, missing items. Handling them honestly mattered more than adding features. |
