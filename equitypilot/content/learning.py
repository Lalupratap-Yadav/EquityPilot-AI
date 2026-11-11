"""Learning Centre content: NISM Series XV (Research Analyst) and MBA Finance concepts.

Each module: summary, sections (markdown), key formulas, a 'try it' link to the relevant page,
and a quiz (question, options, correct index, explanation). Regulatory content is a simplified
educational overview - always refer to the current SEBI regulations and the NISM workbook.
"""

MODULES = [
    {
        "id": "markets", "title": "Indian securities markets", "page": "views/dashboard.py",
        "summary": "Who's who in the Indian equity market: regulator, exchanges, depositories and clearing.",
        "sections": [
            ("Market structure", """
- **SEBI** (Securities and Exchange Board of India) regulates the securities market. It was set up in 1988 and given statutory powers by the SEBI Act, 1992.
- **Stock exchanges** - mainly **NSE** and **BSE** - provide trading platforms. Benchmark indices: **NIFTY 50** (NSE) and **S&P BSE SENSEX** (30 stocks, BSE).
- **Depositories** - **NSDL** and **CDSL** - hold shares in dematerialised form through Depository Participants (DPs).
- **Clearing corporations** (e.g. NSE Clearing, Indian Clearing Corporation) guarantee settlement of trades.
- Indian equities settle on a **T+1** basis (trade day plus one working day)."""),
            ("Primary vs secondary market", """
- **Primary market**: companies raise capital (IPO, FPO, rights issue, QIP).
- **Secondary market**: investors trade already-issued securities on exchanges; the company receives no money.
- **SEBI market-cap categories** (for mutual-fund classification): large-cap = top 100 companies by full market capitalisation, mid-cap = 101st-250th, small-cap = 251st onwards."""),
            ("Where research data comes from", """
- **Exchange filings** (NSE/BSE): results, shareholding patterns, board-meeting outcomes, corporate actions - mandated by SEBI (LODR) Regulations, 2015.
- **Annual reports**: audited financial statements, notes, MD&A, risk management, related-party transactions.
- **RBI / MOSPI**: interest rates, inflation, GDP - the macro context for valuation inputs.
- Third-party aggregators are convenient but secondary: verify material numbers against filings."""),
        ],
        "formulas": ["Market capitalisation = Share price × Shares outstanding"],
        "quiz": [
            ("Which body regulates the Indian securities market?", ["RBI", "SEBI", "NSE", "Ministry of Corporate Affairs"], 1,
             "SEBI is the securities-market regulator; RBI regulates banks and monetary policy."),
            ("Shares held in demat form are held with…", ["Stock exchanges", "Clearing corporations", "Depositories (NSDL/CDSL)", "Registrars only"], 2,
             "NSDL and CDSL are India's depositories; investors access them through Depository Participants."),
            ("Under SEBI's categorisation, a company ranked 180th by market capitalisation is…", ["Large-cap", "Mid-cap", "Small-cap", "Micro-cap"], 1,
             "Mid-cap covers the 101st to 250th companies by full market capitalisation."),
            ("When a company raises money through an IPO, this takes place in the…", ["Secondary market", "Primary market", "Derivatives market", "Money market"], 1,
             "New issues are primary-market transactions; subsequent trading is the secondary market."),
            ("Indian equity trades now settle on a…", ["T+3 basis", "T+2 basis", "T+1 basis", "T+5 basis"], 2,
             "India completed the move to T+1 settlement for all listed equities in January 2023."),
        ],
    },
    {
        "id": "ra", "title": "Research analyst: process and regulation", "page": "views/report.py",
        "summary": "How professional equity research is done - and the rules that govern research analysts in India.",
        "sections": [
            ("The research process", """
1. **Understand the business** - products, customers, competitors, industry structure, management.
2. **Analyse financials** - growth, margins, returns, balance sheet, cash flows; check accounting quality.
3. **Forecast** - revenue drivers, margins, capex, working capital.
4. **Value** - relative (multiples vs peers/history) and intrinsic (DCF); sensitivity and scenarios.
5. **Assess risks** - business, financial, governance, regulatory.
6. **Communicate** - a clear, sourced report with disclosures."""),
            ("SEBI (Research Analysts) Regulations, 2014 - key ideas", """
- Persons who issue research reports or buy/sell/hold recommendations on securities to the public must be **registered with SEBI** as research analysts (subject to the exemptions in the regulations).
- **Disclosures** in research reports include financial interests and conflicts - e.g. whether the analyst or associates hold more than 1% of the subject company's securities, any compensation received from it, and whether the analyst has served as its officer or director.
- **Trading restrictions**: an analyst should not trade in securities they review contrary to their recommendation, and should not deal in them during the period around publication (the regulations specify 30 days before and 5 days after the report).
- Research must be based on reliable information, with **records maintained** and a reasonable basis for recommendations.
- Firms must manage conflicts of interest between research and other businesses (e.g. investment banking).

_This is a simplified overview for learning; always read the current regulations and circulars on sebi.gov.in._"""),
            ("Why EquityPilot doesn't recommend", """
EquityPilot is an educational tool, not a registered research analyst. It shows evidence, calculations and assumptions so **you** can form and defend a view - which is exactly the skill an analyst is assessed on."""),
        ],
        "formulas": [],
        "quiz": [
            ("Under the SEBI (Research Analysts) Regulations, 2014, a person publishing buy/sell recommendations to the public generally must…",
             ["Be registered with SEBI as a research analyst", "Only hold a demat account", "Be a member of NSE", "Be a chartered accountant"], 0,
             "Registration with SEBI is required unless an exemption in the regulations applies."),
            ("A research report must disclose if the analyst or associates own more than what share of the subject company?", ["0.1%", "1%", "5%", "10%"], 1,
             "The 1% ownership threshold is a standard disclosure item."),
            ("Which step should come BEFORE valuation in a research process?", ["Publishing the report", "Understanding the business and analysing financials", "Setting the target price", "Trading the stock"], 1,
             "Valuation rests on an understanding of the business and its financials."),
            ("Why do research firms separate research from investment banking?", ["To reduce costs", "To manage conflicts of interest", "Because SEBI bans investment banking", "To speed up reports"], 1,
             "Information barriers prevent banking relationships from influencing research views."),
            ("A trading restriction applies to research analysts around the publication of a report. The regulations specify…",
             ["1 day before and after", "30 days before and 5 days after", "90 days before only", "No restriction"], 1,
             "Analysts should not deal in the covered securities from 30 days before to 5 days after publication."),
        ],
    },
    {
        "id": "statements", "title": "Reading financial statements", "page": "views/financials.py",
        "summary": "The three statements, how they link, and Indian reporting conventions.",
        "sections": [
            ("The three statements", """
- **Statement of profit and loss** - revenue, expenses and profit over a period (FY = April-March for most Indian companies).
- **Balance sheet** - assets, liabilities and equity at a point in time. Assets = Liabilities + Equity.
- **Cash flow statement** - cash from **operating**, **investing** and **financing** activities. Profit is an opinion; cash is a fact."""),
            ("How they link", """
- Net profit flows into retained earnings (other equity) on the balance sheet.
- Depreciation reduces profit but not cash - it is added back in operating cash flow.
- Increases in working capital (receivables, inventory) absorb operating cash.
- Capex appears in investing cash flow and increases fixed assets."""),
            ("Indian conventions", """
- Listed companies report under **Ind AS** (converged with IFRS).
- **Standalone** statements cover only the listed company; **consolidated** statements include subsidiaries - compare like with like.
- Figures are usually presented in **₹ crore** (1 crore = 10 million) or ₹ lakh (1 lakh = 100,000).
- Quarterly results are filed within prescribed timelines under SEBI (LODR); annual reports include audited statements and notes."""),
        ],
        "formulas": ["Assets = Liabilities + Equity", "Free cash flow = Cash from operations - Capital expenditure",
                     "EBITDA = EBIT + Depreciation & amortisation"],
        "quiz": [
            ("Which statement shows the position at a single point in time?", ["Profit and loss", "Balance sheet", "Cash flow statement", "Statement of changes in equity"], 1,
             "The balance sheet is a snapshot; the others cover a period."),
            ("Depreciation is added back in operating cash flow because…", ["It is a cash expense", "It reduces profit but involves no cash outflow in the period", "It is a tax", "It is an investing activity"], 1,
             "The cash was spent when the asset was bought (capex); depreciation spreads that cost over time."),
            ("A company's consolidated statements include…", ["Only the parent company", "The parent and its subsidiaries", "Only subsidiaries", "Only foreign operations"], 1,
             "Consolidation combines the parent with the entities it controls."),
            ("₹1 crore equals…", ["₹1 lakh", "₹10 lakh", "₹100 lakh (10 million)", "₹1 billion"], 2,
             "1 crore = 100 lakh = 10,000,000."),
            ("Rising receivables with flat sales usually…", ["Increase operating cash flow", "Reduce operating cash flow", "Have no cash effect", "Increase revenue"], 1,
             "Cash is tied up in unpaid customer bills - a common earnings-quality warning sign."),
        ],
    },
    {
        "id": "ratios", "title": "Ratio analysis and DuPont", "page": "views/financials.py",
        "summary": "Turning statements into insight: profitability, returns, leverage, liquidity, efficiency and cash quality.",
        "sections": [
            ("Ratio families", """
| Family | Key ratios | Question answered |
|---|---|---|
| Growth | Revenue/EPS growth, CAGR | Is the business expanding? |
| Profitability | EBITDA, EBIT, net margin | How much of each rupee of sales is kept? |
| Returns | ROE, ROCE, ROA | Is capital earning more than it costs? |
| Leverage | Debt/equity, net debt/EBITDA, interest coverage | Can it service its debt? |
| Liquidity | Current, quick ratio | Can it meet short-term obligations? |
| Efficiency | Asset turnover, receivable & inventory days | How well are assets used? |
| Cash quality | CFO/net profit, FCF margin | Are profits backed by cash? |"""),
            ("DuPont analysis", """
ROE can rise for good reasons (better margins, faster asset turnover) or risky ones (more leverage). DuPont separates them:

**ROE = Net margin × Asset turnover × Equity multiplier**"""),
            ("Common pitfalls", """
- Compare ratios with **peers in the same industry** and with the company's own history.
- Banks and NBFCs need different ratios (NIM, GNPA/NNPA, CASA, CRAR).
- One-off items distort single-year ratios - look at 3-5 year averages.
- Growth from a negative base is not meaningful."""),
        ],
        "formulas": ["ROE = Net profit / Average shareholders' equity", "ROCE = EBIT / Capital employed (Total assets - Current liabilities)",
                     "Interest coverage = EBIT / Finance costs", "Current ratio = Current assets / Current liabilities",
                     "ROE = Net margin × Asset turnover × Equity multiplier"],
        "quiz": [
            ("ROE of 20% with net margin 5% and asset turnover 1.0x implies an equity multiplier of…", ["2x", "4x", "5x", "0.25x"], 1,
             "20% = 5% × 1.0 × EM, so EM = 4x - ROE here is driven mostly by leverage."),
            ("Which ratio best compares operating returns of companies with different debt levels?", ["ROE", "ROCE", "EPS growth", "Dividend yield"], 1,
             "ROCE uses EBIT and total capital employed, so it is independent of financing mix."),
            ("Interest coverage of 1.2x means…", ["Debt is very safe", "Operating profit barely covers interest", "The company has no debt", "ROE is 1.2%"], 1,
             "EBIT is only 1.2 times interest - a small fall in profit could make interest unaffordable."),
            ("CFO / net profit consistently around 0.5x suggests…", ["Excellent earnings quality", "Profits are not converting into cash", "High dividends", "Low tax rate"], 1,
             "Persistently low cash conversion warrants a look at receivables, inventory and revenue recognition."),
            ("Which of these is NOT meaningful for a bank?", ["P/B", "ROE", "EV/EBITDA", "Net interest margin"], 2,
             "For banks, debt is raw material, so enterprise-value and EBITDA measures lose meaning."),
        ],
    },
    {
        "id": "valuation", "title": "Valuation: multiples and DCF", "page": "views/valuation.py",
        "summary": "Relative valuation, discounted cash flow, cost of capital and sensitivity.",
        "sections": [
            ("Relative valuation", """
- **P/E** (price / EPS), **P/B** (price / book value per share), **EV/EBITDA**, **EV/Sales**, dividend yield.
- Compare against **peers** and the company's **own history**; adjust for differences in growth, ROE and risk.
- Use EV-based multiples when capital structures differ; P/B for banks."""),
            ("Discounted cash flow (FCFF)", """
1. Forecast free cash flow to the firm: **FCFF = EBIT×(1-t) + D&A - Capex - ΔNWC**.
2. Discount at **WACC**.
3. Add a **terminal value** (Gordon growth): TV = FCFF_N × (1+g) / (WACC - g).
4. EV - net debt = equity value; divide by shares for value per share.

The terminal value often contributes 60-80% of EV - so always show **sensitivity** to WACC and g, and **scenarios** (bear/base/bull)."""),
            ("Cost of capital", """
- **Cost of equity (CAPM)**: Ke = Rf + β × ERP. In India, Rf ≈ 10-year G-sec yield.
- **WACC** = We × Ke + Wd × Kd × (1 - t), using market-value weights.
- Terminal growth should not exceed long-run nominal GDP growth, and must be below WACC.
- **Reverse DCF**: solve for the growth the market price implies - a useful sanity check."""),
        ],
        "formulas": ["Ke = Rf + β × ERP", "WACC = We·Ke + Wd·Kd·(1 - t)", "FCFF = EBIT(1 - t) + D&A - Capex - ΔNWC",
                     "TV = FCFF_N × (1 + g) / (WACC - g)", "Justified P/B = (ROE - g) / (Ke - g)"],
        "quiz": [
            ("Rf = 7%, β = 1.2, ERP = 6%. Cost of equity is…", ["13.0%", "14.2%", "8.2%", "15.4%"], 1, "7% + 1.2 × 6% = 14.2%."),
            ("If WACC rises with everything else unchanged, DCF value per share…", ["Rises", "Falls", "Is unchanged", "Becomes negative"], 1,
             "Future cash flows are discounted more heavily."),
            ("The Gordon growth terminal value is undefined when…", ["g > 0", "WACC > g", "WACC ≤ g", "FCFF > 0"], 2,
             "The formula divides by (WACC - g), which must be positive."),
            ("Enterprise value equals…", ["Market cap + cash - debt", "Market cap + debt - cash", "Book equity + debt", "Revenue × P/E"], 1,
             "EV = market capitalisation + borrowings - cash (plus minorities/preference capital where relevant)."),
            ("A bank with ROE 16%, cost of equity 13% and growth 6% has a justified P/B of about…", ["0.8x", "1.0x", "1.43x", "2.7x"], 2,
             "(16% - 6%) / (13% - 6%) = 10/7 ≈ 1.43x."),
        ],
    },
    {
        "id": "technical", "title": "Technical analysis basics", "page": "views/technicals.py",
        "summary": "Trend, momentum and volatility indicators - and their limits.",
        "sections": [
            ("Trend", """
- **Moving averages** smooth prices: SMA (simple) and EMA (exponential, more weight on recent prices).
- Price above a rising 200-day average is commonly read as a long-term uptrend. A **golden cross** is the 50-day crossing above the 200-day; a **death cross** the reverse."""),
            ("Momentum and volatility", """
- **RSI (14)**: 0-100 oscillator; above 70 'overbought', below 30 'oversold' by convention.
- **MACD**: EMA(12) - EMA(26) with a 9-day signal line.
- **Bollinger bands**: 20-day SMA ± 2 standard deviations; bands widen in volatile periods.
- **Volume** confirms moves; **ATR** measures typical daily range."""),
            ("Using it responsibly", """
Technical indicators describe past price behaviour. They are most useful for **timing and risk management** alongside fundamental analysis - not as stand-alone predictions."""),
        ],
        "formulas": ["RSI = 100 - 100 / (1 + avg gain / avg loss)", "MACD = EMA(12) - EMA(26)", "Bollinger = SMA(20) ± 2σ"],
        "quiz": [
            ("An RSI reading of 78 is conventionally described as…", ["Oversold", "Neutral", "Overbought", "Bearish divergence"], 2, "Above 70 is the conventional overbought zone."),
            ("A 'golden cross' occurs when…", ["Price crosses above the 50-day SMA", "The 50-day SMA crosses above the 200-day SMA", "RSI crosses 50", "Volume doubles"], 1,
             "It is a moving-average crossover associated with a strengthening trend."),
            ("MACD is calculated as…", ["EMA(26) - EMA(12)", "EMA(12) - EMA(26)", "SMA(50) - SMA(200)", "RSI - 50"], 1, "Fast EMA minus slow EMA."),
            ("Bollinger bands widen when…", ["Volatility rises", "Volume falls", "Price is flat", "RSI is 50"], 0, "Band width is proportional to standard deviation."),
            ("Which statement is most accurate?", ["Indicators guarantee future prices", "Indicators summarise past price behaviour", "RSI measures earnings", "MACD measures debt"], 1,
             "They are descriptive tools; combine them with fundamentals and risk management."),
        ],
    },
    {
        "id": "risk", "title": "Risk, return and portfolios", "page": "views/portfolio.py",
        "summary": "Systematic vs unsystematic risk, beta, diversification and risk-adjusted returns.",
        "sections": [
            ("Types of risk", """
- **Systematic (market) risk** affects all stocks - interest rates, inflation, economic cycles. Measured by **beta**; cannot be diversified away.
- **Unsystematic (specific) risk** - company or industry events. Reduced by **diversification**."""),
            ("Measuring portfolio risk", """
- **Volatility** (standard deviation of returns, annualised × √252 for daily data).
- **Correlation**: diversification works best when holdings are not highly correlated.
- **Sharpe ratio** = (Return - risk-free rate) / volatility.
- **Maximum drawdown**: worst peak-to-trough fall.
- **Concentration**: Herfindahl index Σw²; effective number of holdings = 1/Σw²."""),
            ("Company-level financial risk", """
- **Leverage and coverage** (D/E, interest coverage), **liquidity** (current ratio), **cash-flow quality**.
- **Altman Z-score** combines ratios to screen for distress; **Piotroski F-score** tests improving fundamentals.
- **Promoter pledging** can create forced-selling risk."""),
        ],
        "formulas": ["Sharpe = (Rp - Rf) / σp", "β = Cov(Ri, Rm) / Var(Rm)", "Effective N = 1 / Σ wᵢ²"],
        "quiz": [
            ("Which risk can be reduced by diversification?", ["Systematic risk", "Unsystematic risk", "Interest-rate risk for all stocks", "Inflation"], 1,
             "Company-specific risk diversifies away; market risk does not."),
            ("A stock with beta 1.5 is expected to move, on average…", ["50% less than the market", "In line with the market", "50% more than the market", "Opposite to the market"], 2,
             "Beta 1.5 implies 1.5x the market's moves on average."),
            ("Portfolio return 15%, risk-free 6.5%, volatility 17%. The Sharpe ratio is…", ["0.50", "0.88", "1.15", "0.38"], 0, "(15 - 6.5) / 17 = 0.50."),
            ("Four equally weighted holdings have an effective number of…", ["1", "2", "4", "16"], 2, "Σw² = 4 × 0.25² = 0.25; 1/0.25 = 4."),
            ("High promoter pledging is a risk because…", ["It increases dividends", "Lenders may sell pledged shares if prices fall", "It reduces free float", "It is illegal"], 1,
             "Margin calls on pledged shares can trigger forced selling."),
        ],
    },
    {
        "id": "corporate", "title": "Corporate actions and governance", "page": "views/news.py",
        "summary": "Dividends, bonus issues, splits, buybacks, rights issues and governance signals.",
        "sections": [
            ("Corporate actions", """
- **Dividend**: cash distribution; the share trades ex-dividend after the record date.
- **Bonus issue**: free shares from reserves - more shares, lower price, no change in total value.
- **Stock split**: face value divided - more shares, proportionally lower price.
- **Buyback**: the company repurchases shares - reduces share count; often signals management's view that shares are undervalued.
- **Rights issue**: new shares offered to existing shareholders, usually at a discount."""),
            ("Governance signals", """
- Board independence, related-party transactions, auditor changes or qualifications.
- Promoter holding trends and **pledges**.
- Timeliness and quality of disclosures under SEBI (LODR).
- Capital-allocation track record (ROCE vs cost of capital, acquisitions, dividends)."""),
        ],
        "formulas": ["Adjusted price after a 1:1 bonus ≈ Old price / 2", "Payout ratio = Dividends / Net profit"],
        "quiz": [
            ("After a 1:1 bonus issue, an investor holding 100 shares at ₹1,000 will have about…", ["100 shares at ₹2,000", "200 shares at ₹500", "200 shares at ₹1,000", "50 shares at ₹2,000"], 1,
             "Share count doubles and the price roughly halves; total value is unchanged."),
            ("A buyback generally…", ["Increases shares outstanding", "Reduces shares outstanding", "Has no effect on share count", "Creates debt automatically"], 1,
             "Repurchased shares are extinguished, so EPS on the remaining shares can rise."),
            ("Which is a governance red flag?", ["Independent audit committee", "Frequent unexplained auditor resignations", "Timely results", "Dividend consistency"], 1,
             "Auditor exits without clear reasons warrant investigation."),
            ("A rights issue is offered to…", ["The public at large", "Existing shareholders", "Only promoters", "Only institutions"], 1,
             "Rights are offered pro rata to existing shareholders."),
        ],
    },
]


def module(mid: str) -> dict | None:
    return next((m for m in MODULES if m["id"] == mid), None)


def total_questions() -> int:
    return sum(len(m["quiz"]) for m in MODULES)
