# EquityPilot AI: 7-minute interview demo

**Goal:** show research judgement (not just coding) in 7 minutes. Each step has what to click and what to say. **Company:** TCS (or any company the interviewer names).

**Before the interview**
- Run `streamlit run app.py` and open the Dashboard.
- Refresh the universe in the Data Manager.
- Save a TCS DCF on the Valuation page.
- Generate one PDF report as a backup.

---

### 1. The problem (30 s): Dashboard
> "Retail and student analysts juggle exchange filings, screeners, spreadsheets and chatbots that invent numbers. I built one platform where every number has a source, a timestamp and a label, and where the AI is only allowed to cite those sources."

Point at the live NIFTY/SENSEX tiles and the source line under them: "Delayed data, labelled as such."

### 2. Data honesty (45 s): Data Manager → Sources & status
> "NSE has no public API and blocks automated access, so I don't scrape it. Prices and summarised statements come from Yahoo Finance, labelled third-party. Official figures from annual reports can be uploaded, reviewed and stored with their citation and the consolidated or standalone basis."

Show the data-label legend. *Optional:* "Infosys reports in USD on Yahoo, so the app disables P/E for it rather than show a wrong number."

### 3. Fundamentals (1 min): Financial Analysis → Ratios & DuPont
> "TCS: ROE near 49% with almost no debt. DuPont shows it comes from margins and asset turnover, not leverage, which is high-quality ROE."

Hover over an ⓘ to show the formula. Open the **Data quality** tab: "The app checks that the balance sheet balances and flags irregular periods."

### 4. Valuation (1.5 min): Valuation → DCF → Scenarios & sensitivity
> "WACC from CAPM: risk-free from the 10-year G-sec, beta, equity risk premium. Every step is visible, from FCFF to the EV-to-equity bridge."

Point at **terminal value share of EV**: "About three-quarters of the value is terminal, so I never rely on one number."

Show the **sensitivity grid**, then the **reverse DCF**: "The market price implies roughly X% growth versus a 3-year CAGR of about 6%. That's the question to debate."

### 5. Screening and comparison (1 min): Stock Screener → "Quality compounders" → select 3 → Compare selected
> "Screening 44 large caps on ROE, ROCE, leverage and growth, then comparing side by side. Stars mark the best value, but the app warns when fiscal years, bases or currencies differ."

### 6. Risk (30 s): Risk Analysis (try Tata Steel)
> "Rule-based, with every threshold shown. Tata Steel's Altman Z″ is in the distress zone and leverage is moderate. It's a screening flag, not a verdict."

### 7. AI assistant (1 min): AI Research Assistant
Click **"Is the balance sheet strong?"**
> "Answers are split into facts with source IDs, calculations with formulas, and a clearly labelled interpretation. It's free and offline by default. The Claude API is optional and its cost is shown first."

Then type **"Should I buy TCS?"**
> "It declines. In India, recommendations require SEBI registration. I designed it to show the evidence instead."

### 8. Deliverable (30 s): Report Generator → Generate PDF
Open the PDF:
> "A research note with tables, charts, DCF assumptions, scenarios, a source list and SEBI-aware disclosures."

**Close:**
> "It's tested with over 100 automated tests, including hand-calculated DCF and ratio checks, and it works offline with clearly labelled sample data."

---

## Likely interview questions

| Question | Answer pointers |
|---|---|
| Why not scrape NSE? | No public API, access is blocked, and terms of use matter. The honest alternative is links plus uploads. |
| How do you stop the AI hallucinating? | It only sees numbered source blocks and must cite them. The offline engine is deterministic. LLM answers get a grounding check that traces each figure back to a source. Recommendation requests are refused. |
| Why FCFF and not FCFE? | FCFF is independent of capital structure and pairs with WACC. For banks I use justified P/B, because debt is operating capital. |
| Biggest valuation risk? | The terminal value share. That's why the sensitivity grid, scenarios and reverse DCF are there. |
| How would you scale it? | Licensed data vendor APIs, Postgres, scheduled refresh jobs, user accounts, and quarterly-result alerts. |
| What did you learn? | Data quality issues dominate: currencies, fiscal-year changes, statement basis, missing items. Handling them honestly mattered more than adding features. |
